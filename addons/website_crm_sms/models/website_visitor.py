from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class WebsiteVisitor(models.Model):
    _inherit = "website.visitor"

    def _can_use_sms_composer(self):
        check = super()._can_use_sms_composer()
        if not check and self.lead_ids:
            sorted_leads = self.lead_ids.filtered(
                lambda l: self.mobile in l.phone_ids.mapped("number")
            )._sort_by_confidence_level(reverse=True)
            _debug.logic(
                "sms_reachable_through_lead",
                visitor=self,
                leads=self.lead_ids,
                matching=sorted_leads,
            )
            if sorted_leads:
                return True
        return check

    def _prepare_sms_composer_context(self):
        if not self.partner_id and self.lead_ids:
            leads_with_number = self.lead_ids.filtered(
                lambda l: self.mobile in l.phone_ids.mapped("number")
            )._sort_by_confidence_level(reverse=True)
            _debug.logic(
                "sms_composer_lead_lookup",
                visitor=self,
                leads=self.lead_ids,
                matching=leads_with_number,
            )
            if leads_with_number:
                lead = leads_with_number[0]
                return {
                    "default_res_model": "crm.lead",
                    "default_res_id": lead.id,
                    "number_field_name": "phone_ids",
                }
        return super()._prepare_sms_composer_context()
