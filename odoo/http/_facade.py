import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.wrappers
from werkzeug.exceptions import HTTPException

from odoo.tools._vendor.useragents import UserAgent
from odoo.tools.facade import Proxy, ProxyAttr, ProxyFunc

# Please import DEFAULT_MAX_CONTENT_LENGTH from odoo.http.requestlib
DEFAULT_MAX_CONTENT_LENGTH = 128 * 1024 * 1024  # 128MiB


class HTTPRequest:
    def __init__(self, environ):
        httprequest = werkzeug.wrappers.Request(environ)
        httprequest.user_agent_class = UserAgent  # use vendored userAgent since it will be removed in 2.1
        httprequest.parameter_storage_class = werkzeug.datastructures.ImmutableMultiDict
        httprequest.max_content_length = DEFAULT_MAX_CONTENT_LENGTH
        httprequest.max_form_memory_size = 10 * 1024 * 1024  # 10 MB
        self._session_id__ = httprequest.cookies.get('session_id', '')

        self.__wrapped = httprequest
        self.__environ = self.__wrapped.environ
        self.environ = self.headers.environ = {
            key: value
            for key, value in self.__environ.items()
            if (not key.startswith(('werkzeug.', 'wsgi.', 'socket')) or key in ['wsgi.url_scheme', 'werkzeug.proxy_fix.orig'])
        }

    def __enter__(self):
        return self


_HTTPREQUEST_ATTRIBUTES = [
    '__str__', '__repr__', '__exit__',
    'accept_charsets', 'accept_languages', 'accept_mimetypes', 'access_route', 'args', 'authorization', 'base_url',
    'charset', 'content_encoding', 'content_length', 'content_md5', 'content_type', 'cookies', 'data', 'date',
    'encoding_errors', 'files', 'form', 'full_path', 'get_data', 'get_json', 'headers', 'host', 'host_url', 'if_match',
    'if_modified_since', 'if_none_match', 'if_range', 'if_unmodified_since', 'is_json', 'is_secure', 'json',
    'max_content_length', 'method', 'mimetype', 'mimetype_params', 'origin', 'path', 'pragma', 'query_string', 'range',
    'referrer', 'remote_addr', 'remote_user', 'root_path', 'root_url', 'scheme', 'script_root', 'server', 'session',
    'trusted_hosts', 'url', 'url_charset', 'url_root', 'user_agent', 'values',
]

def _make_request_wrap_methods(attr):  # noqa: E302
    def getter(self):
        return getattr(self._HTTPRequest__wrapped, attr)

    def setter(self, value):
        return setattr(self._HTTPRequest__wrapped, attr, value)

    return getter, setter

for _attr in _HTTPREQUEST_ATTRIBUTES:  # noqa: E305
    setattr(HTTPRequest, _attr, property(*_make_request_wrap_methods(_attr)))

del _HTTPREQUEST_ATTRIBUTES, _attr, _make_request_wrap_methods


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
    no_cache = ProxyAttr(bool)
    no_store = ProxyAttr(bool)
    no_transform = ProxyAttr(bool)
    public = ProxyAttr(bool)
    private = ProxyAttr(bool)
    proxy_revalidate = ProxyAttr(bool)
    s_maxage = ProxyAttr(int)
    pop = ProxyFunc()


class ResponseStream(Proxy):
    _wrapped__ = werkzeug.wrappers.ResponseStream

    write = ProxyFunc(int)
    writelines = ProxyFunc(None)
    tell = ProxyFunc(int)


from .response import Response as UnsafeResponse  # noqa: E402


class SafeResponse(Proxy):
    _wrapped__ = UnsafeResponse

    # werkzeug.wrappers.Response attributes
    __call__ = ProxyFunc()
    add_etag = ProxyFunc(None)
    age = ProxyAttr()
    autocorrect_location_header = ProxyAttr(bool)
    cache_control = ProxyAttr(ResponseCacheControl)
    call_on_close = ProxyFunc()
    charset = ProxyAttr(str)
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
    force_type = ProxyFunc(lambda v: SafeResponse(v))  # noqa: PLW0108
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
    make_conditional = ProxyFunc(lambda v: SafeResponse(v))  # noqa: PLW0108
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
            if isinstance(arg, SafeResponse):
                response = arg._wrapped__
            elif isinstance(arg, UnsafeResponse):
                response = arg
            elif isinstance(arg, werkzeug.wrappers.Response):
                response = UnsafeResponse.load(arg)
        if response is None:
            if isinstance(kwargs.get('headers'), Headers):
                kwargs['headers'] = kwargs['headers']._wrapped__
            response = UnsafeResponse(*args, **kwargs)

        super().__init__(response)
        if 'set_cookie' in response.__dict__:
            self.__dict__['set_cookie'] = response.__dict__['set_cookie']


__wz_get_response = HTTPException.get_response


def get_response(self, environ=None, scope=None):
    return SafeResponse(__wz_get_response(self, environ, scope))


HTTPException.get_response = get_response


werkzeug_abort = werkzeug.exceptions.abort


def abort(status, *args, **kwargs):
    if isinstance(status, SafeResponse):
        status = status._wrapped__
    werkzeug_abort(status, *args, **kwargs)


werkzeug.exceptions.abort = abort
