"""Minimal bearer-token auth: enough to show the pattern without a JWT dependency."""

from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass

# A demo token store. A real service would persist hashed tokens with an expiry.
_TOKENS: dict[str, str] = {}


@dataclass(slots=True, frozen=True)
class Principal:
    name: str
    role: str = "user"

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def issue_token(name: str, role: str = "user") -> str:
    token = secrets.token_urlsafe(32)
    _TOKENS[token] = f"{name}:{role}"
    return token


def resolve(token: str) -> Principal | None:
    """Constant-time comparison against every stored token."""
    for stored, value in _TOKENS.items():
        if hmac.compare_digest(stored, token):
            name, _, role = value.partition(":")
            return Principal(name, role)
    return None


def reset() -> None:
    """Only for tests."""
    _TOKENS.clear()
