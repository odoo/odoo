from odoo import models
from odoo.addons.base.models.ir_http import COOKIES_ANALYTIC, COOKIES_MARKETING


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _forbidden_cookies(cls):
        """Whitelist live chat history cookie if accepted."""
        result = super()._forbidden_cookies()
        choices = cls._chosen_cookie_types()
        if {COOKIES_ANALYTIC, COOKIES_MARKETING} <= choices:
            result.discard("im_livechat_history")
        return result
