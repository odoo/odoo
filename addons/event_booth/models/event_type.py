# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    event_type_booth_ids = fields.One2many(
        'event.type.booth', 'event_type_id',
        string='Booths', readonly=False, store=True)

    def action_create_event(self):
        action = super().action_create_event()
        action['context'].update({
            'default_event_booth_ids': [
                Command.create(booth._prepare_event_booth_values()) for booth in self.event_type_booth_ids
            ]
        })
        return action
