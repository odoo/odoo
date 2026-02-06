from __future__ import annotations

import functools
import logging
import re
import threading
import typing
from os.path import join as opj
from urllib.parse import urlparse

import werkzeug.routing
from psycopg2 import OperationalError
from werkzeug.exceptions import HTTPException
from werkzeug.urls import url_encode  # TODO: use urllib

# TODO: drop the fallback
try:
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    ProxyFix = functools.partial(ProxyFix_, x_for=1, x_proto=1, x_host=1)
except ImportError:
    from werkzeug.contrib.fixers import ProxyFix

import odoo.modules.db
import odoo.service
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.modules.module import (
    Manifest,
    initialize_sys_path,
)
from odoo.service.server import thread_local
from odoo.tools import config, file_path, real_time
from odoo.tools.misc import submap

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from wsgiref.types import StartResponse, WSGIEnvironment

    from .response import Response

_logger = logging.getLogger('odoo.http')


def db_list(force: bool = False, host: str | None = None) -> list[str]:
    """
    Get the list of available databases.

    :param bool force: See :func:`~odoo.modules.db.list_dbs`
    :param host: The Host used to replace %h and %d in the dbfilters
        regexp. Taken from the current request when omitted.
    :returns: the list of available databases
    :rtype: List[str]
    """
    try:
        dbs = odoo.modules.db.list_dbs(force=force)
    except OperationalError:
        return []
    return db_filter(dbs, host)


def db_filter(dbs: Iterable[str], host: str | None = None) -> list[str]:
    """
    Return the subset of ``dbs`` that match the dbfilter or the dbname
    server configuration. In case neither are configured, return ``dbs``
    as-is.

    :param Iterable[str] dbs: The list of database names to filter.
    :param host: The Host used to replace %h and %d in the dbfilters
        regexp. Taken from the current request when omitted.
    :returns: The original list filtered.
    :rtype: List[str]
    """

    if config['dbfilter']:
        #        host
        #     -----------
        # www.example.com:80
        #     -------
        #     domain
        if host is None:
            host = request.httprequest.environ.get('HTTP_HOST', '')
        host = host.partition(':')[0]
        host = host.removeprefix('www.')
        domain = host.partition('.')[0]

        dbfilter_re = re.compile(
            config["dbfilter"].replace(R"%h", re.escape(host))
                              .replace(R"%d", re.escape(domain)))
        return [db for db in dbs if dbfilter_re.match(db)]

    if config['db_name']:
        # In case --db-filter is not provided and --database is passed, Odoo will
        # use the value of --database as a comma separated list of exposed databases.
        return sorted(set(config['db_name']).intersection(dbs))

    return list(dbs)


def dispatch_rpc(service_name: str, method: str, params: Mapping[str, typing.Any]) -> typing.Any:
    """
    Perform a RPC call.

    :param service_name: either "common", "db" or "object".
    :param method: the method name of the given service to execute
    :param params: the keyword arguments for method call
    :return: the return value of the called method
    """
    if service_name == 'object':
        dispatch = odoo.service.model.dispatch
    elif service_name == 'common':
        dispatch = odoo.service.common.dispatch
    else:
        raise ValueError(f"Invalid service name: {service_name}")

    with borrow_request():
        threading.current_thread().uid = None
        threading.current_thread().dbname = None

        return dispatch(method, params)


class RegistryError(RuntimeError):
    pass


class Application:
    """ Odoo WSGI application """
    # See also: https://www.python.org/dev/peps/pep-3333

    def initialize(self) -> None:
        """
        Initialize the application.

        This is to be called when setting up a WSGI application after
        initializing the configuration values.
        """
        initialize_sys_path()
        from odoo.service.server import load_server_wide_modules  # noqa: PLC0415
        load_server_wide_modules()

    def static_path(self, module_name: str) -> str | None:
        """
        Map module names to their absolute ``static`` path on the file
        system.
        """
        manifest = Manifest.for_addon(module_name, display_warning=False)
        return manifest.static_path if manifest is not None else None

    def get_static_file(self, url: str, host: str = '') -> str | None:
        """
        Get the full-path of the file if the url resolves to a local
        static file, otherwise return None.

        Without the second host parameters, ``url`` must be an absolute
        path, others URLs are considered faulty.

        With the second host parameters, ``url`` can also be a full URI
        and the authority found in the URL (if any) is validated against
        the given ``host``.
        """

        netloc, path = urlparse(url)[1:3]  # TODO: use urllib3
        try:
            path_netloc, module, static, resource = path.split('/', 3)
        except ValueError:
            return None

        if ((netloc and netloc != host) or (path_netloc and path_netloc != host)):
            return None

        if not (static == 'static' and resource):
            return None

        static_path = self.static_path(module)
        if not static_path:
            return None

        try:
            return file_path(opj(static_path, resource))
        except FileNotFoundError:
            return None

    @functools.cached_property
    def nodb_routing_map(self):
        nodb_routing_map = werkzeug.routing.Map(strict_slashes=False, converters=None)
        for url, endpoint in _generate_routing_rules([''] + config['server_wide_modules'], nodb_only=True):
            routing = submap(endpoint.routing, ROUTING_KEYS)
            if routing['methods'] is not None and 'OPTIONS' not in routing['methods']:
                routing['methods'] = [*routing['methods'], 'OPTIONS']
            rule = werkzeug.routing.Rule(url, endpoint=endpoint, **routing)
            rule.merge_slashes = False
            nodb_routing_map.add(rule)

        return nodb_routing_map

    @functools.cached_property
    def session_store(self):
        path = config.session_dir
        _logger.debug('HTTP sessions stored in: %s', path)
        return SessionStore(path=path)

    def get_db_router(self, db: str | None) -> werkzeug.routing.Map:
        if not db:
            return self.nodb_routing_map
        return request.env['ir.http'].routing_map()

    def set_csp(self, response: Response) -> None:
        headers = response.headers
        headers['X-Content-Type-Options'] = 'nosniff'

        if 'Content-Security-Policy' in headers:
            return

        if not headers.get('Content-Type', '').startswith('image/'):
            return

        headers['Content-Security-Policy'] = "default-src 'none'"

    def __call__(self, environ: WSGIEnvironment, start_response: StartResponse) -> Iterable[bytes]:
        """
        WSGI application entry point.

        :param environ: container for CGI environment variables
            such as the request HTTP headers, the source IP address and
            the body as an io file.
        :param start_response: function provided by the WSGI
            server that this application must call in order to send the
            HTTP response status line and the response headers.
        """
        current_thread = threading.current_thread()
        current_thread.query_count = 0
        current_thread.query_time = 0
        current_thread.perf_t0 = real_time()
        current_thread.cursor_mode = None
        if hasattr(current_thread, 'dbname'):
            del current_thread.dbname
        if hasattr(current_thread, 'uid'):
            del current_thread.uid
        thread_local.rpc_model_method = ''

        if config['proxy_mode'] and environ.get("HTTP_X_FORWARDED_HOST"):
            # The ProxyFix middleware has a side effect of updating the
            # environ, see https://github.com/pallets/werkzeug/pull/2184
            def fake_app(environ, start_response):
                return []
            def fake_start_response(status, headers):  # noqa: E301, E306
                return
            ProxyFix(fake_app)(environ, fake_start_response)

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
                        _logger.warning("Database or registry unusable, trying without", exc_info=e.__cause__)
                        # TODO: move those bits in a dedicated function
                        request.db = None
                        logout(request.session)
                        if (httprequest.path.startswith('/odoo/')
                            or httprequest.path in (
                                '/odoo', '/web', '/web/login', '/test_http/ensure_db',
                            )):
                            # ensure_db() protected routes, remove ?db= from the query string
                            args_nodb = request.httprequest.args.copy()
                            args_nodb.pop('db', None)
                            request.reroute(httprequest.path, url_encode(args_nodb))
                        response = request._serve_nodb()
                else:
                    response = request._serve_nodb()
                return response(environ, start_response)

            except Exception as exc:
                # Logs the error here so the traceback starts with ``__call__``.
                if hasattr(exc, 'loglevel'):
                    _logger.log(exc.loglevel, exc, exc_info=getattr(exc, 'exc_info', None))
                elif isinstance(exc, HTTPException):
                    pass
                elif isinstance(exc, SessionExpiredException):
                    _logger.info(exc)
                elif isinstance(exc, AccessError):
                    _logger.warning(exc, exc_info='access' in config['dev_mode'])
                elif isinstance(exc, UserError):
                    _logger.warning(exc)
                else:
                    _logger.exception("Exception during request handling.")

                # Ensure there is always a WSGI handler attached to the exception.
                if not hasattr(exc, 'error_response'):
                    if isinstance(exc, AccessDenied):
                        exc.suppress_traceback()
                    exc.error_response = request.dispatcher.handle_error(exc)

                return exc.error_response(environ, start_response)

            finally:
                _request_stack.pop()


root = Application()


# ruff: noqa: E402
from .requestlib import (
    HTTPRequest,
    Request,
    _request_stack,
    borrow_request,
    request,
)
from .routing_map import ROUTING_KEYS, _generate_routing_rules
from .session import SessionExpiredException, SessionStore, logout
