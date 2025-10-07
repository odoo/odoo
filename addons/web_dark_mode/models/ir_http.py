# © 2022 Florian Kantelberg - initOS GmbH
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _set_color_scheme(cls, response):
        scheme = request.httprequest.cookies.get("color_scheme")
        user = request.env.user
        user_scheme = "dark" if getattr(user, "dark_mode", None) else "light"
        device_dependent = getattr(user, "dark_mode_device_dependent", None)
        if (not device_dependent) and scheme != user_scheme:
            response.set_cookie("color_scheme", user_scheme)

    @classmethod
    def _post_dispatch(cls, response):
        cls._set_color_scheme(response)
        return super()._post_dispatch(response)
