from __future__ import annotations

import hashlib

import psycopg
from psycopg.conninfo import conninfo_to_dict

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

_NON_RETRYABLE_CONNECT_ERRORS: tuple[type[psycopg.Error], ...] = (
    psycopg.errors.InvalidCatalogName,
    psycopg.errors.InvalidAuthorizationSpecification,
    psycopg.errors.InvalidPassword,
)


_LOCALE_INDEPENDENT_AUTH_MARKERS: tuple[str, ...] = ("pg_hba.conf",)

_ENGLISH_ABSENT_DB_MARKERS: tuple[tuple[str, ...], ...] = (
    ('database "', "does not exist"),
)

_ENGLISH_AUTH_MARKERS: tuple[tuple[str, ...], ...] = (
    ("password authentication failed",),
    ('role "', "does not exist"),
    ("is not permitted to log in",),
)


def _resolve_connect_error(exc: psycopg.OperationalError) -> psycopg.Error | None:
    msg = str(exc).lower()
    if any(marker in msg for marker in _LOCALE_INDEPENDENT_AUTH_MARKERS):
        _debug.logic("dsn.connect_error_classified", as_="auth", by="pg_hba")
        return psycopg.errors.InvalidAuthorizationSpecification(str(exc))
    if any(all(part in msg for part in group) for group in _ENGLISH_ABSENT_DB_MARKERS):
        _debug.logic("dsn.connect_error_classified", as_="absent_db", by="english")
        return psycopg.errors.InvalidCatalogName(str(exc))
    if any(all(part in msg for part in group) for group in _ENGLISH_AUTH_MARKERS):
        _debug.logic("dsn.connect_error_classified", as_="auth", by="english")
        return psycopg.errors.InvalidAuthorizationSpecification(str(exc))
    _debug.logic("dsn.connect_error_classified", as_="unclassified")
    return None


def _expand_conninfo(info: dict | str) -> dict:
    if isinstance(info, str):
        return conninfo_to_dict(info)
    raw = info.get("dsn")
    keywords = {k: v for k, v in info.items() if k != "dsn"}
    return {**conninfo_to_dict(raw), **keywords} if raw else keywords


def _get_dsn_key(dsn: dict | str) -> frozenset:
    dsn = _expand_conninfo(dsn)
    password = dsn.get("password")
    if password:
        pw_fp = hashlib.blake2s(str(password).encode(), digest_size=8).hexdigest()
    else:
        pw_fp = ""
    items = ((k, str(v)) for k, v in dsn.items() if k != "password" and v is not None)
    key = frozenset((*items, ("password_fp", pw_fp)))
    _debug.logic(
        "dsn.key_built",
        db=dsn.get("dbname"),
        host=dsn.get("host"),
        keys=len(key) - 1,
        password=bool(password),
    )
    return key


def _get_key_dbname(key: frozenset) -> str:
    for name, value in key:
        if name == "dbname":
            return value
    return ""
