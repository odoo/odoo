# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventType(models.Model):
    _inherit = 'event.type'

    event_type_booth_ids = fields.One2many(
        'event.type.booth', 'event_type_id',
        string='Booths', readonly=False, store=True)
