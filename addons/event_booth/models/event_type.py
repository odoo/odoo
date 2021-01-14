# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo import Command


class EventType(models.Model):
    _inherit = 'event.type'

    use_booth = fields.Boolean(string='Booths')
    event_type_booth_category_ids = fields.One2many(
        'event.type.booth.category', 'event_type_id',
        string='Booths Category', compute='_compute_event_type_booth_category_ids',
        readonly=False, store=True)

    @api.depends('use_booth')
    def _compute_event_type_booth_category_ids(self):
        for template in self:
            if not template.use_booth:
                template.event_type_booth_category_ids = [Command.clear()]
            elif not template.event_type_booth_category_ids:
                template.event_type_booth_category_ids = [Command.create({
                    'name': _('Standard Booth'),
                    'is_multi_slots': True,
                })]
