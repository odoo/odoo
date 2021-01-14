# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    use_booth = fields.Boolean(string='Use Booths')
    event_type_booth_ids = fields.One2many(
        'event.type.booth', 'event_type_id',
        string='Booths', compute='_compute_event_type_booth_ids',
        readonly=False, store=True)

    @api.depends('use_booth')
    def _compute_event_type_ticket_ids(self):
        for template in self:
            if not template.use_booth:
                template.event_type_booth_ids = [(5, 0)]
