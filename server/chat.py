"""server/chat.py: the chatbot — POST /chat (REQ-014, week 8 change request).

Buying advice from the prices of the logged-in user's own tracked products. The phone
never talks to the LLM API: it sends the message here, this server adds the user's own
products and calls the LLM API, and only this server holds the key.

The key is read from server/.env (LLM_API_KEY=...), never from the code. Any provider with
an OpenAI-compatible chat endpoint works; pick it with LLM_BASE_URL and LLM_MODEL:

    Gemini: LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
            LLM_MODEL=gemini-flash-lite-latest
    Groq:   LLM_BASE_URL=https://api.groq.com/openai/v1
            LLM_MODEL=llama-3.3-70b-versatile

Errors (week05/api.md): 401 without a token (current_user), 429 after the daily limit,
503 when the LLM API does not answer within 20 seconds or answers with an error.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server import products
from server.course_login import current_user

load_dotenv()

router = APIRouter()

# REQ-014'ün kabul kriterindeki günlük mesaj sayısı: gereksinimine ne yazdıysan bunu ona eşitle.
DAILY_LIMIT = 20
LLM_TIMEOUT_SECONDS = 20

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = "gemini-flash-lite-latest"

# TASLAK: asistanın önerisi. Son metne sen karar ver.
SYSTEM_PROMPT = (
    "Sen FiyatAvcı uygulamasının alışveriş yardımcısısın. Kullanıcının takip ettiği ürünlerin "
    "şimdiki fiyatına, hedef fiyatına ve fiyat geçmişine bakarak 'şimdi al' ya da 'bekle' "
    "şeklinde kısa bir alım tavsiyesi ver ve nedenini fiyatlarla açıkla. Türkçe cevap ver. "
    "Yalnızca sana verilen ürün listesini kullan; listede olmayan fiyat ya da indirim uydurma. "
    "Gelecekteki fiyatı kesin bilemeyeceğini belirt. FiyatAvcı'daki ürünler dışındaki sorulara, "
    "yalnızca takip edilen ürünler hakkında yardım edebildiğini söyleyerek cevap ver."
)

LIMIT_MESSAGE = f"Bugünkü {DAILY_LIMIT} mesaj hakkını kullandın. Yarın yeniden deneyebilirsin."
UNAVAILABLE_MESSAGE = "Sohbet botu şu an cevap veremiyor. Biraz sonra yeniden dene."
EMPTY_MESSAGE = "Bir mesaj yaz."

_usage: dict[str, tuple[str, int]] = {}  # user e-mail -> (UTC day, messages sent that day)


class ChatMessage(BaseModel):
    message: str


def _count_message(user: str) -> None:
    """Counts one message for today; 429 once the user has used up the daily limit."""
    today = datetime.now(UTC).date().isoformat()
    day, count = _usage.get(user, (today, 0))
    if day != today:
        count = 0
    if count >= DAILY_LIMIT:
        raise HTTPException(status_code=429, detail=LIMIT_MESSAGE)
    _usage[user] = (today, count + 1)


def _user_context(user: str) -> str:
    """Only the logged-in user's own products: no e-mail, no link, no other user's data."""
    lines = []
    for product in products.list_products(user):
        target = product.get("target_price")
        target_text = f"{target} TL" if target is not None else "yok"
        readings = ", ".join(f"{r['price']} TL ({r['at'][:10]})" for r in product["readings"][-10:])
        lines.append(
            f"- {product['name']} ({product['site']}): şimdi {product['price']} TL, "
            f"hedef {target_text}; fiyat geçmişi: {readings}"
        )
    return "\n".join(lines) or "Kullanıcı henüz hiçbir ürünü takip etmiyor."


def ask_llm(messages: list[dict[str, str]]) -> str:
    """One call to the LLM API. A week 9 test replaces this with monkeypatch."""
    key = os.getenv("LLM_API_KEY")
    if not key:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_MESSAGE)
    base_url = (os.getenv("LLM_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    model = os.getenv("LLM_MODEL") or DEFAULT_MODEL
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": messages},
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError) as error:
        raise HTTPException(status_code=503, detail=UNAVAILABLE_MESSAGE) from error
    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(status_code=503, detail=UNAVAILABLE_MESSAGE)
    return answer.strip()


@router.post("/chat")
def chat(body: ChatMessage, user: str = Depends(current_user)) -> dict[str, Any]:
    """REQ-014: buying advice from the logged-in user's own tracked products."""
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail=EMPTY_MESSAGE)
    _count_message(user)
    answer = ask_llm(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": "Kullanıcının ürünleri:\n" + _user_context(user)},
            {"role": "user", "content": message[:2000]},
        ]
    )
    return {"answer": answer}


def reset_for_tests() -> None:
    """For your own tests: forgets every user's message count."""
    _usage.clear()
