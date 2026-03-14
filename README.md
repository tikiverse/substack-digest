# 📬 Substack Daily Digest

A lightweight tool that fetches your Substack subscriptions via RSS, summarizes each new post with Claude, and emails you a clean daily digest.

## How It Works

1. Reads your Substack list from `feeds.json`
2. Fetches RSS feeds and finds posts from the last ~26 hours
3. Sends each post to Claude for a concise bullet-point summary
4. Emails you a formatted digest with summaries + links

## Setup (10 minutes)

### 1. Create a private GitHub repo

```bash
git clone <your-new-repo>
cd <your-new-repo>
# Copy all files from this project into the repo
```

### 2. Add your Substacks to `feeds.json`

Replace the examples with your actual subscriptions:

```json
[
  "https://platformer.substack.com",
  "https://www.slowboring.com",
  "https://astralcodexten.substack.com",
  "https://www.thefitzwilliam.com"
]
```

You can use either:
- Full RSS URL: `https://example.substack.com/feed`
- Just the domain: `https://example.substack.com` (auto-converted)
- Or even: `example.substack.com` (we add the rest)

**Tip:** To find all your subscriptions, go to `substack.com/inbox` while logged in.

### 3. Set up email sending

The easiest option is **Gmail with an App Password**:

1. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   (requires 2FA enabled on your Google account)
2. Create a new app password — copy the 16-character code

Alternatively, you can use any SMTP provider (Fastmail, SendGrid, Amazon SES, etc.).

### 4. Add GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these secrets:

| Secret              | Value                                      |
|---------------------|--------------------------------------------|
| `ANTHROPIC_API_KEY` | Your Claude API key from console.anthropic.com |
| `SMTP_HOST`         | `smtp.gmail.com` (or your provider)        |
| `SMTP_PORT`         | `587`                                      |
| `SMTP_USER`         | `you@gmail.com`                            |
| `SMTP_PASS`         | Your app password (not your real password!) |
| `EMAIL_TO`          | Where to send the digest (defaults to SMTP_USER) |

### 5. Test it

Go to **Actions** tab → **Daily Substack Digest** → **Run workflow** → click the green button.

Check your email! If something fails, the Actions log will show you what went wrong.

### 6. Adjust the schedule

Edit `.github/workflows/digest.yml` and change the cron expression:

```yaml
# Some common options (all times UTC):
- cron: "0 7 * * *"    # 7 AM UTC = 3 AM ET / 12 AM PT
- cron: "0 11 * * *"   # 11 AM UTC = 7 AM ET / 4 AM PT
- cron: "0 13 * * *"   # 1 PM UTC = 9 AM ET / 6 AM PT
```

## Configuration

Optional environment variables you can set as GitHub Secrets:

| Variable            | Default  | Description                              |
|---------------------|----------|------------------------------------------|
| `LOOKBACK_HOURS`    | `26`     | How far back to look for new posts       |
| `MAX_CHARS_PER_POST`| `8000`   | Max content length sent to Claude        |
| `CLAUDE_MODEL`      | `claude-sonnet-4-20250514` | Which Claude model to use  |

## Cost

- **GitHub Actions**: Free tier gives 2,000 min/month; this uses ~2 min/day
- **Claude API**: ~$0.01–0.05/day depending on post count and length
- **Total**: Effectively free for personal use

## Troubleshooting

- **No posts found**: Check that your `feeds.json` URLs are correct. Try opening `https://yourblog.substack.com/feed` in a browser.
- **Email not sending**: Verify your SMTP credentials. For Gmail, make sure you're using an App Password, not your account password.
- **Action not running**: GitHub may delay scheduled actions by up to 15 minutes. Use manual trigger to test immediately.
