# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockQuantityHistory(models.TransientModel):
    _name = 'stock.quantity.history'
    _description = 'Stock Quantity History'

    inventory_datetime = fields.Datetime('Inventory at Date',
        help="Choose a date to get the inventory at that date",
        default=fields.Datetime.now, oldname='date')

    def open_at_date(self):
        return {
            'name': str(self.inventory_datetime),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.inventory.report',
            'view_type': 'tree',
            'view_mode': 'tree,pivot,graph',
            'context': {
                'search_default_internal_loc': 1,
                'search_default_productgroup': 1,
                'search_default_locationgroup': 1,
            },
            'domain': [('date', '=', self.inventory_datetime.date())],
        }
