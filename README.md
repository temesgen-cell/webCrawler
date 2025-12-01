# Crawl

Tiny multithreaded crawler. To run locally, create a virtual environment, install dependencies, then run `crawl.py`.

Setup (recommended):

```bash
cd /home/temesgen/tom/python/crawl
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Run:

```bash
python crawl.py
```

Or specify seed URL and duration:

```bash
python crawl.py https://example.com --duration 5
```

The `--duration` flag controls how many seconds the crawler runs before stopping when `--basis time`.
You can also stop by number of URLs using `--basis count` and `--max-urls`.

Examples:

Run for 5 seconds:

```bash
python crawl.py https://example.com --basis time --duration 5
```

Run until 100 unique URLs crawled:

```bash
python crawl.py https://example.com --basis count --max-urls 100
```

Store results in MongoDB:

```bash
python crawl.py https://example.com --basis time --duration 30 --mongodb-uri mongodb://localhost:27017 --mongodb-db webcrawler --mongodb-collection pages
``` 

## ⚙️ How the Multi-threaded Crawler Works

This diagram illustrates the action flow, highlighting the use of a ThreadPoolExecutor for concurrent scraping and the central role of the Queue as a URL frontier.

![Action Flow Diagram of the Multi-threaded Web Crawler](https://github.com/temesgen-cell/webCrawler/blob/main/assets/crawlers_actionflow_diagram.png)

Notes:
- The script uses `requests` and `beautifulsoup4` (with `html5lib` parser).
- If you meant a module named `request` (singular), clarify — the common package is `requests` (plural).
- The crawler will make HTTP requests to external sites. Use responsibly and respect robots.txt and site terms.
