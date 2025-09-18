import functools
import logging
import threading
from urllib.parse import urlencode, urlparse

import werkzeug.routing
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_

import odoo.tools
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.modules import module as module_manager
from odoo.service.server import thread_local
from odoo.tools import config, file_path
from odoo.tools.misc import real_time, submap

from .constants import (
    ROUTING_KEYS,
    geoip2,
    maxminddb,
)
from .core import _request_stack
from .exceptions import RegistryError, SessionExpiredException
from .request_class import Request
from .routing import _generate_routing_rules
from .session import FilesystemSessionStore, Session
from .wrappers import HTTPRequest

_logger = logging.getLogger(__name__)

# Cached ProxyFix instance — we only use it for the side effect of
# rewriting environ keys (X-Forwarded-For/Proto/Host), no need to
# instantiate a new middleware on every request.
_proxy_fix = ProxyFix_(
    lambda environ, start_response: [],
    x_for=1, x_proto=1, x_host=1,
)


def _noop_start_response(status, headers):
    """No-op start_response for ProxyFix."""


class Application:
    """Odoo WSGI application"""

    # See also: https://www.python.org/dev/peps/pep-3333

    def initialize(self):
        """
        Initialize the application.

        This is to be called when setting up a WSGI application after
        initializing the configuration values.
        """
        module_manager.initialize_sys_path()
        from odoo.service.server import load_server_wide_modules

        load_server_wide_modules()

    def static_path(self, module_name: str) -> str | None:
        """
        Map module names to their absolute ``static`` path on the file
        system.
        """
        manifest = module_manager.Manifest.for_addon(module_name, display_warning=False)
        return manifest.static_path if manifest is not None else None

    def get_static_file(self, url, host=""):
        """
        Get the full-path of the file if the url resolves to a local
        static file, otherwise return None.

        Without the second host parameters, ``url`` must be an absolute
        path, others URLs are considered faulty.

        With the second host parameters, ``url`` can also be a full URI
        and the authority found in the URL (if any) is validated against
        the given ``host``.
        """

        netloc, path = urlparse(url)[1:3]
        try:
            path_netloc, module, static, resource = path.split("/", 3)
        except ValueError:
            return None

        if (netloc and netloc != host) or (path_netloc and path_netloc != host):
            return None

        if not (static == "static" and resource):
            return None

        static_path = self.static_path(module)
        if not static_path:
            return None

        try:
            return file_path(f"{static_path}/{resource}")
        except FileNotFoundError:
            return None

    @functools.cached_property
    def nodb_routing_map(self):
        nodb_routing_map = werkzeug.routing.Map(strict_slashes=False, converters=None)
        for url, endpoint in _generate_routing_rules(
            [""] + config["server_wide_modules"], nodb_only=True
        ):
            routing = submap(endpoint.routing, ROUTING_KEYS)
            if routing["methods"] is not None and "OPTIONS" not in routing["methods"]:
                routing["methods"] = [*routing["methods"], "OPTIONS"]
            rule = werkzeug.routing.Rule(url, endpoint=endpoint, **routing)
            rule.merge_slashes = False
            nodb_routing_map.add(rule)

        return nodb_routing_map

    @functools.cached_property
    def session_store(self):
        path = odoo.tools.config.session_dir
        _logger.debug("HTTP sessions stored in: %s", path)
        return FilesystemSessionStore(path, session_class=Session, renew_missing=True)

    def get_db_router(self, db):
        from . import request  # lazy import

        if not db:
            return self.nodb_routing_map
        return request.env["ir.http"].routing_map()

    @functools.cached_property
    def geoip_city_db(self):
        try:
            return geoip2.database.Reader(config["geoip_city_db"])
        except OSError, maxminddb.InvalidDatabaseError:
            _logger.debug(
                "Couldn't load Geoip City file at %s. IP Resolver disabled.",
                config["geoip_city_db"],
                exc_info=True,
            )
            raise

    @functools.cached_property
    def geoip_country_db(self):
        try:
            return geoip2.database.Reader(config["geoip_country_db"])
        except (OSError, maxminddb.InvalidDatabaseError) as exc:
            _logger.debug(
                "Couldn't load Geoip Country file (%s). Fallbacks on Geoip City.",
                exc,
            )
            raise

    def set_csp(self, response):
        headers = response.headers
        headers["X-Content-Type-Options"] = "nosniff"

        if "Content-Security-Policy" in headers:
            return

        if not headers.get("Content-Type", "").startswith("image/"):
            return

        headers["Content-Security-Policy"] = "default-src 'none'"

    def __call__(self, environ, start_response):
        """
        WSGI application entry point.

        :param dict environ: container for CGI environment variables
            such as the request HTTP headers, the source IP address and
            the body as an io file.
        :param callable start_response: function provided by the WSGI
            server that this application must call in order to send the
            HTTP response status line and the response headers.
        """
        current_thread = threading.current_thread()
        current_thread.query_count = 0
        current_thread.query_time = 0
        current_thread.perf_t0 = real_time()
        current_thread.cursor_mode = None
        if hasattr(current_thread, "dbname"):
            del current_thread.dbname
        if hasattr(current_thread, "uid"):
            del current_thread.uid
        thread_local.rpc_model_method = ""

        if odoo.tools.config["proxy_mode"] and environ.get("HTTP_X_FORWARDED_HOST"):
            # The ProxyFix middleware has a side effect of updating the
            # environ, see https://github.com/pallets/werkzeug/pull/2184
            _proxy_fix(environ, _noop_start_response)

        with HTTPRequest(environ) as httprequest:
            request = Request(httprequest)
            _request_stack.push(request)

            try:
                request._post_init()
                current_thread.url = httprequest.url

                if self.get_static_file(httprequest.path):
                    response = request._serve_static()
                elif request.db:
                    try:
                        with request._get_profiler_context_manager():
                            response = request._serve_db()
                    except RegistryError as e:
                        _logger.warning(
                            "Database or registry unusable, trying without",
                            exc_info=e.__cause__,
                        )
                        request.db = None
                        request.session.logout()
                        if httprequest.path.startswith(
                            "/odoo/"
                        ) or httprequest.path in (
                            "/odoo",
                            "/web",
                            "/web/login",
                            "/test_http/ensure_db",
                        ):
                            # ensure_db() protected routes, remove ?db= from the query string
                            args_nodb = request.httprequest.args.copy()
                            args_nodb.pop("db", None)
                            request.reroute(
                                httprequest.path,
                                urlencode(list(args_nodb.items(multi=True))),
                            )
                        response = request._serve_nodb()
                else:
                    response = request._serve_nodb()
                return response(environ, start_response)

            except Exception as exc:
                # Logs the error here so the traceback starts with ``__call__``.
                if hasattr(exc, "loglevel"):
                    _logger.log(
                        exc.loglevel,
                        exc,
                        exc_info=getattr(exc, "exc_info", None),
                    )
                elif isinstance(exc, HTTPException):
                    pass
                elif isinstance(exc, SessionExpiredException):
                    _logger.info(exc)
                elif isinstance(exc, AccessError):
                    _logger.warning(exc, exc_info="access" in config["dev_mode"])
                elif isinstance(exc, UserError):
                    _logger.warning(exc)
                else:
                    _logger.exception("Exception during request handling.")

                # Ensure there is always a WSGI handler attached to the exception.
                if not hasattr(exc, "error_response"):
                    if isinstance(exc, AccessDenied):
                        exc.suppress_traceback()
                    exc.error_response = request.dispatcher.handle_error(exc)

                return exc.error_response(environ, start_response)

            finally:
                _request_stack.pop()


root = Application()
