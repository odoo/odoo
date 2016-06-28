# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    life_time = fields.Integer(string='Product Life Time',
        help='When a new a Serial Number is issued, this is the number of days before the goods may become dangerous and must not be consumed.')
    use_time = fields.Integer(string='Product Use Time',
        help='When a new a Serial Number is issued, this is the number of days before the goods starts deteriorating, without being dangerous yet.')
    removal_time = fields.Integer(string='Product Removal Time',
        help='When a new a Serial Number is issued, this is the number of days before the goods should be removed from the stock.')
    alert_time = fields.Integer(string='Product Alert Time',
        help='When a new a Serial Number is issued, this is the number of days before an alert should be notified.')
