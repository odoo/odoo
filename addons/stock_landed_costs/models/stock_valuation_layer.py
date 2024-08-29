# -*- coding: utf-8 -*-
from odoo.addons import stock_account
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockValuationLayer(models.Model, stock_account.StockValuationLayer):

    stock_landed_cost_id = fields.Many2one('stock.landed.cost', 'Landed Cost')
