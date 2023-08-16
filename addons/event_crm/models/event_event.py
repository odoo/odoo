# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

class EventEvent(models.Model):
    _name = "event.event"
    _inherit = "event.event"

    lead_ids = fields.One2many(
        'crm.lead', 'event_id', string="Leads", groups='sales_team.group_sale_salesman',
        help="Leads generated from this event")
    lead_count = fields.Integer(
        string="# Leads", compute='_compute_lead_count', groups='sales_team.group_sale_salesman')

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        lead_data = self.env['crm.lead']._read_group(
            [('event_id', 'in', self.ids)],
            ['event_id'], ['__count'],
        )
        mapped_data = {event.id: count for event, count in lead_data}
        for event in self:
            event.lead_count = mapped_data.get(event.id, 0)

    def action_generate_leads(self):
        self.ensure_one()

        BATCH_SIZE = 500
        registration_batches = [
            self.registration_ids[i: i + BATCH_SIZE] for i in range(0, len(self.registration_ids), BATCH_SIZE)
        ]
        total_number_of_leads = 0
        for registration_batch in registration_batches:
            created_leads = self.env['event.registration'].create_leads_from_event_lead_rules(registration_batch)
            leads_len = len(created_leads)
            if leads_len > 0:
                _logger.info("Lead generation created a batch of %s lead(s)", leads_len)
                total_number_of_leads += leads_len

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'sticky': False,
                'message': _("Number of leads created: %s", total_number_of_leads),
            }
        }
