"""Google Play review account: lets the Play reviewer log in without reading an e-mail.

Off unless both PLAY_REVIEW_EMAIL and PLAY_REVIEW_CODE are set in server/.env:

    PLAY_REVIEW_EMAIL=review@fiyatavci.app
    PLAY_REVIEW_CODE=2468

For that one address the server sends no e-mail and the code is always PLAY_REVIEW_CODE.
Every other address works exactly as course_login.py says. course_login.py itself is not
changed: this only swaps the dict that holds the waiting codes.
"""

from __future__ import annotations

import os

from server import course_login


class _ReviewPending(dict):
    """course_login's waiting codes; the review address always gets the fixed code."""

    def __init__(self, email: str, code: str) -> None:
        super().__init__()
        self._email = email
        self._code = code

    def __setitem__(self, email: str, pending: course_login._Pending) -> None:
        if email == self._email:
            pending = course_login._Pending(code=self._code, sent_at=pending.sent_at)
        super().__setitem__(email, pending)


def enable() -> bool:
    """Turns the review account on when .env asks for it. Returns whether it is on."""
    email = os.environ.get("PLAY_REVIEW_EMAIL", "").strip().lower()
    code = os.environ.get("PLAY_REVIEW_CODE", "").strip()
    if not email or not (len(code) == 4 and code.isdigit()):
        return False
    course_login._pending = _ReviewPending(email, code)
    send = course_login._deliver

    def deliver(to: str, code_sent: str) -> None:
        if to != email:  # the review address has no inbox: nothing to send
            send(to, code_sent)

    course_login._deliver = deliver
    return True
