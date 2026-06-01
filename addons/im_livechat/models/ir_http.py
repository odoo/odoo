# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_force_guest(cls):
        cls._auth_method_none()
        guest_token = request.httprequest.args.get("guest_token", "")
        guest = request.env["mail.guest"]._get_guest_from_token(guest_token)
        if guest:
            request.update_context(guest=guest)
