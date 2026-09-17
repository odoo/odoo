import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import quote as url_quote

import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.wrappers
from werkzeug.exceptions import HTTPException

from odoo.libs._vendor.useragents import UserAgent
from odoo.libs.debug_log import DebugLog
from odoo.libs.facade import Proxy, ProxyAttr, ProxyFunc

from ._cookies import _set_cookie_on
from .constants import (
    DEFAULT_MAX_CONTENT_LENGTH,
    DEFAULT_MAX_FORM_MEMORY_SIZE,
    DEFAULT_MAX_FORM_PARTS,
)
from .core import request

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def prepare_content_disposition_header(
    filename: str, disposition_type: str = "attachment"
) -> str:
    if disposition_type not in ("attachment", "inline"):
        e = f"Invalid disposition_type: {disposition_type!r}"
        raise ValueError(e)
    return f"{disposition_type}; filename*=UTF-8''{url_quote(filename, safe='')}"


def _prepare_request_property_accessors(attr: str) -> tuple[Any, Any]:

    def getter(self: HTTPRequest) -> Any:
        return getattr(self._HTTPRequest__wrapped, attr)

    def setter(self: HTTPRequest, value: Any) -> None:
        return setattr(self._HTTPRequest__wrapped, attr, value)

    return getter, setter


if TYPE_CHECKING:

    class _HTTPRequestProxied(werkzeug.wrappers.Request):
        pass

else:
    _HTTPRequestProxied = object


class HTTPRequest(_HTTPRequestProxied):
    def __init__(self, environ: dict[str, Any]) -> None:
        httprequest = werkzeug.wrappers.Request(environ)
        httprequest.user_agent_class = UserAgent
        httprequest.parameter_storage_class = werkzeug.datastructures.ImmutableMultiDict
        httprequest.max_content_length = DEFAULT_MAX_CONTENT_LENGTH
        httprequest.max_form_memory_size = DEFAULT_MAX_FORM_MEMORY_SIZE
        httprequest.max_form_parts = DEFAULT_MAX_FORM_PARTS

        self.__wrapped = httprequest
        self.__environ = httprequest.environ
        filtered = {
            key: value
            for key, value in self.__environ.items()
            if (
                not key.startswith(("werkzeug.", "wsgi.", "socket", "odoo.socket"))
                or key in ["wsgi.url_scheme", "werkzeug.proxy_fix.orig"]
            )
        }
        self.environ = filtered
        httprequest.headers = werkzeug.datastructures.EnvironHeaders(filtered)
        _debug.lifecycle(
            "http.httprequest.created",
            method=httprequest.method,
            path=httprequest.path,
            content_length=httprequest.content_length,
            mimetype=httprequest.mimetype,
        )

    @property
    def session_id(self) -> str | None:
        return self.__wrapped.cookies.get("session_id")

    @property
    def raw_environ(self) -> dict[str, Any]:
        return self.__environ

    def _adopt_body_state(self, other: HTTPRequest) -> None:
        src = other.__wrapped
        dst = self.__wrapped
        for key in (
            "max_content_length",
            "max_form_memory_size",
            "max_form_parts",
            "trusted_hosts",
        ):
            setattr(dst, key, getattr(src, key))
        for key in ("stream", "data", "form", "files"):
            if key in src.__dict__:
                dst.__dict__[key] = src.__dict__[key]
        if getattr(src, "_cached_data", None) is not None:
            dst._cached_data = src._cached_data
        _debug.lifecycle(
            "http.httprequest.body_adopted",
            parsed=[
                key
                for key in ("stream", "data", "form", "files")
                if key in src.__dict__
            ],
            cached_data=getattr(src, "_cached_data", None) is not None,
        )

    def __enter__(self) -> Self:
        return self


HTTPREQUEST_ATTRIBUTES = [
    "__str__",
    "__repr__",
    "__exit__",
    "accept_charsets",
    "accept_encodings",
    "accept_languages",
    "accept_mimetypes",
    "access_route",
    "args",
    "authorization",
    "base_url",
    "cache_control",
    "close",
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
    "input_stream",
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
    "stream",
    "trusted_hosts",
    "url",
    "url_root",
    "user_agent",
    "values",
]
for attr in HTTPREQUEST_ATTRIBUTES:
    setattr(HTTPRequest, attr, property(*_prepare_request_property_accessors(attr)))


class _Response(werkzeug.wrappers.Response):
    default_mimetype = "text/html"

    def __init__(self, *args: Any, **kw: Any) -> None:
        template = kw.pop("template", None)
        qcontext = kw.pop("qcontext", None)
        uid = kw.pop("uid", None)
        super().__init__(*args, **kw)
        self.update_qweb_state(template, qcontext, uid)

    @classmethod
    def from_endpoint_result(cls, result: Any, fname: str = "<function>") -> Response:
        if isinstance(result, Response):
            return result

        if isinstance(result, werkzeug.exceptions.HTTPException):
            _logger.warning("%s returns an HTTPException instead of raising it.", fname)
            _debug.logic(
                "http.response.exception_returned",
                endpoint=fname,
                error=type(result).__name__,
            )
            raise result

        if isinstance(result, werkzeug.wrappers.Response):
            _debug.logic("http.response.coerced", kind="werkzeug", endpoint=fname)
            return Response(result)

        if isinstance(result, (bytes, str, type(None))):
            _debug.logic(
                "http.response.coerced", kind=type(result).__name__, endpoint=fname
            )
            return Response(result)

        _debug.logic(
            "http.response.invalid_result",
            endpoint=fname,
            result_type=type(result).__name__,
        )
        raise TypeError(
            f"{fname} returns an invalid value: {result!r}. type='http' routes "
            "return str/bytes/None/Response; for a dict or list, return "
            "request.prepare_json_response(...) or use a jsonrpc/json2 route."
        )

    def update_qweb_state(
        self,
        template: str | None = None,
        qcontext: dict[str, Any] | None = None,
        uid: int | None = None,
    ) -> None:
        self.template = template
        self.qcontext = qcontext or {}
        self.qcontext["response_template"] = self.template
        self.uid = uid

    @property
    def is_qweb(self) -> bool:
        return self.template is not None

    def render(self) -> bytes:
        if self.template is None:
            raise ValueError(
                "Response.render() needs a template; guard the call with "
                "is_qweb() or set one before rendering."
            )
        env = request.env
        if env is None:
            raise RuntimeError("rendering a QWeb response needs a bound environment")
        self.qcontext["request"] = request
        with _debug.perf(
            "http.response.render", cr=env.cr, template=self.template
        ) as span:
            rendered = env["ir.ui.view"]._render_template(self.template, self.qcontext)
            span.set(bytes=len(rendered))
        return rendered

    def flatten(self) -> None:
        if self.template:
            _debug.pipeline("http.response.flattened", template=self.template)
            self.response.append(self.render())
            self.template = None

    def set_cookie(
        self,
        key: str,
        value: str = "",
        max_age: int | None = None,
        expires: datetime | int | None = -1,
        path: str | None = "/",
        domain: str | None = None,
        secure: bool | None = None,
        httponly: bool = False,
        samesite: str | None = None,
        partitioned: bool = False,
        cookie_type: str = "required",
    ) -> None:
        _debug.lifecycle(
            "http.cookie.set", key=key, max_age=max_age, cookie_type=cookie_type
        )
        _set_cookie_on(
            self,
            key,
            value,
            max_age,
            expires,
            path,
            domain,
            secure,
            httponly,
            samesite,
            partitioned,
            cookie_type,
        )


def prepare_no_content_response(status: int = 204, headers: Any = None) -> Response:
    response = Response(status=status, headers=headers)
    del response.headers["Content-Type"]
    return response


def _unwrap_proxy(value: Any) -> Any:
    return value._wrapped__ if isinstance(value, Proxy) else value


class Headers(Proxy):
    _wrapped__ = werkzeug.datastructures.Headers

    _list = ProxyAttr()

    __getitem__ = ProxyFunc()
    __repr__ = ProxyFunc(str)
    __setitem__ = ProxyFunc(None)
    __delitem__ = ProxyFunc(None)
    __str__ = ProxyFunc(str)
    __contains__ = ProxyFunc(bool)
    __iter__ = ProxyFunc()
    __len__ = ProxyFunc(int)
    add = ProxyFunc(None)
    add_header = ProxyFunc(None)
    clear = ProxyFunc(None)
    copy = ProxyFunc(lambda v: Headers(v))  # noqa: PLW0108  self-reference: Headers isn't defined yet when the class body evaluates this lambda, so PLW0108's "redundant lambda" check doesn't apply
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

    def __eq__(self, other: object) -> bool:
        return self._wrapped__ == _unwrap_proxy(other)

    __hash__ = None  # type: ignore[assignment]


class ResponseCacheControl(Proxy):
    _wrapped__ = werkzeug.datastructures.ResponseCacheControl

    __getitem__ = ProxyFunc()
    __setitem__ = ProxyFunc(None)
    __contains__ = ProxyFunc(bool)
    __iter__ = ProxyFunc()
    __len__ = ProxyFunc(int)
    get = ProxyFunc()
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

    def __eq__(self, other: object) -> bool:
        return self._wrapped__ == _unwrap_proxy(other)

    __hash__ = None  # type: ignore[assignment]


class ResponseStream(Proxy):
    _wrapped__ = werkzeug.wrappers.ResponseStream

    write = ProxyFunc(int)
    writelines = ProxyFunc(None)
    tell = ProxyFunc(int)


class Response(Proxy):
    """Typed facade over :class:`_Response`.

    The surface is deliberately minimal: only the attributes listed below
    exist on the public class, and standard werkzeug response attributes left
    out on purpose (``vary``, ``allow``, ``www_authenticate``, ``date``,
    ``content_range``, ``accept_ranges``) raise ``AttributeError``. Anything
    beyond this surface goes through ``response.headers``.
    """

    _wrapped__ = _Response

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
    force_type = ProxyFunc(lambda v: Response(v))  # noqa: PLW0108  self-reference, see Headers.copy
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
    make_conditional = ProxyFunc(lambda v: Response(v))  # noqa: PLW0108  self-reference, see Headers.copy
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

    from_endpoint_result = ProxyFunc()
    update_qweb_state = ProxyFunc(None)
    qcontext = ProxyAttr()
    template = ProxyAttr(str)
    is_qweb = ProxyAttr(bool)
    render = ProxyFunc()
    flatten = ProxyFunc(None)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        response = None
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, Response):
                response = arg._wrapped__
            elif isinstance(arg, _Response):
                response = arg
            elif isinstance(arg, werkzeug.wrappers.Response):
                response = _Response.force_type(arg)
                response.update_qweb_state()
        if response is not None and kwargs:
            raise TypeError(
                f"Response(existing_response) ignores keyword arguments "
                f"{sorted(kwargs)}; set them on the response object instead."
            )
        if response is None:
            if isinstance(kwargs.get("headers"), Headers):
                kwargs["headers"] = kwargs["headers"]._wrapped__
            response = _Response(*args, **kwargs)

        super().__init__(response)


def prepare_exception_response(
    exc: HTTPException, environ: dict[str, Any] | None = None
) -> Response:
    if exc.response is None and exc.code is None:
        _debug.logic("http.exception.statusless_to_500", error=type(exc).__name__)
        exc = werkzeug.exceptions.InternalServerError(exc.description)
    return Response(exc.get_response(environ))
