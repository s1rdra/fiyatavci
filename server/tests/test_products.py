"""Tests for REQ-002 (week04/test_cases.json TC-002-01, TC-002-02): tracking a product by
pasting its Trendyol or Hepsiburada link.

fetch_product_info() is monkeypatched: the real network call is tested by hand (§1 of
ASSIGNMENT_06), not from GitHub Actions.
"""

import uuid

from fastapi.testclient import TestClient

from server import products
from server.course_login import auth_header_for_tests
from server.main import app

client = TestClient(app)


def someone(name: str) -> dict[str, str]:
    """A new user, logged in through the real login: the header with their token."""
    return auth_header_for_tests(client, f"{name}-{uuid.uuid4().hex[:8]}@example.com")


def test_TC_002_01_a_trendyol_link_adds_the_product(monkeypatch):
    products.reset_for_tests()
    monkeypatch.setattr(
        products,
        "fetch_product_info",
        lambda link, site: {
            "name": "JBL Tune 520BT Kulaklık",
            "image": "https://cdn.example.com/jbl-tune-520bt.jpg",
            "price": 1299.0,
        },
    )
    headers = someone("deniz")

    response = client.post(
        "/products",
        json={"link": "https://www.trendyol.com/jbl/tune-520bt-p-123456789"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["site"] == "Trendyol"
    assert body["name"] == "JBL Tune 520BT Kulaklık"
    assert body["price"] == 1299.0

    listed = client.get("/products", headers=headers)
    assert listed.status_code == 200
    assert any(p["id"] == body["id"] for p in listed.json())


def test_TC_002_02_an_unsupported_site_link_is_refused():
    products.reset_for_tests()
    headers = someone("mia")

    response = client.post(
        "/products",
        json={"link": "https://www.amazon.com.tr/dp/B0TEST1234"},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == products.UNSUPPORTED_SITE


def test_TC_002_02_a_link_that_only_pretends_to_be_trendyol_is_refused(monkeypatch):
    """week06 ai_log, attack 1 (SSRF): the server must never fetch an address of its own."""
    products.reset_for_tests()
    fetched = []
    monkeypatch.setattr(products, "fetch_product_info", lambda link, site: fetched.append(link))
    headers = someone("mia")

    for link in [
        "http://127.0.0.1:8000#.trendyol.com",
        "https://www.trendyol.com@127.0.0.1/p-1",
        "https://www.trendyol.com:8443/p-1",
        "file:///etc/passwd#.trendyol.com",
    ]:
        response = client.post("/products", json={"link": link}, headers=headers)

        assert response.status_code == 422, link
        assert response.json()["detail"] == products.UNSUPPORTED_SITE
    assert fetched == []


def test_TC_003_01_a_target_price_starts_tracking(monkeypatch):
    products.reset_for_tests()
    monkeypatch.setattr(
        products,
        "fetch_product_info",
        lambda link, site: {"name": "JBL Tune 520BT Kulaklık", "image": "", "price": 1299.0},
    )
    headers = someone("deniz")
    added = client.post(
        "/products",
        json={"link": "https://www.trendyol.com/jbl/tune-520bt-p-123456789"},
        headers=headers,
    ).json()

    response = client.patch(
        f"/products/{added['id']}/target", json={"target_price": 1100}, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["target_price"] == 1100.0

    listed = client.get("/products", headers=headers).json()
    assert listed[0]["price"] == 1299.0
    assert listed[0]["target_price"] == 1100.0


def test_TC_003_02_an_empty_target_price_is_refused(monkeypatch):
    products.reset_for_tests()
    monkeypatch.setattr(
        products,
        "fetch_product_info",
        lambda link, site: {"name": "JBL Tune 520BT Kulaklık", "image": "", "price": 1299.0},
    )
    headers = someone("mia")
    added = client.post(
        "/products",
        json={"link": "https://www.trendyol.com/jbl/tune-520bt-p-123456789"},
        headers=headers,
    ).json()

    response = client.patch(
        f"/products/{added['id']}/target", json={"target_price": ""}, headers=headers
    )

    assert response.status_code == 422
    assert response.json()["detail"] == products.EMPTY_TARGET


def test_TC_003_02_a_target_price_that_is_not_a_number_is_refused(monkeypatch):
    """week06 ai_log, attack 2: "nan" never notifies and "inf" notifies at once."""
    products.reset_for_tests()
    monkeypatch.setattr(
        products,
        "fetch_product_info",
        lambda link, site: {"name": "JBL Tune 520BT Kulaklık", "image": "", "price": 1299.0},
    )
    headers = someone("mia")
    added = client.post(
        "/products",
        json={"link": "https://www.trendyol.com/jbl/tune-520bt-p-123456789"},
        headers=headers,
    ).json()

    for value in ["nan", "inf", "-inf", "abc"]:
        response = client.patch(
            f"/products/{added['id']}/target", json={"target_price": value}, headers=headers
        )

        assert response.status_code == 422, value
    assert client.get("/products", headers=headers).json()[0]["target_price"] is None


def test_TC_003_03_a_price_at_or_below_target_notifies_once(monkeypatch):
    products.reset_for_tests()
    prices = iter([32_600.0, 32_499.0, 32_499.0])
    monkeypatch.setattr(
        products,
        "fetch_product_info",
        lambda link, site: {
            "name": "Monster Abra A5 V21 Laptop",
            "image": "",
            "price": next(prices),
        },
    )
    headers = someone("arda")
    added = client.post(
        "/products",
        json={"link": "https://www.hepsiburada.com/monster-abra-a5-v21-p-1"},
        headers=headers,
    ).json()
    client.patch(f"/products/{added['id']}/target", json={"target_price": 32_500}, headers=headers)

    first_check = client.post(f"/products/{added['id']}/check", headers=headers)
    assert first_check.json()["notification"]["message"] == (
        "Monster Abra A5 V21 Laptop şimdi 32499.0 TL (hedefin: 32500.0 TL)."
    )

    second_check = client.post(f"/products/{added['id']}/check", headers=headers)
    assert second_check.json()["notification"] is None  # aynı düşüş için ikinci bildirim yok

    notifications = client.get("/notifications", headers=headers).json()
    assert len(notifications) == 1
    assert notifications[0]["product_name"] == "Monster Abra A5 V21 Laptop"


def test_TC_011_01_a_user_cannot_see_or_change_another_users_products(monkeypatch):
    products.reset_for_tests()
    monkeypatch.setattr(
        products,
        "fetch_product_info",
        lambda link, site: {"name": "JBL Tune 520BT Kulaklık", "image": "", "price": 1299.0},
    )
    deniz, ali = someone("deniz"), someone("ali")
    added = client.post(
        "/products",
        json={"link": "https://www.trendyol.com/jbl/tune-520bt-p-123456789"},
        headers=deniz,
    )
    product_id = added.json()["id"]

    listed = client.get("/products", headers=ali)
    assert listed.status_code == 200
    assert all(p["id"] != product_id for p in listed.json())

    changed = client.patch(f"/products/{product_id}/target", json={"target_price": 1}, headers=ali)
    assert changed.status_code == 404

    mine = client.get("/products", headers=deniz).json()
    assert [p["target_price"] for p in mine if p["id"] == product_id] == [None]
