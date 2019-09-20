# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    def _prepare_visitor_send_sms_values(self):
        visitor_sms_values = super(WebsiteVisitor, self)._prepare_visitor_send_sms_values()
        if not visitor_sms_values:
            leads_with_number = self.lead_ids.filtered(lambda l: l.mobile == self.mobile or l.phone == self.mobile)._sort_by_confidence_level(reverse=True)
            if leads_with_number:
                lead = leads_with_number[0]
                return {
                    'res_model': 'crm.lead',
                    'res_id': lead.id,
                    'partner_ids': [lead.id],
                    'number_field_name': 'mobile' if lead.mobile == self.mobile else 'phone',
                }
        return visitor_sms_values
