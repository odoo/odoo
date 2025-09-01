# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from math import floor
import base64
from odoo import api, fields, models
from odoo.tools.misc import file_open

# Format table expressed as width x height in inch.
ZPL_FORMAT_SIZE = {
    'normal': (2.25, 1.25),
    'small': (1.25, 1.00),
    'alternative': (2.00, 1.00),
    'jewelry': (2.20, 0.50),
}


class ProductLabelLayout(models.TransientModel):
    _inherit = 'product.label.layout'

    @api.model
    def _get_zpl_label_placeholder(self):
        with file_open('stock/static/img/zpl_label_placeholder.png', 'rb') as f:
            return base64.b64encode(f.read())

    move_ids = fields.Many2many('stock.move')
    move_quantity = fields.Selection([
        ('move', 'Operation Quantities'),
        ('custom', 'Custom')], string="Quantity to print", required=True, default='custom')
    print_format = fields.Selection(selection_add=[
        ('zpl', 'ZPL Labels'),
        ('zplxprice', 'ZPL Labels with price')
    ], ondelete={'zpl': 'set default', 'zplxprice': 'set default'})
    zpl_template = fields.Selection([
        ('normal', 'Normal (2.25" x 1.25")'),
        ('small', 'Small (1.25" x 1.00")'),
        ('alternative', 'Alternative (2.00" x 1.00")'),
        ('jewelry', 'Jewelry (2.20" x 0.50")'),
    ], string="ZPL Template", default='normal', required=True)
    zpl_preview = fields.Image('ZPL Preview', readonly=True, default=_get_zpl_label_placeholder)
    print_packaging_labels = fields.Boolean(
        string="Packaging labels",
        help="Print only one label per complete packaging")

    @api.depends('print_packaging_labels')
    def _compute_hide_pricelist(self):
        super()._compute_hide_pricelist()
        for wizard in self:
            wizard.hide_pricelist = wizard.hide_pricelist or wizard.print_packaging_labels

    @api.depends_context('display_print_packaging_labels')
    def _compute_hide_uom_id(self):
        super()._compute_hide_uom_id()
        for wizard in self:
            wizard.hide_uom_id = wizard.hide_uom_id or self.env.context.get('display_print_packaging_labels')

    def _prepare_report_data(self):
        xml_id, data = super()._prepare_report_data()

        if 'zpl' in self.print_format:
            xml_id = 'stock.label_product_product'
            data['zpl_template'] = self.zpl_template
        if self.move_quantity == 'custom':
            return xml_id, data

        data_by_product_id = defaultdict(list)
        uom_unit = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)
        if self.move_ids and all(ml.product_uom_id.is_zero(ml.quantity) for ml in self.move_ids.move_line_ids):
            for move in self.move_ids:
                product = move.product_id
                use_reserved = move.product_uom.compare(move.quantity, 0) > 0
                useable_qty = move.quantity if use_reserved else move.product_uom_qty
                data_by_product_id[product.id] += self._get_labels_data_for(move.product_id, useable_qty, move.product_uom)
        elif self.move_ids.move_line_ids:
            custom_barcodes = defaultdict(list)
            for line in self.move_ids.move_line_ids:
                product = line.product_id
                qty = 1
                if line.product_uom_id._has_common_reference(uom_unit):
                    if (line.lot_id or line.lot_name) and int(line.quantity):
                        custom_barcodes[product.id].append((line.lot_id.name or line.lot_name, int(line.quantity)))
                        continue
                    qty = line.packaging_uom_qty
                data_by_product_id[product.id] += self._get_labels_data_for(product, qty, line.move_id.packaging_uom_id)
            data['custom_barcodes'] = custom_barcodes
        data['data_by_product_id'] = data_by_product_id
        return xml_id, data

    def _get_labels_data_for(self, product, quantity=0, uom=False):
        labels = []
        if (uom or product.uom_id).is_zero(quantity):
            return []
        label_data = {
            'barcode': product.barcode or '',
            'quantity': floor(quantity),
        }
        # Adapt label data if we want to print package barcode instead of product barcode.
        if self.print_packaging_labels and uom:
            packaging = uom.product_uom_ids.filtered(lambda p_uom: p_uom.product_id == product)[:1]
            if packaging:
                integer_qty = floor(quantity)
                remaining_qty = quantity - integer_qty
                label_data.update(
                    packaging_id=packaging.id,
                    barcode=(packaging.barcode or ''),
                    uom_id=packaging.uom_id.id,
                    quantity=integer_qty,
                )
                # If packaging qty is a float, try to convert its float part into product's UoM.
                if remaining_qty:
                    product_uom_qty = floor(uom._compute_quantity(
                        remaining_qty,
                        product.uom_id
                    ))
                    if not product.uom_id.is_zero(remaining_qty):
                        labels += self._get_labels_data_for(product, product_uom_qty)
        labels.append(label_data)
        return labels
