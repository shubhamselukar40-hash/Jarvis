# Jarvis — personal WhatsApp agent

Talks to you over WhatsApp, understands what you ask (via Claude), and acts:
summarizes unread email, checks/creates calendar events, and sets reminders
(one-off or recurring, like a water-drinking alarm) that fire in the
background even when you're not chatting.

## What you need (all free/cheap tiers)

1. **Anthropic API key** — console.anthropic.com
2. **Twilio account** (free trial works) with the **WhatsApp Sandbox** enabled
   — console.twilio.com → Messaging → Try it out → WhatsApp
3. **Google Cloud project** with Gmail API + Calendar API enabled, and an
   OAuth 2.0 Client ID (type: Web application) — console.cloud.google.com
4. **Railway** (or Render/Fly.io) account connected to your GitHub

## 1. Push this to GitHub

Create a new repo on GitHub (you can do this from the GitHub mobile app or
site), upload this folder's contents to it.

## 2. Deploy on Railway

- New Project → Deploy from GitHub repo → pick this repo
- Railway auto-detects the `Procfile` and installs `requirements.txt`
- Add all the environment variables from `.env.example` under Variables
  (Railway → your service → Variables tab)
- Once deployed, Railway gives you a public URL like
  `https://jarvis-production.up.railway.app`
- Set `GOOGLE_REDIRECT_URI` to `https://<that-url>/auth/google/callback`
  and update the same URI in your Google Cloud OAuth client's
  "Authorized redirect URIs"

## 3. Connect your Google account (one-time)

From your phone browser, visit:
`https://<your-app-url>/auth/google`

Log in, grant access. That's it — Jarvis stores a refresh token and won't
ask again.

## 4. Connect WhatsApp

In the Twilio console (WhatsApp Sandbox settings), set the
**"When a message comes in"** webhook to:
`https://<your-app-url>/webhook/whatsapp` (method: POST)

Then message the Twilio sandbox number from your phone with the join code
Twilio gives you (e.g. "join happy-tiger"). After that, anything you send
that number goes straight to Jarvis.

## 5. Talk to Jarvis

Examples:
- "summarize my unread emails"
- "what's on my calendar today"
- "add a meeting tomorrow 3pm to 4pm called DB review"
- "remind me to drink water every 2 hours"
- "remind me to check the backup job at 11pm tonight"

## Notes / limits of this first build

- **Single user only** — the webhook doesn't check the sender, so treat the
  webhook URL and your Twilio sandbox as private (don't share the URL).
- **Token storage**: the Google token is saved to a file on disk
  (`google_token.json`). On Railway's free tier the filesystem can reset on
  redeploy, so you may need to redo step 3 after a redeploy. If that gets
  annoying, next step would be storing the token in a small database or
  Railway's persistent volume — happy to add that.
- **Twilio sandbox** numbers expire after ~72 hours of inactivity (just
  re-join). For a permanent number you'd apply for a real WhatsApp Business
  sender later — not needed to get started.
- **Wake-up alarms**: currently implemented as a one-off or recurring
  reminder ("remind me at 7am tomorrow"). A true recurring daily alarm can
  be added as a specific `interval_minutes=1440` reminder or a cron-style
  trigger — say the word and I'll extend `scheduler.py`.

## Local testing (optional, needs a computer)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in real values
uvicorn app.main:app --reload
```
