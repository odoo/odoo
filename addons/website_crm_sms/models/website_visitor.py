# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    def _check_for_sms_composer(self):
        check = super(WebsiteVisitor, self)._check_for_sms_composer()
        if not check and self.lead_ids:
            sorted_leads = self.lead_ids.filtered(lambda l: l.phone == self.phone)._sort_by_confidence_level(reverse=True)
            if sorted_leads:
                return True
        return check

    def _prepare_sms_composer_context(self):
        if not self.partner_id and self.lead_ids:
            leads_with_number = self.lead_ids.filtered(lambda l: l.phone == self.phone)._sort_by_confidence_level(reverse=True)
            if leads_with_number:
                lead = leads_with_number[0]
                return {
                    'default_res_model': 'crm.lead',
                    'default_res_id': lead.id,
                    'number_field_name': 'phone',
                }
        return super(WebsiteVisitor, self)._prepare_sms_composer_context()
