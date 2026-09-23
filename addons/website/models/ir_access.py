from odoo import api, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.website.models import ir_http

_debug = DebugLog(__name__)


class IrAccess(models.Model):
    _inherit = "ir.access"

    @api.model
    def _eval_context(self):
        res = super()._eval_context()

        is_frontend = ir_http.get_request_website()
        Website = self.env["website"]
        res["website"] = (is_frontend and Website.get_current_website()) or Website
        _debug.logic(
            "access_eval_context", frontend=bool(is_frontend), website=res["website"].id
        )
        return res

    def _get_access_context(self):
        yield from super()._get_access_context()
        yield self.env.context.get("website_id")
