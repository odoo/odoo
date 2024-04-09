# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import models
from odoo.http import request as http_request
from odoo.addons.bus.websocket import wsrequest as websocket_request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_guest(cls):
        _guest = cls._fetch_guest_info_from_cookies()
        cls._auth_method_public()

    @classmethod
    def _fetch_guest_info_from_cookies(cls):
        request = http_request or websocket_request
        token = request.httprequest.cookies.get(request.env["mail.guest"]._cookie_name, "")
        guest = request.env["mail.guest"]._get_guest_from_token(token)
        if guest and not guest.timezone and not request.env.cr.readonly:
            timezone = request.env["mail.guest"]._get_timezone_from_request(request)
            if timezone:
                guest._update_timezone(timezone)
        if guest:
            request.update_context(guest=guest)
        return guest
