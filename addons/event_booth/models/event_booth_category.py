# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventBoothCategory(models.Model):
    _name = 'event.booth.category'
    _description = 'Event Booth Category'
    _inherit = ['image.mixin']
    _order = 'sequence ASC'

    active = fields.Boolean(default=True)
    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    description = fields.Html(string='Description', translate=True, sanitize_attributes=False)
    booth_ids = fields.One2many(
        'event.booth', 'booth_category_id', string='Booths', groups='event.group_event_registration_desk')
