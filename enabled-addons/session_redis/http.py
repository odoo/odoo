# Copyright 2016-2024 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
import functools
import logging
import os

from odoo import http
from odoo.tools import config

from .session import RedisSessionStore
from .strtobool import strtobool

_logger = logging.getLogger(__name__)

try:
    import redis
    from redis.sentinel import Sentinel
except ImportError:
    redis = None  # noqa
    _logger.debug("Cannot 'import redis'.")


def is_true(strval):
    return bool(strtobool(strval or "0".lower()))


sentinel_host = os.getenv("ODOO_SESSION_REDIS_SENTINEL_HOST")
sentinel_master_name = os.getenv("ODOO_SESSION_REDIS_SENTINEL_MASTER_NAME")
if sentinel_host and not sentinel_master_name:
    raise Exception(
        "ODOO_SESSION_REDIS_SENTINEL_MASTER_NAME must be defined "
        "when using session_redis"
    )
sentinel_port = int(os.getenv("ODOO_SESSION_REDIS_SENTINEL_PORT", 26379))
host = os.getenv("ODOO_SESSION_REDIS_HOST", "localhost")
port = int(os.getenv("ODOO_SESSION_REDIS_PORT", 6379))
prefix = os.getenv("ODOO_SESSION_REDIS_PREFIX")
url = os.getenv("ODOO_SESSION_REDIS_URL")
password = os.getenv("ODOO_SESSION_REDIS_PASSWORD")
expiration = os.getenv("ODOO_SESSION_REDIS_EXPIRATION")
anon_expiration = os.getenv("ODOO_SESSION_REDIS_EXPIRATION_ANONYMOUS")
# For non url connections
ssl = os.getenv("ODOO_SESSION_REDIS_SSL", "1")
ssl_cert_reqs = os.getenv("ODOO_SESSION_REDIS_SSL_CERT_REQS", "1")
redis_cluster = os.getenv("ODOO_SESSION_REDIS_CLUSTER", "0")


@functools.cached_property
def session_store(self):
    if sentinel_host:
        sentinel = Sentinel([(sentinel_host, sentinel_port)], password=password)
        redis_client = sentinel.master_for(sentinel_master_name)
    elif url:
        redis_client = redis.from_url(url)
    elif is_true(redis_cluster):
        redis_client = redis.RedisCluster(
            host=host,
            port=port,
            password=password,
            ssl=is_true(ssl),
            ssl_cert_reqs=is_true(ssl_cert_reqs),
        )
    else:
        redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            ssl=is_true(ssl),
            ssl_cert_reqs=is_true(ssl_cert_reqs),
        )
    return RedisSessionStore(
        redis=redis_client,
        prefix=prefix,
        expiration=expiration,
        anon_expiration=anon_expiration,
        session_class=http.Session,
    )


def purge_fs_sessions(path):
    if not os.path.isdir(path):
        _logger.warning(f"Session directory '{path}' does not exist.")
        return

    for fname in os.listdir(path):
        path = os.path.join(path, fname)
        try:
            os.unlink(path)
        except OSError:
            _logger.warning("OS Error during purge of redis sessions.")


if is_true(os.getenv("ODOO_SESSION_REDIS")):
    if sentinel_host:
        _logger.debug(
            "HTTP sessions stored in Redis with prefix '%s'. Using Sentinel on %s:%s",
            prefix or "",
            sentinel_host,
            sentinel_port,
        )
    else:
        _logger.debug(
            "HTTP sessions stored in Redis with prefix '%s' on %s:%s",
            prefix or "",
            host,
            port,
        )
    http.Application.session_store = session_store
    # cached_property needs __set_name__ to be called, but it is not called
    # automatically since we are attaching the property after instance creation.
    # So we have to do it manually
    # See: https://docs.python.org/3/reference/datamodel.html#object.__set_name__
    # Credit: https://stackoverflow.com/a/62161136
    http.Application.session_store.__set_name__(
        http.Application,
        "session_store",
    )
    # clean the existing sessions on the file system
    purge_fs_sessions(config.session_dir)
