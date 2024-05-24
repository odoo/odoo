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

    # @classmethod
    # def _set_guest_and_cookie(cls, guest):
    #     request = http_request or websocket_request
    #     expiration_date = cls.env.cr.now() + timedelta(days=365)
    #     request.future_response.set_cookie(
    #         guest._cookie_name,
    #         guest._format_auth_cookie(),
    #         httponly=True,
    #         expires=expiration_date,
    #     )
    #     request.update_context(guest=guest.sudo(False))
