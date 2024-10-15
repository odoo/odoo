# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import sale_stock, stock_delivery


class StockPicking(sale_stock.StockPicking, stock_delivery.StockPicking):

    website_id = fields.Many2one('website', related='sale_id.website_id', string='Website',
                                 help='Website where this order has been placed, for eCommerce orders.',
                                 store=True, readonly=True)
