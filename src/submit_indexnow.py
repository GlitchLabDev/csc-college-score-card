#!/usr/bin/env python3
"""
Submit URLs to IndexNow — Bing, Copilot, DuckDuckGo and Yandex.

Google does NOT support IndexNow. This does nothing for Google Search; it exists
because Bing and DuckDuckGo are already sending traffic while Google sits on
5,800-odd pages at "Discovered - currently not indexed".

Run it from your own machine (the key file has to be live on the site first):

    python3 src/submit_indexnow.py --dry-run     # show what would be sent
    python3 src/submit_indexnow.py               # submit every URL in sitemap.xml
    python3 src/submit_indexnow.py URL [URL...]  # submit just these

Standard library only — no pip install needed.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Must match INDEXNOW_KEY in build_site.py, and the file served at
# https://www.myuniview.com/<KEY>.txt — IndexNow verifies ownership by fetching it.
KEY = '83328049409d86f564920869f691aabe'
HOST = 'www.myuniview.com'
ORIGIN = f'https://{HOST}'
ENDPOINT = 'https://api.indexnow.org/indexnow'
BATCH = 10000          # IndexNow's documented per-request ceiling
TIMEOUT = 60

REPO = Path(__file__).resolve().parent.parent


def sitemap_urls():
    """Every <loc> in the committed sitemap."""
    sm = REPO / 'sitemap.xml'
    if not sm.exists():
        sys.exit(f'No sitemap at {sm} — run build_site.py first.')
    urls = re.findall(r'<loc>\s*(.*?)\s*</loc>', sm.read_text(), re.S)
    if not urls:
        sys.exit(f'{sm} parsed but contained no <loc> entries.')
    return urls


def check_key_file():
    """
    The endpoint rejects the whole batch if it can't fetch the key file, so fail
    early with a useful message instead of a 403 on 6,563 URLs.
    """
    url = f'{ORIGIN}/{KEY}.txt'
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            body = r.read().decode('utf-8', 'replace').strip()
    except urllib.error.HTTPError as e:
        return False, f'{url} returned HTTP {e.code}. Commit and push the key file first.'
    except Exception as e:
        return False, f"Couldn't fetch {url}: {e}"
    if body != KEY:
        return False, f'{url} exists but contains "{body[:40]}" instead of the key.'
    return True, f'Key file verified at {url}'


def submit(urls):
    payload = {
        'host': HOST,
        'key': KEY,
        'keyLocation': f'{ORIGIN}/{KEY}.txt',
        'urlList': urls,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json; charset=utf-8'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read().decode('utf-8', 'replace')[:400]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')[:400]


# What the documented status codes actually mean, so a 422 isn't a mystery.
MEANING = {
    200: 'Accepted — URLs are queued.',
    202: 'Accepted, key validation pending. Normal on a first submission.',
    400: 'Bad request — malformed JSON or URL list.',
    403: 'Key not valid — see the response body for which case this is.',
    422: 'URLs do not match the host, or the key does not match the schema.',
    429: 'Too many requests. Wait and retry; do not resubmit the same URLs repeatedly.',
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('urls', nargs='*', help='specific URLs; default is all of sitemap.xml')
    ap.add_argument('--dry-run', action='store_true', help='show what would be sent, send nothing')
    args = ap.parse_args()

    urls = args.urls or sitemap_urls()

    bad = [u for u in urls if not u.startswith(ORIGIN)]
    if bad:
        sys.exit(f'{len(bad)} URL(s) are not on {ORIGIN}, which IndexNow rejects. '
                 f'First: {bad[0]}')

    print(f'{len(urls):,} URL(s) to submit for {HOST}')
    print(f'  first: {urls[0]}')
    print(f'  last : {urls[-1]}')

    if args.dry_run:
        print('\n--dry-run: nothing sent.')
        return

    ok, msg = check_key_file()
    print(f'\n{msg}')
    if not ok:
        sys.exit(1)

    batches = [urls[i:i + BATCH] for i in range(0, len(urls), BATCH)]
    failures = 0
    pending = False
    for i, b in enumerate(batches, 1):
        status, body = submit(b)
        note = MEANING.get(status, 'Unexpected status.')
        print(f'\nBatch {i}/{len(batches)} — {len(b):,} URLs — HTTP {status}: {note}')
        if body.strip():
            print(f'  response: {body.strip()}')
        if 'SiteVerificationNotCompleted' in body:
            pending = True
        if status not in (200, 202):
            failures += 1

    if pending:
        # Not a configuration problem: the key file is live and correct, but Bing
        # fetches and verifies it on its own schedule after a domain's first ever
        # submission. Re-running later is the whole fix.
        sys.exit('\nBing has not finished verifying the key file yet. Nothing is wrong '
                 'with it — this is a one-time wait after a domain\'s first submission.\n'
                 'Wait a few hours and run this again; registering the site at '
                 'https://www.bing.com/webmasters usually speeds it up.')
    if failures:
        sys.exit(f'\n{failures} batch(es) were not accepted.')
    print('\nDone. Bing typically reflects this within a day or two; check Bing '
          'Webmaster Tools rather than assuming it worked.')


if __name__ == '__main__':
    main()
