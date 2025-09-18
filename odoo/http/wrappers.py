"""HTTP request and response wrappers."""

import functools
import logging
from datetime import datetime, timedelta

import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.wrappers
from werkzeug.exceptions import HTTPException

from odoo.libs._vendor.useragents import UserAgent
from odoo.libs.facade import Proxy, ProxyAttr, ProxyFunc

from .constants import DEFAULT_MAX_CONTENT_LENGTH

_logger = logging.getLogger(__name__)


def make_request_wrap_methods(attr):
    def getter(self):
        return getattr(self._HTTPRequest__wrapped, attr)

    def setter(self, value):
        return setattr(self._HTTPRequest__wrapped, attr, value)

    return getter, setter


class HTTPRequest:
    def __init__(self, environ):
        httprequest = werkzeug.wrappers.Request(environ)
        httprequest.user_agent_class = (
            UserAgent  # vendored: werkzeug removed its built-in parser
        )
        httprequest.parameter_storage_class = werkzeug.datastructures.ImmutableMultiDict
        httprequest.max_content_length = DEFAULT_MAX_CONTENT_LENGTH
        # Werkzeug 3.1 changed defaults from unlimited to 500 KB / 1000 parts.
        # Odoo needs 10 MB for base64 form fields, HTML content, and import data.
        # Odoo forms with One2many lines can exceed 1000 parts (e.g., 200 invoice
        # lines × 5+ fields each). Set to 10000 to match the memory size headroom.
        httprequest.max_form_memory_size = 10 * 1024 * 1024
        httprequest.max_form_parts = 10_000
        self._session_id__ = httprequest.cookies.get("session_id")

        self.__wrapped = httprequest
        self.__environ = self.__wrapped.environ
        self.environ = self.headers.environ = {
            key: value
            for key, value in self.__environ.items()
            if (
                not key.startswith(("werkzeug.", "wsgi.", "socket"))
                or key in ["wsgi.url_scheme", "werkzeug.proxy_fix.orig"]
            )
        }

    def __enter__(self):
        return self


HTTPREQUEST_ATTRIBUTES = [
    "__str__",
    "__repr__",
    "__exit__",
    "accept_charsets",
    "accept_languages",
    "accept_mimetypes",
    "access_route",
    "args",
    "authorization",
    "base_url",
    "content_encoding",
    "content_length",
    "content_md5",
    "content_type",
    "cookies",
    "data",
    "date",
    "files",
    "form",
    "full_path",
    "get_data",
    "get_json",
    "headers",
    "host",
    "host_url",
    "if_match",
    "if_modified_since",
    "if_none_match",
    "if_range",
    "if_unmodified_since",
    "is_json",
    "is_secure",
    "json",
    "max_content_length",
    "method",
    "mimetype",
    "mimetype_params",
    "origin",
    "path",
    "pragma",
    "query_string",
    "range",
    "referrer",
    "remote_addr",
    "remote_user",
    "root_path",
    "root_url",
    "scheme",
    "script_root",
    "server",
    "session",
    "trusted_hosts",
    "url",
    "url_root",
    "user_agent",
    "values",
]
for attr in HTTPREQUEST_ATTRIBUTES:
    setattr(HTTPRequest, attr, property(*make_request_wrap_methods(attr)))


class _Response(werkzeug.wrappers.Response):
    """
    Outgoing HTTP response with body, status, headers and qweb support.
    In addition to the :class:`werkzeug.wrappers.Response` parameters,
    this class's constructor can take the following additional
    parameters for QWeb Lazy Rendering.

    :param str template: template to render
    :param dict qcontext: Rendering context to use
    :param int uid: User id to use for the ir.ui.view render call,
        ``None`` to use the request's user (the default)

    these attributes are available as parameters on the Response object
    and can be altered at any time before rendering

    Also exposes all the attributes and methods of
    :class:`werkzeug.wrappers.Response`.
    """

    default_mimetype = "text/html"

    def __init__(self, *args, **kw):
        template = kw.pop("template", None)
        qcontext = kw.pop("qcontext", None)
        uid = kw.pop("uid", None)
        super().__init__(*args, **kw)
        self.set_default(template, qcontext, uid)

    @classmethod
    def load(cls, result, fname="<function>"):
        """
        Convert the return value of an endpoint into a Response.

        :param result: The endpoint return value to load the Response from.
        :type result: Response | werkzeug.wrappers.Response |
            werkzeug.exceptions.HTTPException | str | bytes | None
        :param str fname: The endpoint function name wherefrom the
            result emanated, used for logging.
        :returns: The created :class:`~odoo.http.Response`.
        :rtype: Response
        :raises TypeError: When ``result`` type is none of the above-
            mentioned type.
        """
        if isinstance(result, Response):
            return result

        if isinstance(result, werkzeug.exceptions.HTTPException):
            _logger.warning("%s returns an HTTPException instead of raising it.", fname)
            raise result

        if isinstance(result, werkzeug.wrappers.Response):
            response = cls.force_type(result)
            response.set_default()
            return response

        if isinstance(result, (bytes, str, type(None))):
            return Response(result)

        raise TypeError(f"{fname} returns an invalid value: {result}")

    def set_default(self, template=None, qcontext=None, uid=None):
        self.template = template
        self.qcontext = qcontext or {}
        self.qcontext["response_template"] = self.template
        self.uid = uid

    @property
    def is_qweb(self):
        return self.template is not None

    def render(self):
        """Renders the Response's template, returns the result."""
        from . import request  # lazy import

        self.qcontext["request"] = request
        return request.env["ir.ui.view"]._render_template(self.template, self.qcontext)

    def flatten(self):
        """
        Forces the rendering of the response's template, sets the result
        as response body and unsets :attr:`.template`
        """
        if self.template:
            self.response.append(self.render())
            self.template = None

    def set_cookie(
        self,
        key,
        value="",
        max_age=None,
        expires=-1,
        path="/",
        domain=None,
        secure=False,
        httponly=False,
        samesite=None,
        partitioned=False,
        cookie_type="required",
    ):
        """
        The default expires in Werkzeug is None, which means a session cookie.
        We want to continue to support the session cookie, but not by default.
        Now the default is arbitrary 1 year.
        So if you want a cookie of session, you have to explicitly pass expires=None.
        """
        from . import request  # lazy import

        if expires == -1:  # not provided value -> default value -> 1 year
            expires = datetime.now() + timedelta(days=365)

        if request.db and not request.env["ir.http"]._is_allowed_cookie(cookie_type):
            max_age = 0
        super().set_cookie(
            key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
            partitioned=partitioned,
        )


class Headers(Proxy):
    _wrapped__ = werkzeug.datastructures.Headers

    __getitem__ = ProxyFunc()
    __repr__ = ProxyFunc(str)
    __setitem__ = ProxyFunc(None)
    __str__ = ProxyFunc(str)
    __contains__ = ProxyFunc(bool)
    add = ProxyFunc(None)
    add_header = ProxyFunc(None)
    clear = ProxyFunc(None)
    copy = ProxyFunc(lambda v: Headers(v))  # noqa: PLW0108
    extend = ProxyFunc(None)
    get = ProxyFunc()
    get_all = ProxyFunc()
    getlist = ProxyFunc()
    items = ProxyFunc()
    keys = ProxyFunc()
    pop = ProxyFunc()
    popitem = ProxyFunc()
    remove = ProxyFunc(None)
    set = ProxyFunc(None)
    setdefault = ProxyFunc()
    setlist = ProxyFunc(None)
    setlistdefault = ProxyFunc()
    to_wsgi_list = ProxyFunc()
    update = ProxyFunc(None)
    values = ProxyFunc()


class ResponseCacheControl(Proxy):
    _wrapped__ = werkzeug.datastructures.ResponseCacheControl

    __getitem__ = ProxyFunc()
    __setitem__ = ProxyFunc(None)
    immutable = ProxyAttr(bool)
    max_age = ProxyAttr(int)
    must_revalidate = ProxyAttr(bool)
    must_understand = ProxyAttr(bool)
    no_cache = ProxyAttr(bool)
    no_store = ProxyAttr(bool)
    no_transform = ProxyAttr(bool)
    public = ProxyAttr(bool)
    private = ProxyAttr(bool)
    proxy_revalidate = ProxyAttr(bool)
    s_maxage = ProxyAttr(int)
    stale_if_error = ProxyAttr(int)
    stale_while_revalidate = ProxyAttr(int)
    pop = ProxyFunc()


class ResponseStream(Proxy):
    _wrapped__ = werkzeug.wrappers.ResponseStream

    write = ProxyFunc(int)
    writelines = ProxyFunc(None)
    tell = ProxyFunc(int)


class Response(Proxy):
    _wrapped__ = _Response

    # werkzeug.wrappers.Response attributes
    __call__ = ProxyFunc()
    add_etag = ProxyFunc(None)
    age = ProxyAttr()
    autocorrect_location_header = ProxyAttr(bool)
    cache_control = ProxyAttr(ResponseCacheControl)
    call_on_close = ProxyFunc()
    content_encoding = ProxyAttr(str)
    content_length = ProxyAttr(int)
    content_location = ProxyAttr(str)
    content_md5 = ProxyAttr(str)
    content_type = ProxyAttr(str)
    data = ProxyAttr()
    default_mimetype = ProxyAttr(str)
    default_status = ProxyAttr(int)
    delete_cookie = ProxyFunc(None)
    direct_passthrough = ProxyAttr(bool)
    expires = ProxyAttr()
    force_type = ProxyFunc(lambda v: Response(v))  # noqa: PLW0108
    freeze = ProxyFunc(None)
    get_data = ProxyFunc()
    get_etag = ProxyFunc()
    get_json = ProxyFunc()
    headers = ProxyAttr(Headers)
    is_json = ProxyAttr(bool)
    is_sequence = ProxyAttr(bool)
    is_streamed = ProxyAttr(bool)
    iter_encoded = ProxyFunc()
    json = ProxyAttr()
    last_modified = ProxyAttr()
    location = ProxyAttr(str)
    make_conditional = ProxyFunc(lambda v: Response(v))  # noqa: PLW0108
    make_sequence = ProxyFunc(None)
    max_cookie_size = ProxyAttr(int)
    mimetype = ProxyAttr(str)
    response = ProxyAttr()
    retry_after = ProxyAttr()
    set_cookie = ProxyFunc(None)
    set_data = ProxyFunc(None)
    set_etag = ProxyFunc(None)
    status = ProxyAttr(str)
    status_code = ProxyAttr(int)
    stream = ProxyAttr(ResponseStream)

    # odoo.http._response attributes
    load = ProxyFunc()
    set_default = ProxyFunc(None)
    qcontext = ProxyAttr()
    template = ProxyAttr(str)
    is_qweb = ProxyAttr(bool)
    render = ProxyFunc()
    flatten = ProxyFunc(None)

    def __init__(self, *args, **kwargs):
        response = None
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, Response):
                response = arg._wrapped__
            elif isinstance(arg, _Response):
                response = arg
            elif isinstance(arg, werkzeug.wrappers.Response):
                response = _Response.load(arg)
        if response is None:
            if isinstance(kwargs.get("headers"), Headers):
                kwargs["headers"] = kwargs["headers"]._wrapped__
            response = _Response(*args, **kwargs)

        super().__init__(response)
        if "set_cookie" in response.__dict__:
            self.__dict__["set_cookie"] = response.__dict__["set_cookie"]


# Monkey-patch HTTPException.get_response to return our Response
__wz_get_response = HTTPException.get_response


def get_response(self, environ=None, scope=None):
    return Response(__wz_get_response(self, environ, scope))


HTTPException.get_response = get_response

# Monkey-patch werkzeug.exceptions.abort to handle our Response
werkzeug_abort = werkzeug.exceptions.abort


def abort(status, *args, **kwargs):
    if isinstance(status, Response):
        status = status._wrapped__
    werkzeug_abort(status, *args, **kwargs)


werkzeug.exceptions.abort = abort


class FutureResponse:
    """
    werkzeug.Response mock class that only serves as placeholder for
    headers to be injected in the final response.
    """

    max_cookie_size = 4093

    def __init__(self):
        self.headers = werkzeug.datastructures.Headers()

    @functools.wraps(werkzeug.Response.set_cookie)
    def set_cookie(
        self,
        key,
        value="",
        max_age=None,
        expires=-1,
        path="/",
        domain=None,
        secure=False,
        httponly=False,
        samesite=None,
        partitioned=False,
        cookie_type="required",
    ):
        from . import request  # lazy import

        if expires == -1:  # not forced value -> default value -> 1 year
            expires = datetime.now() + timedelta(days=365)

        if request.db and not request.env["ir.http"]._is_allowed_cookie(cookie_type):
            max_age = 0
        werkzeug.Response.set_cookie(
            self,
            key,
            value=value,
            max_age=max_age,
            expires=expires,
            path=path,
            domain=domain,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
            partitioned=partitioned,
        )
