# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventBooth(models.Model):
    _inherit = 'event.booth'

    product_id = fields.Many2one(related='booth_category_id.product_id')
    price = fields.Float(related='booth_category_id.price')
    extra_price = fields.Float(related='booth_category_id.extra_price')
