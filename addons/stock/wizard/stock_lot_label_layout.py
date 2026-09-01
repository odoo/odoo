# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import api, fields, models


class LotLabelLayout(models.TransientModel):
    _name = 'lot.label.layout'
    _description = 'Choose the sheet layout to print lot labels'

    lot_ids = fields.Many2many('stock.lot')
    move_line_ids = fields.Many2many('stock.move.line')
    custom_quantity = fields.Integer(default=1)
    label_quantity = fields.Selection([
        ('lots', 'One per lot/SN'),
        ('units', 'One per unit')], string="Quantity to print", required=True, default='lots', help="If the UoM of a lot is not 'units', the lot will be considered as a unit and only one label will be printed for this lot.")
    print_format = fields.Selection([
        ('4x12', '4 x 12'),
        ('zpl', 'ZPL Labels')], string="Format", default='4x12', required=True)

    @api.model
    def _process_lot_labels(self, lots, print_format, custom_quantity=1):
        wizard = self.create({
            'lot_ids': lots.ids,
            'custom_quantity': custom_quantity,
            'print_format': print_format,
        })
        return wizard.process()

    def _prepare_lot_gs1_barcode_extra_data(self, lot):
        return ''

    def _prepare_lot_gs1_barcode(self, lot):
        barcode = ''
        if lot.product_id.valid_ean:
            barcode = f"01{lot.product_id.barcode.rjust(14, '0')}"

        barcode += self._prepare_lot_gs1_barcode_extra_data(lot)
        if lot.product_id.tracking == 'lot':
            barcode += f'10{lot.name}'
        elif lot.product_id.tracking == 'serial':
            barcode += f'21{lot.name}'
        return barcode

    def _prepare_lot_quantities(self):
        self.ensure_one()

        if self.lot_ids:
            return {lot: self.custom_quantity for lot in self.lot_ids}

        if self.label_quantity == 'lots':
            return {lot: 1 for lot in self.move_line_ids.lot_id}

        uom_unit = self.env.ref('uom.product_uom_unit')
        quantity_by_lot = defaultdict(int)
        for move_line in self.move_line_ids:
            if not move_line.lot_id:
                continue
            if move_line.uom_id._has_common_reference(uom_unit):
                quantity_by_lot[move_line.lot_id] += int(move_line.quantity)
            else:
                quantity_by_lot[move_line.lot_id] += 1
        return quantity_by_lot

    def _prepare_label_values(self, lot, copies):
        product = lot.product_id.with_context(display_default_code=False)
        gs1_barcode = self._prepare_lot_gs1_barcode(lot) if self.env.user.has_group('stock.group_stock_lot_print_gs1') else ''
        return {
            'barcode_value': gs1_barcode or lot.name,
            'barcode_text': lot.name,
            'copies': copies,
            'name': product.display_name,
            'reference': lot.product_id.default_code or '',
        }

    def _get_report_xml_ids(self):
        self.ensure_one()
        barcode_format = 'qr' if self.env.user.has_group('stock.group_stock_lot_print_gs1') else 'barcode'
        if self.print_format == 'zpl':
            return 'product.report_product_template_label_zpl', f'stock.lot_{barcode_format}_alternative_label'
        return 'product.action_report_product_label_pdf', f'stock.lot_{barcode_format}_4x12_label'

    def _prepare_report_data(self):
        self.ensure_one()
        report_xml_id, label_template_xml_id = self._get_report_xml_ids()
        return report_xml_id, {
            'labels': [
                self._prepare_label_values(lot, copies)
                for lot, copies in self._prepare_lot_quantities().items()
            ],
            'label_template': label_template_xml_id,
            'layout': {
                'rows': 12 if self.print_format == '4x12' else 1,
                'columns': 4 if self.print_format == '4x12' else 1,
            },
        }

    def process(self):
        self.ensure_one()
        xml_id, data = self._prepare_report_data()
        report_action = self.env.ref(xml_id).report_action(None, data=data, config=False)
        report_action.update({'close_on_report_download': True})
        return report_action
