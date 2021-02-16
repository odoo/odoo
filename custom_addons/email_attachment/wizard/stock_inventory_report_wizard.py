# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockInventoryWizardReport(models.TransientModel):
    _name = 'report.stock.inventory.wizard'
    _description = 'Add Students'

    product_ids = fields.Many2many('product.product', 'report_stock_inventory_rel', 'report_stock_inventory_id',
                                   domain=[('product_tmpl_id.type', 'in', ('consu', 'product'))],
                                   string='Select Product', required=True)

    def print_report(self):
        data = {
            'model': 'report.stock.inventory.wizard',
            'form': self.read()[0],
        }
        # print(data['form']['product_ids'])
        return self.env.ref('qweb_report.report_product_stock_inventory_wizard_action').report_action(self, data=data)
