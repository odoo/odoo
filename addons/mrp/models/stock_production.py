# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    move_lot_ids = fields.One2many('stock.move.lots', 'lot_id', string='Stock Move Lots')
