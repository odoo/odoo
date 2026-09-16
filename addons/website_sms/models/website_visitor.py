from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class WebsiteVisitor(models.Model):
    _inherit = "website.visitor"

    def _can_use_sms_composer(self):
        return bool(self.partner_id.phone_ids)

    def _prepare_sms_composer_context(self):
        return {
            "default_res_model": "res.partner",
            "default_res_id": self.partner_id.id,
            "default_composition_mode": "comment",
            "default_number_field_name": "phone_ids",
        }

    def action_send_sms(self):
        self.check_singleton()
        _debug.logic(
            "visitor_sms_composer",
            visitor=self,
            partner=self.partner_id,
            reachable=self._can_use_sms_composer(),
        )
        if not self._can_use_sms_composer():
            raise UserError(
                _(
                    "There are no contact and/or no phone or mobile numbers linked to this visitor."
                )
            )
        visitor_composer_ctx = self._prepare_sms_composer_context()

        compose_ctx = dict(self.env.context)
        compose_ctx.update(**visitor_composer_ctx)
        return {
            "name": _("Send SMS"),
            "type": "ir.actions.act_window",
            "res_model": "sms.composer",
            "view_mode": "form",
            "context": compose_ctx,
            "target": "new",
        }
