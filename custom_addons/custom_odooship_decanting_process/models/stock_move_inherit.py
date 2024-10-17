# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class StockMoveLine(models.Model):
    _inherit = "stock.move"

    remaining_qty = fields.Float('Quantity')
    is_remaining_qty = fields.Boolean(string='Remaining', default=False)



