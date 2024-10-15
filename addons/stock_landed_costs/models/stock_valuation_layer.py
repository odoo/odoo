# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import purchase_stock, stock_account


class StockValuationLayer(stock_account.StockValuationLayer, purchase_stock.StockValuationLayer):

    stock_landed_cost_id = fields.Many2one('stock.landed.cost', 'Landed Cost')
