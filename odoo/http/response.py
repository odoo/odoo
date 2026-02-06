from __future__ import annotations

import functools
import logging
import typing
from datetime import datetime, timedelta

import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.wrappers

_logger = logging.getLogger('odoo.http')


class Response(werkzeug.wrappers.Response):
    """
    Outgoing HTTP response with body, status, headers and qweb support.
    In addition to the :class:`werkzeug.wrappers.Response` parameters,
    this class's constructor can take the following additional
    parameters for QWeb Lazy Rendering.

    :param template: template to render
    :param qcontext: Rendering context to use
    :param uid: User id to use for the ir.ui.view render call,
        ``None`` to use the request's user (the default)

    these attributes are available as parameters on the Response object
    and can be altered at any time before rendering

    Also exposes all the attributes and methods of
    :class:`werkzeug.wrappers.Response`.
    """
    default_mimetype = 'text/html'

    def __init__(self,
        *args,
        template: str | None = None,
        qcontext: dict | None = None,
        uid: int | None = None,
        **kw,
    ):
        super().__init__(*args, **kw)
        self.set_default(template, qcontext, uid)

    @classmethod
    def load(
        cls,
        result: Response | werkzeug.wrappers.Response | werkzeug.exceptions.HTTPException | bytes | str | None,
        fname: str = "<function>",
    ) -> Response:
        """
        Convert the return value of an endpoint into a Response.

        :param result: The endpoint return value to load the Response from.
        :param fname: The endpoint function name where the result emanated from,
                      used for logging.
        :returns: The created :class:`~odoo.http.Response`.
        :raises TypeError: When ``result`` type is none of the above-
            mentioned type.
        """
        if isinstance(result, Response):
            return result

        if isinstance(result, werkzeug.exceptions.HTTPException):
            _logger.warning("%s returns an HTTPException instead of raising it.", fname)
            raise result

        if isinstance(result, werkzeug.wrappers.Response):
            response: Response = cls.force_type(result)
            response.set_default()
            return response

        if isinstance(result, (bytes, str, type(None))):
            return Response(result)

        raise TypeError(f"{fname} returns an invalid value: {result}")

    def set_default(self, template: str | None = None, qcontext: dict | None = None, uid: int | None = None) -> None:
        self.template = template
        self.qcontext = qcontext or dict()
        self.qcontext['response_template'] = self.template
        self.uid = uid

    @property
    def is_qweb(self) -> bool:
        return self.template is not None

    def render(self) -> typing.Any:
        """ Renders the Response's template, returns the result. """
        self.qcontext['request'] = request
        return request.env["ir.ui.view"]._render_template(self.template, self.qcontext)

    def flatten(self) -> None:
        """
        Forces the rendering of the response's template, sets the result
        as response body and unsets :attr:`.template`
        """
        if self.template:
            self.response.append(self.render())
            self.template = None

    def set_cookie(self, key, value='', max_age=None, expires=-1, path='/', domain=None, secure=False, httponly=False, samesite=None, cookie_type='required'):
        """
        The default expires in Werkzeug is None, which means a session cookie.
        We want to continue to support the session cookie, but not by default.
        Now the default is arbitrary 1 year.
        So if you want a cookie of session, you have to explicitly pass expires=None.
        """
        if expires == -1:  # not provided value -> default value -> 1 year
            expires = datetime.now() + timedelta(days=365)

        if request.db and not request.env['ir.http']._is_allowed_cookie(cookie_type):
            max_age = 0
        super().set_cookie(key, value=value, max_age=max_age, expires=expires, path=path, domain=domain, secure=secure, httponly=httponly, samesite=samesite)


# Replace the above (unsafe) response by the facade safe one
if not typing.TYPE_CHECKING:
    from ._facade import SafeResponse as Response  # noqa: F811


class FutureResponse:
    """
    werkzeug.Response mock class that only serves as placeholder for
    headers to be injected in the final response.
    """
    # used by werkzeug.Response.set_cookie
    charset = 'utf-8'
    max_cookie_size = 4093

    def __init__(self):
        self.headers = werkzeug.datastructures.Headers()

    @property
    def _charset(self):
        return self.charset

    @functools.wraps(werkzeug.Response.set_cookie)
    def set_cookie(self, key, value='', max_age=None, expires=-1, path='/', domain=None, secure=False, httponly=False, samesite=None, cookie_type='required'):
        if expires == -1:  # not forced value -> default value -> 1 year
            expires = datetime.now() + timedelta(days=365)

        if request.db and not request.env['ir.http']._is_allowed_cookie(cookie_type):
            max_age = 0
        werkzeug.Response.set_cookie(self, key, value=value, max_age=max_age, expires=expires, path=path, domain=domain, secure=secure, httponly=httponly, samesite=samesite)


# ruff: noqa: E402
from .requestlib import request
