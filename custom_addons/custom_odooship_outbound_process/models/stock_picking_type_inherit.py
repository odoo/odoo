# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    picking_process_type = fields.Selection([
        ('dr', 'DR'),
        ('receipt', 'Receipt'),
        ('internal', 'Internal Transfer'),
        ('pick', 'Pick'),
        ('pack', 'Pack'),
        ('delivery', 'Delivery Order'),
        ('returns', 'Returns')
    ], string='Process Type')
