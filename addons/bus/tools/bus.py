# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import wraps

from odoo import models
from odoo.http import request
from odoo.addons.bus.websocket import wsrequest


def notify_bus_on_completion(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        bus_rpc_uuid = kwargs.pop("bus_rpc_uuid", None)
        try:
            result = func(self, *args, **kwargs)
        finally:
            partner, guest = request.env["res.partner"]._get_current_persona()
        if bus_rpc_uuid:
            (partner or guest)._bus_send("bus.rpc/end", bus_rpc_uuid)
        return result
    return wrapper


def add_guest_to_context(func):
    """ Decorate a function to extract the guest from the request.
    The guest is then available on the context of the current
    request.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        req = request or wsrequest
        token = (
            req.cookies.get(req.env["mail.guest"]._cookie_name, "")
        )
        guest = req.env["mail.guest"]._get_guest_from_token(token)
        if guest and not guest.timezone and not req.env.cr.readonly:
            timezone = req.env["mail.guest"]._get_timezone_from_request(req)
            if timezone:
                guest._update_timezone(timezone)
        if guest:
            req.update_context(guest=guest)
            if isinstance(self, models.BaseModel):
                self = self.with_context(guest=guest)
        return func(self, *args, **kwargs)

    return wrapper
