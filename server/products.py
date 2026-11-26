"""server/products.py: tracked products — REQ-002 (add by link), REQ-003 (target price and
price-drop notifications) and the start of REQ-004 (timestamped price readings).

The server fetches the product's name, image and current price straight from the product
page. The actual HTTP fetch lives in fetch_product_info() so a test can monkeypatch it
instead of hitting the real site from GitHub Actions.

Week 6: in-memory storage, one list per logged-in user. From Week 8 this moves to a file or
a database so it survives a server restart. REQ-004's own 6-hour automatic check (the
scheduler) is not built yet; POST /products/{id}/check and POST /price-check are the manual
trigger ASSIGNMENT_06 §1 (and REQ-003's acceptance) asks for this week.
"""

from __future__ import annotations

import itertools
import json
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.course_login import current_user

router = APIRouter()

SITES = {
    "trendyol.com": "Trendyol",
    "hepsiburada.com": "Hepsiburada",
}

UNSUPPORTED_SITE = "Desteklenmeyen site. Bu link desteklenen online mağazalardan birine ait değil."
EMPTY_TARGET = "Bir hedef fiyat yaz: örneğin 1100."

_products: dict[str, list[dict[str, Any]]] = {}  # user e-mail -> their tracked products
_notifications: dict[str, list[dict[str, Any]]] = {}  # user e-mail -> their notifications
_next_id = itertools.count(1)
_next_notification_id = itertools.count(1)
_last_checked_at: str | None = None  # REQ-004: when a price check last ran, for any user

DB_FILE = Path(__file__).parent / "data.json"


def _load_db() -> None:
    """Loads products and notifications from disk if data.json exists."""
    global _last_checked_at, _next_id, _next_notification_id
    if not DB_FILE.is_file():
        return
    try:
        data = json.loads(DB_FILE.read_text(encoding="utf-8"))
        _products.clear()
        _products.update(data.get("products", {}))
        _notifications.clear()
        _notifications.update(data.get("notifications", {}))
        _last_checked_at = data.get("last_checked_at")

        max_p_id = max(
            (p["id"] for prods in _products.values() for p in prods if isinstance(p, dict) and "id" in p),
            default=0,
        )
        _next_id = itertools.count(max_p_id + 1)

        max_n_id = max(
            (n["id"] for notifs in _notifications.values() for n in notifs if isinstance(n, dict) and "id" in n),
            default=0,
        )
        _next_notification_id = itertools.count(max_n_id + 1)
    except Exception:
        pass


def _save_db() -> None:
    """Persists products, notifications, and last_checked_at to data.json."""
    data = {
        "products": _products,
        "notifications": _notifications,
        "last_checked_at": _last_checked_at,
    }
    try:
        tmp = DB_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DB_FILE)
    except Exception:
        pass


_load_db()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def site_for(link: str) -> str | None:
    """The site's display name for a product link, or None when it is not supported."""
    # urlsplit reads the host the way requests does, so "http://127.0.0.1#.trendyol.com" is
    # 127.0.0.1, not a Trendyol page (week06 ai_log, attack 1: SSRF).
    parts = urlsplit(link.strip())
    host = (parts.hostname or "").removeprefix("www.")
    if parts.scheme not in ("http", "https") or parts.port is not None:
        return None
    for domain, name in SITES.items():
        if host == domain or host.endswith("." + domain):
            return name
    return None


def fetch_product_info(link: str, site: str) -> dict[str, Any]:
    """Reads the product's name, image and price straight off its page.

    A real network call — this is what a test replaces with monkeypatch.setattr(products,
    "fetch_product_info", ...) so GitHub Actions never has to reach Trendyol or Hepsiburada.
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; FiyatAvciBot/1.0)"}
    try:
        response = requests.get(link, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502, detail=f"{site} ürün sayfasına erişilemedi."
        ) from error

    soup = BeautifulSoup(response.text, "lxml")

    def meta(prop: str) -> str | None:
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        value = tag.get("content") if tag else None
        return value.strip() if isinstance(value, str) and value.strip() else None

    name = meta("og:title")
    if not name and soup.title and soup.title.string:
        name = soup.title.string.strip()
    image = meta("og:image") or ""

    price_text = meta("product:price:amount") or meta("og:price:amount")
    if not price_text:
        match = re.search(r'"price"\s*:\s*"?([\d.,]+)"?', response.text)
        price_text = match.group(1) if match else None

    if not name or not price_text:
        raise HTTPException(status_code=502, detail=f"{site} ürün bilgisi sayfadan okunamadı.")

    return {"name": name, "image": image, "price": _parse_price(price_text)}


def _parse_price(text: str) -> float:
    """Reads a price from either machine-readable text (meta tags, JSON-LD: "425.70", a plain
    decimal point) or a Turkish-formatted display string ("1.299,00" or "425,70", a comma for
    the decimal part). Only a comma is ever the decimal separator; a dot is one only when no
    comma is present too."""
    cleaned = text.strip().replace(" ", "").replace("TL", "").replace("₺", "")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return round(float(cleaned), 2)
    except ValueError as error:
        raise HTTPException(status_code=502, detail="Fiyat sayfadan okunamadı.") from error


class NewProductLink(BaseModel):
    link: str


class NewTarget(BaseModel):
    target_price: float | str | None = None


def _find(user: str, product_id: int) -> dict[str, Any]:
    for product in _products.get(user, []):
        if product["id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Böyle bir ürün yok.")


@router.post("/products", status_code=201)
def add_product(body: NewProductLink, user: str = Depends(current_user)) -> dict:
    """REQ-002: adds a product to the logged-in user's tracking list from its link."""
    link = body.link.strip()
    site = site_for(link) if link else None
    if not link or site is None:
        raise HTTPException(status_code=422, detail=UNSUPPORTED_SITE)

    info = fetch_product_info(link, site)
    now = _now()
    product = {
        "id": next(_next_id),
        "link": link,
        "site": site,
        "name": info["name"],
        "image": info["image"],
        "price": info["price"],
        "target_price": None,
        "notified": False,
        "checked_at": now,
        "readings": [{"price": info["price"], "at": now}],
    }
    _products.setdefault(user, []).append(product)
    _save_db()
    return product


@router.get("/products")
def list_products(user: str = Depends(current_user)) -> list[dict]:
    """REQ-002 / REQ-011: the logged-in user's own tracked products, no one else's."""
    return _products.get(user, [])


@router.patch("/products/{product_id}/target")
def set_target(product_id: int, body: NewTarget, user: str = Depends(current_user)) -> dict:
    """REQ-003: sets (or changes) a tracked product's target price."""
    product = _find(user, product_id)
    try:
        value = float(str(body.target_price).strip().replace(",", "."))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail=EMPTY_TARGET) from None
    if not math.isfinite(value) or value <= 0:  # "nan" and "inf" are floats too
        raise HTTPException(status_code=422, detail=EMPTY_TARGET)
    product["target_price"] = value
    if product["price"] > value:
        product["notified"] = False  # a fresh target above the current price: a real new watch
    _save_db()
    return product


def _check_one(user: str, product: dict[str, Any]) -> dict | None:
    """Re-reads one product's price, records it, and returns a new notification if the price
    just reached its target (REQ-003: never twice for the same drop)."""
    info = fetch_product_info(product["link"], product["site"])
    product["price"] = info["price"]
    product["name"] = info["name"]
    product["image"] = info["image"] or product["image"]
    product["checked_at"] = _now()
    product["readings"].append({"price": info["price"], "at": product["checked_at"]})

    target = product.get("target_price")
    if target is None:
        return None
    if info["price"] > target:
        product["notified"] = False  # back above target: a later drop may notify again
        return None
    if product["notified"]:
        return None  # already notified for this drop

    product["notified"] = True
    notification = {
        "id": next(_next_notification_id),
        "product_id": product["id"],
        "product_name": product["name"],
        "price": product["price"],
        "target_price": target,
        "message": f"{product['name']} şimdi {product['price']} TL (hedefin: {target} TL).",
        "at": product["checked_at"],
    }
    _notifications.setdefault(user, []).insert(0, notification)
    _save_db()
    return notification


@router.post("/products/{product_id}/check")
def check_one_product(product_id: int, user: str = Depends(current_user)) -> dict:
    """REQ-003 / REQ-004: manually re-checks one product's price now (ASSIGNMENT_06 §1: 'fiyat
    kontrolü elle tetiklenir'). The 6-hour automatic check is not built yet."""
    global _last_checked_at
    product = _find(user, product_id)
    notification = _check_one(user, product)
    _last_checked_at = product["checked_at"]
    _save_db()
    return {"product": product, "notification": notification}


@router.post("/price-check")
def check_all_products(user: str = Depends(current_user)) -> dict:
    """REQ-004: manually re-checks every one of the logged-in user's products at once."""
    global _last_checked_at
    notified = []
    for product in _products.get(user, []):
        notification = _check_one(user, product)
        if notification:
            notified.append(notification)
    _last_checked_at = _now()
    _save_db()
    return {"checked": len(_products.get(user, [])), "notified": notified, "at": _last_checked_at}


@router.get("/price-check/status")
def check_status(user: str = Depends(current_user)) -> dict:
    """REQ-004: when a price check last ran, for the 'Son kontrol: ...' note on the home page.
    Login required like every other route: without a token, 401."""
    return {"last_checked_at": _last_checked_at}


@router.get("/notifications")
def list_notifications(user: str = Depends(current_user)) -> list[dict]:
    """REQ-003: the logged-in user's own price-drop notifications, newest first."""
    return _notifications.get(user, [])


def reset_for_tests() -> None:
    """For your own tests: forgets every tracked product and notification, for every user."""
    global _last_checked_at, _next_id, _next_notification_id
    _products.clear()
    _notifications.clear()
    _last_checked_at = None
    _next_id = itertools.count(1)
    _next_notification_id = itertools.count(1)
    if DB_FILE.is_file():
        try:
            DB_FILE.unlink()
        except OSError:
            pass
