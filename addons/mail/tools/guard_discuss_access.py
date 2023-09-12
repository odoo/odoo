from urllib.parse import urlsplit
from functools import wraps
from inspect import Parameter, signature
from werkzeug.exceptions import NotFound

from odoo.tools import consteq
from odoo.http import request
from odoo.addons.bus.websocket import wsrequest


def is_request_from_same_origin(req):
    origin_url = urlsplit(req.httprequest.headers.get("origin", req.httprequest.headers.get("referer")))
    return (
        origin_url.netloc == req.httprequest.headers.get("host")
        and origin_url.scheme == req.httprequest.scheme
        or req.httprequest.environ.get("HTTP_SEC_FETCH_DEST") == "document"
    )


def add_guest_to_context(func):
    """Decorate a function to extract the guest from the request.
    The guest is then available on the context of the current request. In case
    of cross origin request, the `guest_token` passed in the request params is
    used to authenticate the guest. The authentication cookie is used otherwise.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        req = request or wsrequest
        token = (
            req.httprequest.cookies.get(req.env["mail.guest"]._cookie_name, "")
            if is_request_from_same_origin(req)
            else kwargs.pop("guest_token", req.env.context.get("guest_token", ""))
        )
        parts = token.split(req.env["mail.guest"]._cookie_separator)
        guest = req.env["mail.guest"]
        if len(parts) == 2:
            guest_id, guest_access_token = parts
            guest = req.env["mail.guest"].browse(int(guest_id)).sudo().exists()
            if not guest or not guest.access_token or not consteq(guest.access_token, guest_access_token):
                guest = req.env["mail.guest"]
            elif not guest.timezone:
                timezone = req.env["mail.guest"]._get_timezone_from_request(req)
                if timezone:
                    guest._update_timezone(timezone)
        if guest:
            guest = guest.sudo(False)
            req.update_context(guest=guest)
            if hasattr(self, "env"):
                self.env.context = {**self.env.context, "guest": guest}
        return func(self, *args, **kwargs)

    # Add the guest_token parameter to the wrapper signature
    # so that it is not marked as being ignored. It will be
    # popped before calling the wrapped function.
    old_sig = signature(wrapper)
    params = list(old_sig.parameters.values())
    new_param_index = next(
        (
            index
            for index, param in enumerate(params)
            if param.kind in [Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD]
        ),
        len(params),
    )
    new_param = Parameter("guest_token", Parameter.POSITIONAL_OR_KEYWORD, default=None)
    params.insert(new_param_index, new_param)
    wrapper.__signature__ = old_sig.replace(parameters=params)
    return wrapper


def guard_discuss_access(func):
    """Decorate a function that checks if the current user has access to
    the discuss app routes. In case of cross origin request, the `guest_token`
    passed in the request params is used to authenticate the guest. The
    authentication cookie is used otherwise. If the guest is authenticated, it
    is added to the context of the current request. If there is no user and no
    guest, a 404 error is raised.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        req = request or wsrequest
        has_valid_user = not request.env.user._is_public() and is_request_from_same_origin(req)
        if not req.env["mail.guest"]._get_guest_from_context() and not has_valid_user:
            raise NotFound()
        return func(self, *args, **kwargs)

    return add_guest_to_context(wrapper)
