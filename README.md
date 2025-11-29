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

The `--duration` (or `-d`) flag controls how many seconds the crawler runs before stopping.

Notes:
- The script uses `requests` and `beautifulsoup4` (with `html5lib` parser).
- If you meant a module named `request` (singular), clarify — the common package is `requests` (plural).
- The crawler will make HTTP requests to external sites. Use responsibly and respect robots.txt and site terms.
