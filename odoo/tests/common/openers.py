"""Exposes "openers" (/ configurable / persistent clients) for the HTTP-ish
test cases.

The primary role of those openers is to enforce flushing connections when a new
(test) cursor might be created and thus working solely out of the local cache
is an issue. Transport only does that.

``RequestsOpener`` is then a client patterned after ``requests.Session`` with
some minor convenience tacked on (the domain is optional and defaults to
``base_url``).

``TestClientOpener`` is a subclass of ``werkzeug.test.Client`` which attempts to
provide an interface compatible with ``RequestsOpener`` (/ ``requests.Session``),
to make the transition easier, or even allow running tests against both
direct-WSGI and over-http-and-through-an-other-thread clients.

Running against the WSGI application has slightly less overhead and should
provide synchronous stacks (which is convenient for debugging), but turns out to
be no panacea and not significantly easier than going trough the outer HTTP
interface, really.
"""
import contextlib
import json
import xmlrpc.client
from http.cookies import BaseCookie

import requests
import werkzeug.wrappers
from requests import HTTPError
from werkzeug.urls import url_parse

import odoo
from odoo.sql_db import BaseCursor

from .utils import HOST, base_url

class RequestsOpener(requests.Session):
    """
    Flushes and clears the current transaction when starting a request.

    This is likely necessary when we make a request to the server, as the
    request is made with a test cursor, which uses a different cache than this
    transaction.
    """
    def __init__(self, cr: BaseCursor):
        super().__init__()
        self.cr = cr

    def request(self, *args, **kwargs):
        self.cr.flush()
        self.cr.clear()
        # fixup URL for convenience compatibility with werkzeug client
        if args[1].startswith('/'):
            args = (
                args[0],
                base_url().join(args[1]).to_url(),
                *args[2:]
            )
        return super().request(*args, **kwargs)

class Transport(xmlrpc.client.Transport):
    """ see :class:`RequestsOpener` """
    def __init__(self, cr: BaseCursor):
        self.cr = cr
        super().__init__()

    def request(self, *args, **kwargs):
        self.cr.flush()
        self.cr.clear()
        return super().request(*args, **kwargs)


class TestResponse(werkzeug.wrappers.Response):
    """Werkzeug 2.0 has TestResponse which basically adds this, but we don't
    require it (yet) so add requests.Response compatibility shims
    """
    @property
    def url(self):
        return '???' # doesn't exist in werkzeug
    @property
    def reason(self):
        return self.status
    def raise_for_status(self):
        reason = self.status
        if 400 <= self.status_code < 500:
            http_error_msg = (
                f"{self.status_code} Client Error: {reason} for url: {self.url}"
            )
        elif 500 <= self.status_code < 600:
            http_error_msg = (
                f"{self.status_code} Server Error: {reason} for url: {self.url}"
            )
        else:
            http_error_msg = ""

        if http_error_msg:
            raise HTTPError(http_error_msg, response=self)
    @property
    def ok(self):
        with contextlib.suppress(HTTPError):
            self.raise_for_status()
            return True
        return False

    @property
    def text(self):
        return self.get_data(as_text=True)

    # werkzeug 2 adds a `json` to `Response`, but it's a property...
    # pylint: disable=invalid-overridden-method
    def json(self):
        return json.loads(self.text)

    @property
    def content(self):
        return self.data

    @property
    def cookies(self):
        cookies = BaseCookie()
        for h, v in self.headers.items():
            if h == 'Set-Cookie':
                cookies.load(v)
        return {name: morsel.value for name, morsel in cookies.items()}

class TestClientOpener(werkzeug.test.Client):
    def __init__(self, cr):
        super().__init__(odoo.http.root, response_wrapper=TestResponse)
        self.cr = cr

    def open(self, *args, **kwargs):
        self.cr.flush()
        self.cr.clear()
        assert not kwargs.pop('files', None), \
            "TODO: translate files between requests and werkzeug APIs"
        kwargs.pop('timeout', None)
        # translate kwargs from requests
        kwargs['follow_redirects'] = kwargs.pop('allow_redirects', False)

        url = url_parse(args[0])
        if url.netloc and url.netloc != base_url().netloc:
            raise AssertionError(f"WSGI client implies {HOST}")

        args = (url.replace(scheme='', netloc='').to_url(), *args[1:])
        kwargs['environ_base'] = {'REMOTE_ADDR': HOST}
        return super().open(*args, **kwargs)

    @property
    def cookies(self):
        # should be a RequestsCookieJar, which is a CookieJar subclass with a
        # complex MutableMapping interface (and some more), but just implement
        # setitem for now, client has a cookie_jar attribute which is its own
        # TestCookieJar
        return CookiesProxy(self)

class CookiesProxy:
    def __init__(self, client):
        self.client = client

    def __setitem__(self, key, value):
        # nb: that's not the cookiejar method
        self.client.set_cookie("", key, value)
