import os
from dotenv import load_dotenv
import multiprocessing
import argparse
from bs4 import BeautifulSoup
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
import requests
from threading import Lock
import time
from pymongo import MongoClient




class MultiThreadedCrawler:
    def __init__(self, seed_url, basis='time', duration=None, max_urls=None,
                 mongodb_uri=None, mongodb_db='webcrawler', mongodb_collection='pages', max_workers=5):
        self.seed_url = seed_url
        self.basis = basis
        self.duration = duration
        self.max_urls = max_urls
        self.root_url = '{}://{}'.format(urlparse(self.seed_url).scheme,
                                         urlparse(self.seed_url).netloc)
        self.pool = ThreadPoolExecutor(max_workers=max_workers)
        self.scraped_pages = set()
        self.crawl_queue = Queue()
        self.crawl_queue.put(self.seed_url)
        self.lock = Lock()

        # MongoDB client (optional)
        self.mongo_client = None
        self.mongo_collection = None
        if mongodb_uri:
            try:
                self.mongo_client = MongoClient(mongodb_uri,serverSelectionTimeoutMS=5000)
                self.mongo_client.admin.command('isMaster')
                db = self.mongo_client[mongodb_db]
                self.mongo_collection = db[mongodb_collection]
                print("Connected to MongoDB successfully.")
            except Exception as e:
                print(f"Warning: could not connect to MongoDB: {e}")
                self.mongo_client = None

    def parse_links(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        anchor_tags = soup.find_all('a', href=True)
        for link in anchor_tags:
            url = link['href']
            # only follow same-site or relative links
            if url.startswith('/') or url.startswith(self.root_url):
                url = urljoin(self.root_url, url)
                if url not in self.scraped_pages:
                    self.crawl_queue.put(url)

    def extract_text(self, html):
        soup = BeautifulSoup(html, 'html5lib')
        # prefer <title>
        title_tag = soup.title.string.strip() if soup.title and soup.title.string else ''
        # extract paragraph text
        paras = soup.find_all('p')
        text_parts = []
        for p in paras:
            t = p.get_text(strip=True)
            if t and 'https:' not in t:
                text_parts.append(t)
        text = '\n'.join(text_parts)
        return title_tag, text

    def save_page(self, url, title, content, status_code, headers):
        # 1. Check if the collection object exists (SHOULD exist if connection succeeded)
        if self.mongo_collection is None:
            print(f"!!! DEBUG: SKIPPING SAVE for {url}. Collection object is NONE.") 
            return
        
        doc = {
            'seed': self.seed_url,
            'url': url,
            'title': title,
            # ... rest of the document ...
        }
        try:
            # 2. Print BEFORE attempting insertion
            print(f"ATTEMPTING SAVE: {url[:50]}...")
            self.mongo_collection.insert_one(doc)
            
            # 3. Print AFTER successful insertion
            print(f"✅ SUCCESSFULLY SAVED: {url[:50]}...") 
        except Exception as e:
            # 4. Print the exact exception that occurs during insertion
            print(f"❌ FAILED to save {url[:50]} to MongoDB: {e}")
    def post_scrape_callback(self, fut):
        try:
            result = fut.result()
        except Exception:
            return
        if result and result.status_code == 200:
            html = result.text
            self.parse_links(html)
            title, content = self.extract_text(html)
            print(f"\n--- {result.url} ({result.status_code}) ---\nTitle: {title}\n")
            # store in MongoDB if configured
            self.save_page(result.url, title, content, result.status_code, result.headers)

    def scrape_page(self, url):
        try:
            # keep requests threadsafe with a simple lock for session-less requests
            with self.lock:
                res = requests.get(url, timeout=(3, 30))
                return res
        except requests.RequestException:
            return None

    def run(self):
        start_time = time.time()
        try:
            while True:
                # check stopping conditions
                if self.basis == 'time' and self.duration is not None:
                    if (time.time() - start_time) >= self.duration:
                        print(f"Duration {self.duration}s reached. Stopping crawler.")
                        break
                if self.basis == 'count' and self.max_urls is not None:
                    if len(self.scraped_pages) >= self.max_urls:
                        print(f"Crawled {len(self.scraped_pages)} pages (limit {self.max_urls}). Stopping crawler.")
                        break

                try:
                    print("\nName of the current executing process:", multiprocessing.current_process().name)
                    target_url = self.crawl_queue.get(timeout=1)
                    if target_url not in self.scraped_pages:
                        print("Scraping URL:", target_url)
                        self.scraped_pages.add(target_url)
                        job = self.pool.submit(self.scrape_page, target_url)
                        job.add_done_callback(self.post_scrape_callback)
                except Empty:
                    # nothing to process right now; loop back and re-check stop conditions
                    continue
                except Exception as e:
                    print(f"Error in run loop: {e}")
                    continue
        finally:
            try:
                self.pool.shutdown(wait=True)
            except Exception:
                pass
            if self.mongo_client:
                try:
                    print("Closing MongoDB connection.")
                    self.mongo_client.close()
                except Exception:
                    pass

    def info(self):
        print('\nSeed URL:', self.seed_url)
        print('Scraped pages count:', len(self.scraped_pages))
        print('Scraped pages sample:', list(self.scraped_pages)[:10])


def _valid_url(u):
    p = urlparse(u)
    return p.scheme in ('http', 'https') and p.netloc


if __name__ == '__main__':
    load_dotenv()  # Load environment variables from .env file if present
    parser = argparse.ArgumentParser(description='Simple multithreaded crawler')
    parser.add_argument('seed_url', nargs='?', default='https://www.geeksforgeeks.org/',
                        help='Seed URL to start crawling from')
    parser.add_argument('--basis', choices=['time', 'count'], default='time',
                        help='Stop crawling after a duration (`time`) or after crawling a number of URLs (`count`)')
    parser.add_argument('--duration', type=int, default=30,
                        help='Duration in seconds to run the crawler (when basis=time)')
    parser.add_argument('--max-urls', type=int, default=None,
                        help='Maximum number of unique URLs to crawl (when basis=count)')
    parser.add_argument('--mongodb-uri', type=str, default=os.getenv('MONGODB_URL'),
                        help='MongoDB URI to store crawled pages, e.g. mongodb://localhost:27017')
    parser.add_argument('--mongodb-db', type=str, default='webcrawler', help='MongoDB database name')
    parser.add_argument('--mongodb-collection', type=str, default='pages', help='MongoDB collection name')
    parser.add_argument('--workers', type=int, default=5, help='Number of worker threads')
    args = parser.parse_args()

    if args.mongodb_uri:
        print(f"DEBUG: MongoDB URI successfully loaded: {args.mongodb_uri[:20]}...")
    else:
        print("DEBUG: MongoDB URI is set to None.connection will be skipped.")

    if not _valid_url(args.seed_url):
        print('Invalid seed URL. Provide a URL with http:// or https://')
        raise SystemExit(1)

    cc = MultiThreadedCrawler(args.seed_url, basis=args.basis, duration=args.duration,
                               max_urls=args.max_urls, mongodb_uri=args.mongodb_uri,
                               mongodb_db=args.mongodb_db, mongodb_collection=args.mongodb_collection,
                               max_workers=args.workers)

    try:
        cc.run()
    except KeyboardInterrupt:
        print('\nKeyboard interrupt received; stopping crawler.')
    finally:
        cc.info()
