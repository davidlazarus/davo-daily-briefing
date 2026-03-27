# Davo's Daily Briefing Agent — Setup Guide

## Overview

This agent runs on Railway, fetches data from 5 sources every morning at 5am AEST,
uses GPT-4o to synthesize a briefing, and emails it to you.

**Sources:** Google Calendar, Gmail, Trello, Plaud, RUNNA
**Delivery:** Email via SendGrid to both davidlazarus89@gmail.com and david@kojador.com

---

## Step 1: Google Cloud Setup (Calendar + Gmail)

This gives the agent read-only access to your calendar and inbox.

### 1.1 Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown (top bar) → **New Project**
3. Name it `davo-briefing-agent` → **Create**
4. Make sure this new project is selected in the dropdown

### 1.2 Enable APIs

1. Go to **APIs & Services → Library** (left sidebar)
2. Search for and enable each of these:
   - **Google Calendar API** → Click → **Enable**
   - **Gmail API** → Click → **Enable**

### 1.3 Create OAuth Credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth Client ID**
3. If prompted to configure consent screen:
   - Choose **External** → Create
   - App name: `Davo Briefing Agent`
   - User support email: your email
   - Developer contact: your email
   - Click **Save and Continue** through all screens
   - Under **Test users**, add `davidlazarus89@gmail.com`
   - Click **Save and Continue** → **Back to Dashboard**
4. Now go back to **Credentials → + Create Credentials → OAuth Client ID**
5. Application type: **Desktop app**
6. Name: `briefing-agent`
7. Click **Create**
8. **Download the JSON** → save as `credentials.json` in the project folder

### 1.4 Generate a Refresh Token

Run this one-time script on your local machine (NOT on Railway):

```bash
cd davo-daily-briefing
pip install google-auth-oauthlib
python get_google_token.py
```

This opens a browser, you log in, grant permissions, and it prints your refresh token.
Copy the three values into your `.env`:

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

---

## Step 2: Trello API Setup

1. Go to [trello.com/power-ups/admin](https://trello.com/power-ups/admin)
2. Click **New** → Create a new Power-Up/integration
3. Name: `Davo Briefing` / any name
4. After creating, go to the **API Key** section
5. Copy your **API Key**
6. Click the link to generate a **Token** (authorize read access)
7. Get your **Board ID**: open your Trello board in browser, the URL looks like
   `https://trello.com/b/BOARD_ID/board-name` — copy that BOARD_ID

```
TRELLO_API_KEY=your-key
TRELLO_TOKEN=your-token
TRELLO_BOARD_ID=your-board-id
```

**Important:** Make sure your Trello columns are named by day: "Monday", "Tuesday", etc.
The agent matches by day name. If they're named differently (e.g., "Mon" or "Mon 31 Mar"),
let me know and I'll adjust the matching logic.

---

## Step 3: Plaud Auth Token

1. Go to [web.plaud.ai](https://web.plaud.ai) and log in
2. Open browser DevTools (F12 or Cmd+Option+I)
3. Go to **Application** tab → **Local Storage** → `web.plaud.ai`
4. Find the key `tokenstr` — copy its value (starts with `eyJ...`)
5. Add to your `.env`:

```
PLAUD_AUTH_TOKEN=eyJ...your-token-here
```

**Note:** This token lasts ~300 days. If the briefing stops showing Plaud data,
grab a fresh token.

---

## Step 4: RUNNA Credentials

Just your login email and password. The agent uses a headless browser to scrape
your training plan.

```
RUNNA_EMAIL=your-runna-email
RUNNA_PASSWORD=your-runna-password
```

**Heads up:** This is the most fragile integration. If RUNNA changes their web app,
the scraper may break. I've built it to fail gracefully — if RUNNA fails, the rest
of the briefing still works fine.

---

## Step 5: SendGrid (Email Delivery)

1. Sign up at [sendgrid.com](https://sendgrid.com) (free tier = 100 emails/day, plenty)
2. Go to **Settings → API Keys → Create API Key**
3. Give it **Full Access** or at least **Mail Send** permission
4. Copy the key

```
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=briefing@kojador.com
```

**Sender verification:** SendGrid requires you verify the "from" address.
Go to **Settings → Sender Authentication** and either:
- Verify a single sender email (quick, use briefing@kojador.com or your gmail)
- Or set up domain authentication for kojador.com (better for deliverability)

---

## Step 6: OpenAI API Key

1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create a new key → Copy it

```
OPENAI_API_KEY=sk-...
```

---

## Step 7: Final .env Config

```
BRIEFING_EMAILS=davidlazarus89@gmail.com,david@kojador.com
BRIEFING_HOUR=5
BRIEFING_MINUTE=0
TIMEZONE=Australia/Melbourne
ARLO_REFERENCE_DATE=2026-03-27
```

**ARLO_REFERENCE_DATE:** Set this to any date that IS an Arlo day.
The agent alternates every other day from this reference.
Is March 27, 2026 an Arlo day for you? If not, change to a date that is.

---

## Step 8: Test Locally

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Copy and fill in your .env
cp .env.example .env
# Edit .env with your values

# Dry run (prints briefing to console, doesn't send email)
python main.py --test

# Full run (generates + sends email)
python main.py
```

---

## Step 9: Deploy to Railway

1. Push this project to a GitHub repo (private recommended)
2. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub Repo**
3. Select your repo
4. Railway will detect the Procfile and nixpacks config automatically
5. Go to **Variables** tab → add ALL your `.env` variables
6. Railway will build and start the worker process
7. The scheduler runs continuously and fires the briefing at 5am AEST daily

**Verify it's running:** Check Railway logs — you should see:
```
Scheduler started. Briefing will run daily at 05:00 Australia/Melbourne
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| No calendar events | Check Google refresh token hasn't expired. Re-run `get_google_token.py` |
| Trello empty | Verify board ID and column names match day names |
| Plaud error | Token expired — grab a fresh one from web.plaud.ai DevTools |
| RUNNA error | Scraper may be broken. Check if RUNNA changed their UI. Non-critical. |
| Email not arriving | Check SendGrid dashboard for bounces. Verify sender authentication. |
| Wrong Arlo days | Update ARLO_REFERENCE_DATE to a confirmed Arlo day |
