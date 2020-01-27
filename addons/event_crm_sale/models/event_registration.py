# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    def _get_lead_values(self, rule):
        registration_lead_values = super(EventRegistration, self)._get_lead_values(rule)
        registration_lead_values.update({
            'campaign_id': self.utm_campaign_id.id,
            'source_id': self.utm_source_id.id,
            'medium_id': self.utm_medium_id.id,
        })
        return registration_lead_values

    def _get_lead_group(self, rule):
        super(EventRegistration, self)._get_lead_group(rule)
        registration_group = self.search([('sale_order_id', '=', self.sale_order_id.id)])
        return registration_group.lead_ids.filtered(lambda lead: lead.event_lead_rule_id == rule)
