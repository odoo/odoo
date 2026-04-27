# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, Command


class CalendarEventCrm(models.Model):
    _inherit = 'calendar.event'

    def _get_lead_values(self, partner):
        lead_values = super()._get_lead_values(partner)
        visitor_sudo = self.env['website.visitor']._get_visitor_from_request()
        # Ensures that we enrich the lead with the actual visitor information
        # (i.e. either anonymous or identified as the partner booking the appointment)
        if visitor_sudo and (not visitor_sudo.partner_id or visitor_sudo.partner_id == partner):
            lead_values['visitor_ids'] = [Command.link(visitor_sudo.id)]
            if not lead_values.get('country_id') and visitor_sudo.country_id:
                lead_values['country_id'] = visitor_sudo.country_id.id
            if not lead_values.get('lang_id') and visitor_sudo.lang_id:
                lead_values['lang_id'] = visitor_sudo.lang_id.id
        return lead_values
