# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockQuantityHistory(models.TransientModel):
    _name = 'stock.quantity.history'
    _description = 'Stock Quantity History'

    compute_at_date = fields.Selection([
        (0, 'Current Inventory'),
        (1, 'At a Specific Date')
    ], string="Compute", help="Choose to analyze the current inventory or from a specific date in the past.")
    date = fields.Datetime('Inventory at Date', help="Choose a date to get the inventory at that date", default=fields.Datetime.now)
    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string="Warehouse"
    )
    location_id = fields.Many2one(
        comodel_name='stock.location',
        string="Location"
    )

    def open_table(self):
        self.ensure_one()

        if self.compute_at_date:
            tree_view_id = self.env.ref('stock.view_stock_product_tree').id
            form_view_id = self.env.ref('stock.product_form_view_procurement_button').id
            # We pass `to_date` in the context so that `qty_available` will be computed across
            # moves until date.
            action = {
                'type': 'ir.actions.act_window',
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                'view_mode': 'tree,form',
                'domain': "['|', ('qty_available', '!=', 0), ('virtual_available', '!=', 0)]",
                'name': _('Products'),
                'res_model': 'product.product',
                'context': dict(self.env.context, to_date=self.date, location=self.location_id.id, warehouse=self.warehouse_id.id),
            }
            return action
        else:
            self.env['stock.quant']._merge_quants()
            return self.env.ref('stock.quantsact').read()[0]
