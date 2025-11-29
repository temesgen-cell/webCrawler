import multiprocessing
import argparse
from bs4 import BeautifulSoup
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
import requests
from threading import Lock
from time import sleep
import time


class MultiThreadedCrawler:

    def __init__(self, seed_url, duration=None):
        self.seed_url = seed_url
        self.duration = duration
        self.root_url = '{}://{}'.format(urlparse(self.seed_url).scheme,
                                         urlparse(self.seed_url).netloc)
        self.pool = ThreadPoolExecutor(max_workers=5)
        self.scraped_pages = set([])
        self.crawl_queue = Queue()
        self.crawl_queue.put(self.seed_url)

    def parse_links(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        Anchor_Tags = soup.find_all('a', href=True)
        for link in Anchor_Tags:
            url = link['href']
            if url.startswith('/') or url.startswith(self.root_url):
                url = urljoin(self.root_url, url)
                if url not in self.scraped_pages:
                    self.crawl_queue.put(url)

    def scrape_info(self, html):
        soup = BeautifulSoup(html, "html5lib")
        web_page_paragraph_contents = soup('p')
        text = ''
        for para in web_page_paragraph_contents:
            if not ('https:' in str(para.text)):
                text = text + str(para.text).strip()
        print(f'\n <---Text Present in The WebPage is --->\n', text, '\n')
        return

    def post_scrape_callback(self, res):
        result = res.result()
        if result and result.status_code == 200:
            self.parse_links(result.text)
            self.scrape_info(result.text)
#here i just added a with lock to make the requests thread synchronized
    def scrape_page_synchronous(self, url):
        try:
            with Lock():
                res = requests.get(url, timeout=(3, 30))
                return res
        except requests.RequestException:
            return

    def run_web_crawler(self):
        start_time = time.time()
        while True:
            # stop when duration exceeded (if duration is set)
            if self.duration is not None and (time.time() - start_time) >= self.duration:
                print(f"Duration {self.duration}s reached. Stopping crawler.")
                break

            try:
                print("\n Name of the current executing process: ",
                      multiprocessing.current_process().name, '\n')
                # use short timeout so we can check duration often
                target_url = self.crawl_queue.get(timeout=1)
                if target_url not in self.scraped_pages:
                    print("Scraping URL: {}".format(target_url))
                    self.current_scraping_url = "{}".format(target_url)
                    self.scraped_pages.add(target_url)
                    job = self.pool.submit(self.scrape_page_synchronous, target_url)
                    job.add_done_callback(self.post_scrape_callback)

            except Empty:
                # queue empty; loop and check duration again
                continue
            except Exception as e:
                print(e)
                continue

        try:
            self.pool.shutdown(wait=True)
        except Exception:
            pass

    def info(self):
        print('\n Seed URL is: ', self.seed_url, '\n')
        print('Scraped pages are: ', self.scraped_pages, '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Simple multithreaded crawler')
    parser.add_argument('seed_url', nargs='?', default='https://www.geeksforgeeks.org/',
                        help='Seed URL to start crawling from')
    parser.add_argument('-d', '--duration', type=int, default=10,
                        help='Duration in seconds to run the crawler')
    args = parser.parse_args()

    cc = MultiThreadedCrawler(args.seed_url, duration=args.duration)
    try:
        cc.run_web_crawler()
    except KeyboardInterrupt:
        print('\nKeyboard interrupt received; stopping crawler.')
    finally:
        cc.info()