import time
from collections.abc import Iterable

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

CORS_MAX_AGE = 60 * 60 * 24

SAFE_HTTP_METHODS = ("GET", "HEAD", "OPTIONS")

DEFAULT_ALLOWED_METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE")

STATIC_ALLOWED_METHODS = ("GET", "HEAD")
"""What a ``/<module>/static/<path>`` URL answers.

A file on disk is a read-only resource, and the static branch runs ahead of the
router, so no route can ever narrow it: whatever this names is what the whole
static tree accepts.
"""


def prepare_allow_header(methods: Iterable[str] | None = None) -> str:
    if methods is None:
        methods = DEFAULT_ALLOWED_METHODS
    normalized = dict.fromkeys(method.upper() for method in methods)
    if "GET" in normalized:
        normalized.setdefault("HEAD", None)
    normalized.setdefault("OPTIONS", None)
    return ", ".join(normalized)


CORS_DEFAULT_ALLOWED_HEADERS = (
    "Origin, X-Requested-With, Content-Type, Accept, Authorization, Range"
)
"""What a preflight allows when the client names no `Access-Control-Request-Headers`.

This list is NOT a ceiling. Without `@route(cors_allow_headers=...)` the
preflight deliberately echoes whatever headers the client asked for — the
origin was already vetted before any of this is emitted, so restricting header
names would add friction without adding a boundary. The list above only
answers a preflight that asks for nothing. A route that needs a real
allow-list declares one with `cors_allow_headers=`.
"""

REJECTED_HTTP_METHODS = ("TRACE",)

CSRF_TOKEN_MAX_AGE = 60 * 60 * 24 * 365

DEFAULT_LANG = "en_US"


def prepare_default_session() -> dict[str, object]:
    return {
        "context": {},
        "create_time": time.time(),
        "db": None,
        "debug": "",
        "login": None,
        "uid": None,
        "session_token": None,
        "_trace": [],
    }


DEFAULT_MAX_CONTENT_LENGTH = 128 * 1024 * 1024

DEFAULT_MAX_FORM_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_MAX_FORM_PARTS = 10_000

WILDCARD_CORS_CREDENTIALS_WARNING = """\
Refusing to send credentials to the wildcard origin for path %r

The route declares cors_credentials and its cors resolver returned '*' for
this request. The CORS specification forbids combining
Access-Control-Allow-Origin: * with Access-Control-Allow-Credentials: true,
so no CORS headers were sent at all. Return the caller's own origin from the
resolver instead of '*', for instance with odoo.http.resolve_cors_same_host.
"""

MISSING_CSRF_WARNING = """\
No CSRF validation token provided for path %r

Odoo URLs are CSRF-protected by default (when accessed with unsafe
HTTP methods). See
https://www.odoo.com/documentation/master/developer/reference/addons/http.html#csrf
for more details.

* if this endpoint is accessed through Odoo via py-QWeb form, embed a CSRF
  token in the form, Tokens are available via `request.csrf_token()`
  can be provided through a hidden input and must be POST-ed named
  `csrf_token` e.g. in your form add:
      <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>

* if the form is generated or posted in javascript, the token value is
  available as `csrf_token` on `web.core` and as the `csrf_token`
  value in the default js-qweb execution context

* if the form is accessed by an external third party (e.g. REST API
  endpoint, payment gateway callback) you will need to disable CSRF
  protection (and implement your own protection if necessary) by
  passing the `csrf=False` parameter to the `route` decorator.
"""

_NODB_NOT_FOUND = (
    "No database is selected and the requested URL was not found in the "
    "server-wide controllers."
)

NOT_FOUND_NODB_TEXT = (
    f"{_NODB_NOT_FOUND} Verify the hostname, or name a database with the "
    "X-Odoo-Database header."
)

NOT_FOUND_NODB = f"""\
<!DOCTYPE html>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>{_NODB_NOT_FOUND}</p>
<p>Please verify the hostname, <a href=/web/login>login</a> and try again.</p>

<!-- Alternatively, use the X-Odoo-Database header. -->
"""
"""The same answer for a browser: `_serve_nodb` picks between the two by the
inferred dispatcher."""


SELECT_DB_PATHS: set[str] = set()
SELECT_DB_PATH_PREFIXES: tuple[str, ...] = ()
"""A tuple, not a set, because its only reader feeds it to ``str.startswith``.

``startswith`` takes a tuple and nothing else, so a set here means the sole
call site rebuilds one on every request that loses its database.
"""


def register_select_db_paths(*paths: str, prefixes: Iterable[str] = ()) -> None:
    global SELECT_DB_PATH_PREFIXES  # noqa: PLW0603  the module owns this registry
    SELECT_DB_PATHS.update(paths)
    SELECT_DB_PATH_PREFIXES = tuple(
        dict.fromkeys((*SELECT_DB_PATH_PREFIXES, *prefixes))
    )
    _debug.lifecycle(
        "http.select_db_paths.registered",
        paths=len(SELECT_DB_PATHS),
        prefixes=len(SELECT_DB_PATH_PREFIXES),
    )


def is_select_db_path(path: str) -> bool:
    return path in SELECT_DB_PATHS or path.startswith(SELECT_DB_PATH_PREFIXES)


ROUTING_KEYS = frozenset(
    {
        "defaults",
        "subdomain",
        "build_only",
        "strict_slashes",
        "redirect_to",
        "alias",
        "host",
        "methods",
        "websocket",
    }
)

SESSION_LIFETIME = 60 * 60 * 24 * 7

SESSION_ROTATION_INTERVAL = 60 * 60 * 3

SESSION_DELETION_TIMER = 120

SESSION_ROTATION_EXCLUDED_PATHS: set[str] = set()


def register_session_rotation_excluded_paths(*paths: str) -> None:
    SESSION_ROTATION_EXCLUDED_PATHS.update(paths)
    _debug.lifecycle(
        "http.session_rotation_excluded_paths.registered",
        paths=len(SESSION_ROTATION_EXCLUDED_PATHS),
    )


STORED_SESSION_BYTES = 42

STATIC_CACHE = 60 * 60 * 24 * 7

STATIC_CACHE_LONG = 60 * 60 * 24 * 365
