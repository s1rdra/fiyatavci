# FiyatAvcı — Price Tracker

Paste a Trendyol or Hepsiburada product link, set a target price, and FiyatAvcı tells you when the price drops to it — with a price history so you can see whether a "discount" is real.

Built solo as the term project of an **AI-Assisted Software Development** course: an Android app, a web client and a Python backend.

<!-- Screenshots: add mobile/web screenshots to docs/ and link them here -->

## Features
- **Price scraping** — reads product name, image and price from public product pages (Open Graph / structured data, with a fallback parser)
- **Target-price alerts** — every price check is stored as a reading; an in-app notification fires when the price hits the target
- **Price history** — per-product readings to check whether a discount is genuine
- **AI shopping assistant** — chat backed by an OpenAI-compatible LLM API (Gemini / Groq), given only the logged-in user's own products as context, with a per-user daily message limit
- **Passwordless login** — one-time 4-digit e-mail code with expiry, rate limiting and lockout (login module provided by the course)
- **Two clients, one API** — Flutter Android app and a lightweight web client, both talking only to the REST API

## Security
The backend went through a hostile review; the attacks were reproduced as tests (`server/tests/test_attacks_week06.py`) and fixed:
- **SSRF** — product links are validated by parsed hostname, scheme and port, so tricks like `http://127.0.0.1#.trendyol.com` are rejected before any request is made
- **IDOR** — every product route is scoped to the logged-in user, so user B cannot check or edit user A's product by guessing its ID
- **Input validation** — non-numeric target prices such as `nan` / `inf` are rejected
- **Data isolation** — the LLM prompt contains only the current user's products: no e-mails, links or other users' data
- **Abuse limits** — per-user daily cap on chat messages (HTTP 429)
- Secrets live in `.env` (never committed); see `server/.env.example`

## Tech stack
| Part | Tech |
|---|---|
| Mobile | Flutter (Dart), `http` |
| Web | HTML, CSS, JavaScript |
| Server | Python, FastAPI, Pydantic |
| Scraping | requests, BeautifulSoup, lxml |
| AI | OpenAI-compatible chat API (Gemini / Groq) |
| Testing | pytest |

## Run locally
```bash
pip install fastapi uvicorn pydantic requests beautifulsoup4 lxml python-dotenv
cp server/.env.example server/.env   # add your LLM_API_KEY
uvicorn server.main:app --reload
```
- API docs: http://127.0.0.1:8000/docs
- Web client: http://127.0.0.1:8000/web
- Mobile: `cd mobile && flutter run` (Android emulator reaches the server at `10.0.2.2:8000`)
