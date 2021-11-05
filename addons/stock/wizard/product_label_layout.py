# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    move_line_ids = fields.Many2many('stock.move.line')
    picking_quantity = fields.Selection([
        ('picking', 'Transfer Quantities'),
        ('custom', 'Custom')], string="Quantity to print", required=True, default='custom')
    print_format = fields.Selection(selection_add=[
        ('zpl', 'ZPL Labels'),
        ('zplxprice', 'ZPL Labels with price')
    ], ondelete={'zpl': 'set default', 'zplxprice': 'set default'})

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()

        if 'zpl' in self.print_format:
            xml_id = 'stock.label_product_product'

        if self.picking_quantity == 'picking' and self.move_line_ids:
            qties = defaultdict(int)
            custom_barcodes = defaultdict(list)
            uom_unit = self.env.ref('uom.product_uom_categ_unit', raise_if_not_found=False)
            for line in self.move_line_ids:
                if line.product_uom_id.category_id == uom_unit:
                    if (line.lot_id or line.lot_name) and int(line.qty_done):
                        custom_barcodes[line.product_id.id].append((line.lot_id.name or line.lot_name, int(line.qty_done)))
                        continue
                    qties[line.product_id.id] += line.qty_done
            # Pass only products with some quantity done to the report
            data['quantity_by_product'] = {p: int(q) for p, q in qties.items() if q}
            data['custom_barcodes'] = custom_barcodes
        return xml_id, data
