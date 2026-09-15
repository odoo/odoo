from odoo import api, models
from odoo.libs.debug_log import DebugLog

from odoo.addons.website.models import ir_http

_debug = DebugLog(__name__)


class IrRule(models.Model):
    _inherit = "ir.rule"

    @api.model
    def _eval_context(self):
        res = super()._eval_context()

        is_frontend = ir_http.get_request_website()
        Website = self.env["website"]
        res["website"] = (is_frontend and Website.get_current_website()) or Website
        _debug.logic(
            "rule_eval_context", frontend=bool(is_frontend), website=res["website"].id
        )
        return res

    def _get_context_keys_in_domains(self):
        return super()._get_context_keys_in_domains() + ["website_id"]
