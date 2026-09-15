import functools
import logging
import re
from collections.abc import Iterable

import psycopg

import odoo.service.db
from odoo.db import is_maintenance_db
from odoo.db import settings as pool_settings
from odoo.libs.debug_log import DebugLog

from .core import request
from .settings import current as current_settings

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def invalidate_db_catalog_cache() -> None:
    odoo.service.db.invalidate_catalog_caches()
    _debug.lifecycle("http.db_catalog.invalidated")


def get_dbs_served(force: bool = False, host: str | None = None) -> list[str]:
    env = request.env if request else None
    cr = env.cr if env is not None else None
    try:
        with _debug.perf("http.dbs.list", force=force) as span:
            dbs = odoo.service.db.list_dbs(force, cr=cr)
            span.set(dbs=len(dbs))
    except psycopg.Error:
        _logger.warning(
            "Could not list databases; answering as though this instance serves none.",
            exc_info=True,
        )
        _debug.logic("http.dbs.list_failed", force=force)
        return []
    return filter_dbs_served(dbs, host)


def _normalize_dbfilter_host(host: str) -> str:
    if host.startswith("["):
        end = host.find("]")
        if end != -1:
            host = host[: end + 1]
        return host.lower()
    return host.partition(":")[0].lower().removeprefix("www.")


@functools.lru_cache(maxsize=8)
def _has_host_placeholder(pattern: str) -> bool:
    return "%h" in pattern or "%d" in pattern


@functools.lru_cache(maxsize=512)
def _compile_dbfilter(pattern: str, host: str) -> re.Pattern[str]:
    domain = host.partition(".")[0]
    return re.compile(
        pattern.replace("%h", re.escape(host)).replace("%d", re.escape(domain))
    )


def filter_dbs_served(dbs: Iterable[str], host: str | None = None) -> list[str]:
    settings = current_settings()
    pool = pool_settings.current()
    names = [db for db in dbs if not is_maintenance_db(db, pool)]

    pattern = settings.dbfilter
    if pattern:
        if _has_host_placeholder(pattern):
            if host is None:
                host = (
                    request.httprequest.environ.get("HTTP_HOST", "") if request else ""
                )
            host = _normalize_dbfilter_host(host)
        else:
            host = ""
        dbfilter_re = _compile_dbfilter(pattern, host)
        names = [db for db in names if dbfilter_re.match(db)]

    if settings.db_name:
        exposed = set(settings.db_name)
        names = [db for db in names if db in exposed]

    _debug.logic(
        "http.dbfilter",
        host=host,
        pattern=pattern or None,
        db_name=len(settings.db_name or ()),
        served=len(names),
    )
    return names
