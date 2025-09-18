"""HTTP layer constants."""

import time

# The validity duration of a preflight response, one day.
CORS_MAX_AGE = 60 * 60 * 24

# The HTTP methods that do not require a CSRF validation.
SAFE_HTTP_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")

# The default csrf token lifetime, a salt against BREACH, one year
CSRF_TOKEN_SALT = 60 * 60 * 24 * 365

# The default lang to use when the browser doesn't specify it
DEFAULT_LANG = "en_US"


def get_default_session():
    """The dictionary to initialise a new session with."""
    return {
        "context": {},  # 'lang': request.default_lang()  # must be set at runtime
        "create_time": time.time(),
        "db": None,
        "debug": "",
        "login": None,
        "uid": None,
        "session_token": None,
        "_trace": [],
    }


DEFAULT_MAX_CONTENT_LENGTH = 128 * 1024 * 1024  # 128MiB

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

NOT_FOUND_NODB = """\
<!DOCTYPE html>
<title>404 Not Found</title>
<h1>Not Found</h1>
<p>No database is selected and the requested URL was not found in the server-wide controllers.</p>
<p>Please verify the hostname, <a href=/web/login>login</a> and try again.</p>

<!-- Alternatively, use the X-Odoo-Database header. -->
"""

# The @route arguments to propagate from the decorated method to the
# routing rule.
ROUTING_KEYS = {
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

# The default duration of a user session cookie. Inactive sessions are reaped
# server-side as well with a threshold that can be set via an optional
# config parameter `sessions.max_inactivity_seconds` (default: SESSION_LIFETIME)
SESSION_LIFETIME = 60 * 60 * 24 * 7

# The default duration (3h) before a session is rotated, changing the
# session id (also on the cookie) but keeping the same content.
SESSION_ROTATION_INTERVAL = 60 * 60 * 3

# After a session is rotated, the session should be kept for a couple of
# seconds to account for network delay between multiple requests which are
# made at the same time and all use the same old cookie.
SESSION_DELETION_TIMER = 120

# The amount of bytes of the session that will remain static and can be used
# for calculating the csrf token and be stored inside the database.
STORED_SESSION_BYTES = 42

# The cache duration for static content from the filesystem, one week.
STATIC_CACHE = 60 * 60 * 24 * 7

# The cache duration for content where the url uniquely identifies the
# content (usually using a hash), one year.
STATIC_CACHE_LONG = 60 * 60 * 24 * 365


# GeoIP empty objects - only available if geoip2 is installed
try:
    import geoip2.database
    import geoip2.errors
    import geoip2.models

    GEOIP_EMPTY_COUNTRY = geoip2.models.Country(None)
    GEOIP_EMPTY_CITY = geoip2.models.City(None)
except ImportError:
    geoip2 = None
    GEOIP_EMPTY_COUNTRY = None
    GEOIP_EMPTY_CITY = None

try:
    import maxminddb
except ImportError:
    maxminddb = None
