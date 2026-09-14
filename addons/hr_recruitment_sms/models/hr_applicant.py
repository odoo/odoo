from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrApplicant(models.Model):
    _inherit = "hr.applicant"

    def action_send_sms(self):
        res = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "sms.sms_composer_action_form"
        )
        _debug.pipeline("sms_composer_opened", applicants=self)
        res["context"] = {
            "default_composition_mode": "mass",
            "default_mass_keep_log": True,
            "default_res_ids": self.ids,
        }
        return res
