#!/usr/bin/env python3
"""
Substack Daily Digest
Fetches RSS feeds from your Substack subscriptions, summarizes new posts
using Claude, and emails you a daily digest.
"""

import os
import json
import smtplib
import hashlib
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import feedparser
import httpx

# ---------------------------------------------------------------------------
# Configuration (set via environment variables / GitHub Secrets)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASS = os.environ["SMTP_PASS"]
EMAIL_TO = os.environ.get("EMAIL_TO", SMTP_USER)  # defaults to sender
LOOKBACK_HOURS = int(os.environ.get("LOOKBACK_HOURS", "26"))  # slightly >24 to avoid gaps
MAX_CHARS_PER_POST = int(os.environ.get("MAX_CHARS_PER_POST", "8000"))
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Load feeds from feeds.json (list of Substack URLs or RSS URLs)
FEEDS_FILE = Path(__file__).parent / "feeds.json"


def load_feeds() -> list[str]:
    """Load RSS feed URLs from feeds.json."""
    with open(FEEDS_FILE) as f:
        feeds = json.load(f)
    # Normalise: if someone puts "example.substack.com", convert to RSS URL
    normalised = []
    for url in feeds:
        url = url.strip().rstrip("/")
        if not url.startswith("http"):
            url = f"https://{url}"
        if "/feed" not in url:
            url = f"{url}/feed"
        normalised.append(url)
    return normalised


def fetch_new_posts(feeds: list[str], since: datetime) -> list[dict]:
    """Fetch posts published after `since` from all feeds."""
    posts = []
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            blog_title = parsed.feed.get("title", feed_url)
            for entry in parsed.entries:
                # Parse published date
                published = None
                for date_field in ("published_parsed", "updated_parsed"):
                    tp = entry.get(date_field)
                    if tp:
                        published = datetime(*tp[:6], tzinfo=timezone.utc)
                        break
                if published and published < since:
                    continue
                # Extract content (prefer full content, fall back to summary)
                content = ""
                if entry.get("content"):
                    content = entry.content[0].get("value", "")
                elif entry.get("summary"):
                    content = entry.summary
                # Strip HTML tags (basic)
                import re
                content = re.sub(r"<[^>]+>", " ", content)
                content = re.sub(r"\s+", " ", content).strip()
                posts.append({
                    "blog": blog_title,
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "published": published.isoformat() if published else "Unknown",
                    "content": content[:MAX_CHARS_PER_POST],
                })
        except Exception as e:
            print(f"⚠ Error fetching {feed_url}: {e}")
    return posts


def summarize_post(post: dict) -> str:
    """Use Claude to summarize a single post."""
    prompt = f"""Summarize the following newsletter post in 3-5 concise bullet points.
Focus on the key insights, arguments, or news. Be specific — no filler.

Title: {post['title']}
Author/Blog: {post['blog']}

Content:
{post['content']}"""

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"]


def build_html_email(posts_with_summaries: list[dict], date_str: str) -> str:
    """Build a nicely formatted HTML email."""
    html = f"""\
<html>
<head>
<style>
  body {{ font-family: Georgia, serif; max-width: 640px; margin: 0 auto; padding: 20px; color: #1a1a1a; }}
  h1 {{ font-size: 22px; border-bottom: 2px solid #111; padding-bottom: 8px; }}
  .post {{ margin-bottom: 28px; }}
  .post h2 {{ font-size: 17px; margin: 0 0 2px 0; }}
  .post .meta {{ font-size: 13px; color: #666; margin-bottom: 8px; }}
  .post .meta a {{ color: #444; }}
  .post .summary {{ font-size: 15px; line-height: 1.6; color: #333; }}
  .post .summary ul {{ padding-left: 18px; }}
  .footer {{ margin-top: 32px; font-size: 12px; color: #999; border-top: 1px solid #ddd; padding-top: 10px; }}
</style>
</head>
<body>
<h1>📬 Substack Digest — {date_str}</h1>
<p style="color:#666;font-size:14px;">{len(posts_with_summaries)} new post{'s' if len(posts_with_summaries) != 1 else ''} from your subscriptions.</p>
"""
    for item in posts_with_summaries:
        post = item["post"]
        summary = item["summary"]
        html += f"""\
<div class="post">
  <h2>{post['title']}</h2>
  <div class="meta">{post['blog']} · <a href="{post['link']}">Read full post →</a></div>
  <div class="summary">{summary}</div>
</div>
"""
    html += """\
<div class="footer">Generated by your Substack Digest bot using Claude.</div>
</body>
</html>"""
    return html


def build_plain_email(posts_with_summaries: list[dict], date_str: str) -> str:
    """Build a plain text fallback."""
    lines = [f"SUBSTACK DIGEST — {date_str}", f"{len(posts_with_summaries)} new posts", ""]
    for item in posts_with_summaries:
        post = item["post"]
        lines.append(f"### {post['title']}")
        lines.append(f"    {post['blog']} — {post['link']}")
        lines.append(item["summary"])
        lines.append("")
    return "\n".join(lines)


def send_email(html: str, plain: str, date_str: str):
    """Send the digest email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📬 Substack Digest — {date_str}"
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [EMAIL_TO], msg.as_string())
    print(f"✅ Digest sent to {EMAIL_TO}")


def main():
    print("📡 Loading feeds…")
    feeds = load_feeds()
    print(f"   {len(feeds)} feeds loaded")

    since = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    print(f"📥 Fetching posts since {since.isoformat()}…")
    posts = fetch_new_posts(feeds, since)
    print(f"   {len(posts)} new posts found")

    if not posts:
        print("😴 No new posts — skipping digest.")
        return

    print("🤖 Summarizing with Claude…")
    results = []
    for i, post in enumerate(posts, 1):
        print(f"   [{i}/{len(posts)}] {post['title']}")
        try:
            summary = summarize_post(post)
        except Exception as e:
            print(f"   ⚠ Summarization failed: {e}")
            summary = f"(Summary unavailable — <a href='{post['link']}'>read the original</a>)"
        results.append({"post": post, "summary": summary})

    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    html = build_html_email(results, date_str)
    plain = build_plain_email(results, date_str)

    print("📧 Sending digest…")
    send_email(html, plain, date_str)
    print("🎉 Done!")


if __name__ == "__main__":
    main()
