from __future__ import annotations

from hashlib import sha256
import hmac
import time

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from ..config import get_settings


router = APIRouter()

TERMINAL_TOKEN_TTL_SECONDS = 60
LOCALHOST_HOSTS = {"127.0.0.1", "::1", "localhost"}


class TerminalTokenRequest(BaseModel):
    uid: int = Field(gt=0)


def _signature(secret: str, uid: int, issued_at: int) -> str:
    payload = f"{uid}:{issued_at}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()


def build_terminal_token(secret: str, uid: int, issued_at: int | None = None) -> str:
    issued = issued_at or int(time.time())
    return f"{uid}:{issued}:{_signature(secret, uid, issued)}"


def validate_terminal_token(secret: str, token: str | None) -> tuple[bool, int | None]:
    if not token:
        return False, None

    try:
        uid_text, issued_at_text, signature = token.split(":", 2)
        uid = int(uid_text)
        issued_at = int(issued_at_text)
    except (AttributeError, TypeError, ValueError):
        return False, None

    now = int(time.time())
    if issued_at > now + TERMINAL_TOKEN_TTL_SECONDS:
        return False, None
    if now - issued_at > TERMINAL_TOKEN_TTL_SECONDS:
        return False, None

    expected_signature = _signature(secret, uid, issued_at)
    if not hmac.compare_digest(signature, expected_signature):
        return False, None
    return True, uid


def ensure_internal_request(request: Request, internal_secret: str | None) -> None:
    client_host = request.client.host if request.client else None
    if client_host not in LOCALHOST_HOSTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Terminal token endpoint only accepts localhost requests",
        )
    if not internal_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Forge-Internal header",
        )
    if not hmac.compare_digest(internal_secret, get_settings().terminal_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-Forge-Internal header",
        )


@router.post("/terminal/token")
async def issue_terminal_token(
    payload: TerminalTokenRequest,
    request: Request,
    x_forge_internal: str | None = Header(default=None, alias="X-Forge-Internal"),
) -> dict[str, object]:
    ensure_internal_request(request, x_forge_internal)
    token = build_terminal_token(get_settings().terminal_secret, payload.uid)
    return {
        "token": token,
        "expires_in": TERMINAL_TOKEN_TTL_SECONDS,
    }
