"""JWT authentication for service-to-service calls (HS256 shared secret).

The Odoo addon mints a short-lived (60 s) JWT and calls
``POST /v1/extract`` with ``Authorization: Bearer <token>``. This module is
the FastAPI side of that contract:

* ``require_token`` is wired as ``Depends(require_token)`` on every
  authenticated route (``/v1/extract``). ``/healthz`` stays open so the
  compose healthcheck never needs a token.
* Verification: ``jwt.decode(token, SECRET, algorithms=['HS256'],
  audience='invoice-ai')``. An **audience** is mandatory so a token minted
  for another service (wrong ``aud``) is rejected even with the correct
  secret — the shared-secret HS256 world has no public/private key
  separation, so the audience is the only thing scoping one service's
  tokens away from another's.
* Clock skew: ``leeway=10`` absorbs a few seconds of drift between the Odoo
  host and the container clock without widening the exploit window
  meaningfully (tokens still die after ~70 s max).
* Every failure — missing token, malformed, expired, bad signature, wrong
  audience — returns a single ``401 Unauthorized`` with the OpenAPI
  ``ErrorEnvelope`` shape. We never leak *why* a token was rejected to the
  caller (it is a machine client; the reason belongs in the server log).
* The shared secret lives in ``INVOICE_AI_JWT_SECRET`` (env / .env), never
  in source — mirrors how the Odoo side keeps it in ``ir.config_parameter``.

Why HS256 and not RS256 here: this is an internal service-to-service
boundary inside one VPC, where the two hosts share a secret out-of-band
(via ``ir.config_parameter`` on the Odoo side and env on the service). RS256
buys key rotation without secret distribution, but the operational cost and
the key-distribution problem are not justified at this trust boundary.
"""

import logging

from fastapi import Header, HTTPException, status

from .config import settings

_logger = logging.getLogger(__name__)

AUTH_HEADER_SCHEME = "Bearer"


class AuthenticationError(Exception):
    """Raised internally by token validation; mapped to 401 by require_token."""


def _require_token(
    authorization: str | None = Header(default=None),
) -> dict:
    """FastAPI dependency: validate a Bearer JWT, return its decoded claims.

    Returns the payload dict (callers can read ``sub`` / ``iss`` for
    auditability). Raises ``HTTPException 401`` on any failure — the same
    envelope the Odoo client already parses for its config-error path.

    The secret/audience are read from ``settings`` at call time (not bound
    as default argument values) so tests can swap ``settings.jwt_secret``
    before minting a real signed token.
    """
    secret = settings.jwt_secret
    audience = settings.jwt_audience

    if not secret:
        _logger.error(
            "invoice-ai JWT_SECRET is not configured — refusing all "
            "authenticated requests",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "E4011",
                    "message": "Service is not configured for JWT auth",
                }
            },
        )

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "E4011",
                    "message": "Missing Authorization header",
                }
            },
        )

    scheme, _separator, token = authorization.partition(" ")
    if scheme.lower() != AUTH_HEADER_SCHEME.lower() or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "E4011",
                    "message": "Expected 'Authorization: Bearer <token>'",
                }
            },
        )

    try:
        return _decode(token, secret=secret, audience=audience)
    except AuthenticationError as exc:
        _logger.warning(
            "invoice-ai rejected JWT: %s (audience=%s)",
            exc,
            audience,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "E4011",
                    "message": "Invalid or expired token",
                }
            },
        ) from exc


def _decode(token: str, *, secret: str, audience: str) -> dict:
    """Decode and validate a JWT, raising :class:`AuthenticationError`.

    Deliberately a module-level function (not nested inside the dependency)
    so the contract tests can import it directly and re-raise the underlying
    ``ExpiredSignatureError`` / ``InvalidTokenError`` classes exactly as the
    brief demands.
    """
    import jwt
    from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=audience,
            leeway=10,
        )
    except ExpiredSignatureError as exc:
        raise AuthenticationError("expired signature") from exc
    except InvalidTokenError as exc:
        raise AuthenticationError("invalid token") from exc


# The dependency function FastAPI resolves. Exposed as a module attribute so
# tests can ``app.dependency_overrides[require_token]`` it.
require_token = _require_token


__all__ = ["AuthenticationError", "require_token"]
