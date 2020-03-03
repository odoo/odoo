# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EventEvent(models.Model):
    _name = "event.event"
    _inherit = "event.event"

    lead_ids = fields.One2many('crm.lead', 'event_id', string="Leads",
        help="Leads generated from this event")
    lead_count = fields.Integer(compute='_compute_lead_count', string="# Leads",
        help="Counter for the leads linked to this event")

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        lead_data = self.env['crm.lead'].read_group([('event_id', 'in', self.ids)], ['event_id'], ['event_id'])
        mapped_data = {l['event_id'][0]: l['event_id_count'] for l in lead_data}
        for event in self:
            event.lead_count = mapped_data.get(event.id, 0)
