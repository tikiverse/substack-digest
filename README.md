# Substack Digest

Daily email digest of your Substack subscriptions, summarized by Claude.

## How it works

`digest.py` reads `feeds.json`, fetches RSS feeds, summarizes new posts with Claude, and emails you a digest. Runs daily via GitHub Actions (`.github/workflows/digest.yml`).

### GitHub Actions setup

**Secrets** (required):

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key |
| `SMTP_USER` | Email sender (e.g. Gmail address) |
| `SMTP_PASS` | [App password](https://support.google.com/accounts/answer/185833?hl=en) (not account password) |

**Variables** (optional):

- `EMAIL_TO` (default: `SMTP_USER`)
- `SMTP_HOST` (default: `smtp.gmail.com`)
- `SMTP_PORT` (default: `587`)

**Optional env overrides**: `LOOKBACK_HOURS` (26), `MAX_CHARS_PER_POST` (8000), `CLAUDE_MODEL`.

Test via **Actions** tab > **Run workflow**.

## Syncing feeds

`feeds.json` goes stale as you subscribe/unsubscribe. `sync_feeds.py` scrapes your current subscriptions from substack.com via Playwright.

```bash
# One-time setup
uv run playwright install chromium

# Add your session cookie (DevTools > Application > Cookies > substack.sid)
echo 'SUBSTACK_SID=your-cookie-value' > .env

# Sync
uv run sync_feeds.py
```

Also accepts `--cookie` flag or `SUBSTACK_SID` env var.
