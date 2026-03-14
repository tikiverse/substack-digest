#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright"]
# ///
"""
Sync feeds.json with your actual Substack subscriptions.

Uses Playwright to open substack.com/library with your session cookie,
then extracts all publication URLs from the page.

Usage:
    uv run sync_feeds.py
    uv run sync_feeds.py --cookie "your-substack-sid"
    # Or set SUBSTACK_SID in env or .env file

Note: First run may require: playwright install chromium
"""

import argparse
import json
import sys
from pathlib import Path

FEEDS_FILE = Path(__file__).parent / "feeds.json"
LIBRARY_URL = "https://substack.com/library"


def get_cookie(cli_cookie: str | None) -> str:
    """Get substack.sid cookie from CLI arg, env var, or .env file."""
    if cli_cookie:
        return cli_cookie

    import os

    val = os.environ.get("SUBSTACK_SID")
    if val:
        return val

    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "SUBSTACK_SID":
                return value.strip().strip("\"'")

    print("Error: No cookie found. Provide via --cookie, SUBSTACK_SID env var, or .env file.")
    sys.exit(1)


def fetch_subscriptions(cookie: str) -> list[str]:
    """Launch browser, load library page, extract publication URLs."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Error: playwright is not installed.")
        print("  pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies([{
            "name": "substack.sid",
            "value": cookie,
            "domain": ".substack.com",
            "path": "/",
        }])

        page = context.new_page()
        page.goto(LIBRARY_URL, wait_until="domcontentloaded")
        # Wait for subscription links to render (sidebar with publication list)
        page.wait_for_selector("a[href]", timeout=15000)
        page.wait_for_timeout(2000)  # let remaining items render

        if "sign in" in page.title().lower() or "login" in page.url.lower():
            browser.close()
            print("Error: Not authenticated. Your cookie may be expired.")
            sys.exit(1)

        # Extract all root-path links to non-substack.com domains
        urls = page.evaluate("""() => {
            const pubUrls = new Set();
            for (const a of document.querySelectorAll('a[href]')) {
                try {
                    const url = new URL(a.href);
                    const path = url.pathname.replace(/\\/$/, '');
                    if ((path === '' || path === '/') &&
                        url.hostname !== 'substack.com' &&
                        url.hostname !== 'www.substack.com') {
                        pubUrls.add(url.origin);
                    }
                } catch {}
            }
            return Array.from(pubUrls);
        }""")

        browser.close()

    if not urls:
        print("Error: No subscriptions found on the library page.")
        sys.exit(1)

    return sorted(urls, key=str.lower)


def main():
    parser = argparse.ArgumentParser(description="Sync feeds.json from Substack subscriptions")
    parser.add_argument("--cookie", help="substack.sid cookie value")
    args = parser.parse_args()

    cookie = get_cookie(args.cookie)

    print("Fetching subscriptions from Substack...")
    new_feeds = fetch_subscriptions(cookie)

    # Load existing feeds for diff
    old_feeds = set()
    if FEEDS_FILE.exists():
        old_feeds = set(json.loads(FEEDS_FILE.read_text()))

    new_set = set(new_feeds)
    added = new_set - old_feeds
    removed = old_feeds - new_set

    # Write
    FEEDS_FILE.write_text(json.dumps(new_feeds, indent=2) + "\n")

    # Summary
    print(f"\nTotal feeds: {len(new_feeds)}")
    if added:
        print(f"  + {len(added)} added")
        for url in sorted(added):
            print(f"    {url}")
    if removed:
        print(f"  - {len(removed)} removed")
        for url in sorted(removed):
            print(f"    {url}")
    if not added and not removed:
        print("  No changes.")
    print(f"\nWrote {FEEDS_FILE}")


if __name__ == "__main__":
    main()
