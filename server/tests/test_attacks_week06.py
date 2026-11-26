"""Week 6 hostile reviewer: attacks 2 and 3 tried as tests (ai_log_06.md).

They print what the server answered instead of asserting, so the same file can be run against
the code before and after the fix. Trendyol refuses the bot from this network, so the product
is added with fetch_product_info() monkeypatched, as in test_products.py.
"""

import uuid

from fastapi.testclient import TestClient

from server import products
from server.course_login import auth_header_for_tests
from server.main import app

client = TestClient(app)
JBL = "https://www.trendyol.com/jbl/tune-520bt-p-123456789"


def someone(name: str) -> dict[str, str]:
    return auth_header_for_tests(client, f"{name}-{uuid.uuid4().hex[:8]}@example.com")


def a_product_of(headers: dict[str, str], monkeypatch) -> int:
    monkeypatch.setattr(
        products,
        "fetch_product_info",
        lambda link, site: {"name": "JBL Tune 520BT Kulaklık", "image": "", "price": 1299.0},
    )
    return client.post("/products", json={"link": JBL}, headers=headers).json()["id"]


def test_attack_2_a_target_price_that_is_not_a_number(monkeypatch):
    a = someone("a")
    product_id = a_product_of(a, monkeypatch)
    for value in ["nan", "inf"]:
        response = client.patch(
            f"/products/{product_id}/target", json={"target_price": value}, headers=a
        )
        print(
            f"\nPATCH /products/{product_id}/target {value!r} -> {response.status_code} {response.json()}"
        )


def test_attack_3_another_users_product_by_id(monkeypatch):
    a, b = someone("a"), someone("b")
    product_id = a_product_of(a, monkeypatch)
    response = client.post(f"/products/{product_id}/check", headers=b)
    print(f"\nB: POST /products/{product_id}/check -> {response.status_code} {response.json()}")
    response = client.patch(f"/products/{product_id}/target", json={"target_price": 1}, headers=b)
    print(f"B: PATCH /products/{product_id}/target 1 -> {response.status_code} {response.json()}")
