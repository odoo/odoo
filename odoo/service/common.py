import logging
from collections.abc import Callable
from typing import Any

import psycopg

import odoo.api
import odoo.release
from odoo.db import PoolError
from odoo.exceptions import AccessDenied
from odoo.libs.debug_log import DebugLog
from odoo.modules.registry import Registry

from ._dispatch import dispatch_through_table, is_db_rpc_exposed

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_EXPECTED_CONNECT_FAILURES: tuple[type[BaseException], ...] = (
    psycopg.OperationalError,
    psycopg.errors.InvalidCatalogName,
    PoolError,
)


def _get_rpc_version_1() -> dict[str, Any]:
    return {
        "server_version": odoo.release.version,
        "server_version_info": odoo.release.version_info,
        "server_serie": odoo.release.serie,
        "protocol_version": 1,
    }


def exp_login(db: str, login: str, password: str) -> int | bool:
    return exp_authenticate(db, login, password, None)


def exp_authenticate(
    db: str,
    login: str,
    password: str,
    user_agent_env: dict | None = None,
) -> int | bool:
    if not isinstance(db, str) or not db:
        _debug.logic("rpc.authenticate.rejected", reason="db_type")
        return False
    if not isinstance(login, str) or not isinstance(password, str):
        _debug.logic("rpc.authenticate.rejected", reason="credential_type", db=db)
        return False
    if user_agent_env is None:
        user_agent_env = {}
    elif not isinstance(user_agent_env, dict):
        _debug.logic("rpc.authenticate.rejected", reason="user_agent_env_type", db=db)
        return False
    if not is_db_rpc_exposed(db):
        _debug.logic("rpc.authenticate.db_not_exposed", db=db)
        return False
    try:
        registry = Registry(db)
    except (psycopg.Error, PoolError) as exc:
        _debug.logic(
            "rpc.authenticate.registry_unavailable",
            db=db,
            error=type(exc).__name__,
            expected=isinstance(exc, _EXPECTED_CONNECT_FAILURES),
        )
        if isinstance(exc, _EXPECTED_CONNECT_FAILURES):
            _logger.debug(
                "exp_authenticate: registry unavailable for %r", db, exc_info=True
            )
        else:
            _logger.warning(
                "exp_authenticate: unexpected database error for %r; answering "
                "False to keep the RPC response uniform",
                db,
                exc_info=True,
            )
        return False
    if "res.users" not in registry.models:
        _logger.debug("exp_authenticate: %r is reachable but not an Odoo database", db)
        _debug.logic("rpc.authenticate.not_odoo_db", db=db)
        return False
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, None, {})  # type: ignore[arg-type]
        env.transaction.default_env = env
        try:
            credential = {
                "login": login,
                "password": password,
                "type": "password",
            }
            _debug.lifecycle("rpc.authenticate", db=db, login=login)
            with _debug.perf("rpc.authenticate.checked", cr=cr, db=db) as span:
                uid: int | bool = env["res.users"].authenticate(
                    credential, {**user_agent_env, "interactive": False}
                )["uid"]
                span.set(uid=uid)
            return uid
        except AccessDenied:
            _debug.logic("rpc.authenticate.denied", db=db, login=login)
            return False


def exp_version() -> dict[str, Any]:
    _debug.pipeline("rpc.version", version=odoo.release.version)
    return _get_rpc_version_1()


def dispatch(method: str, params: list | tuple) -> Any:
    _debug.pipeline("rpc.common.dispatch", method=method)
    return dispatch_through_table(method, params, _DISPATCH)


_DISPATCH: dict[str, Callable] = {
    "login": exp_login,
    "authenticate": exp_authenticate,
    "version": exp_version,
}


__all__ = (
    "dispatch",
    "exp_authenticate",
    "exp_login",
    "exp_version",
)
