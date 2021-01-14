# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventBooth(models.Model):
    _name = 'event.type.booth'
    _description = 'Event Booth Template'

    name = fields.Char(string='Name', required=True)
    event_type_id = fields.Many2one(
        'event.type', string='Event Category',
        ondelete='cascade', required=True)
    booth_category_id = fields.Many2one(
        'event.booth.category', string='Booth Category',
        ondelete='restrict', required=True)

    def _get_event_booth_fields_whitelist(self):
        return ['name', 'booth_category_id']
