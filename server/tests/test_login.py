"""Login tests (REQ-001), one for each test case in week04/test_cases.json.

The course's own ten tests in course_tests/ check that the login is wired correctly; these
three check our test cases against the real login (server/course_login.py).
"""

from fastapi.testclient import TestClient

from server.course_login import reset_for_tests
from server.main import app

client = TestClient(app)


def _send_code(monkeypatch, tmp_path, email: str) -> str:
    code_file = tmp_path / "code.txt"
    monkeypatch.setenv("AIASD_CODE_FILE", str(code_file))
    response = client.post("/auth/code", json={"email": email})
    assert response.status_code == 200
    return code_file.read_text(encoding="utf-8").strip()


def test_TC_001_01_a_code_is_sent_and_the_right_code_logs_in(monkeypatch, tmp_path):
    reset_for_tests()
    code = _send_code(monkeypatch, tmp_path, "deniz@example.com")

    response = client.post("/auth/login", json={"email": "deniz@example.com", "code": code})

    assert response.status_code == 200
    assert "token" in response.json()


def test_TC_001_02_a_wrong_code_is_refused(monkeypatch, tmp_path):
    reset_for_tests()
    real_code = _send_code(monkeypatch, tmp_path, "mia@example.com")
    wrong_code = "0000" if real_code != "0000" else "1111"

    response = client.post("/auth/login", json={"email": "mia@example.com", "code": wrong_code})

    assert response.status_code == 401


def test_TC_001_03_three_wrong_codes_lock_the_email(monkeypatch, tmp_path):
    reset_for_tests()
    real_code = _send_code(monkeypatch, tmp_path, "arda@example.com")
    wrong_code = "0000" if real_code != "0000" else "1111"

    for _ in range(3):
        client.post("/auth/login", json={"email": "arda@example.com", "code": wrong_code})

    response = client.post("/auth/login", json={"email": "arda@example.com", "code": real_code})

    assert response.status_code == 429
