# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models


class ProductLabelLayout(models.TransientModel):
    _name = 'lot.label.layout'
    _description = 'Choose the sheet layout to print lot labels'

    picking_ids = fields.Many2many('stock.picking')
    label_quantity = fields.Selection([
        ('lots', 'One per lot/SN'),
        ('units', 'One per unit')], string="Quantity to print", required=True, default='lots', help="If the UoM of a lot is not 'units', the lot will be considered as a unit and only one label will be printed for this lot.")
    print_format = fields.Selection([
        ('4x12', '4 x 12'),
        ('zpl', 'ZPL Labels')], string="Format", default='4x12', required=True)

    def process(self):
        self.ensure_one()
        xml_id = 'stock.action_report_lot_label'
        if self.print_format == 'zpl':
            xml_id = 'stock.label_lot_template'
        if self.label_quantity == 'lots':
            docids = self.picking_ids.move_line_ids.lot_id.ids
        else:
            uom_categ_unit = self.env.ref('uom.product_uom_categ_unit')
            quantity_by_lot = defaultdict(int)
            for move_line in self.picking_ids.move_line_ids:
                if not move_line.lot_id:
                    continue
                if move_line.product_uom_id.category_id == uom_categ_unit:
                    quantity_by_lot[move_line.lot_id.id] += int(move_line.qty_done)
                else:
                    quantity_by_lot[move_line.lot_id.id] += 1
            docids = []
            for lot_id, qty in quantity_by_lot.items():
                docids.extend([lot_id] * qty)
        report_action = self.env.ref(xml_id).report_action(docids)
        report_action.update({'close_on_report_download': True})
        return report_action
