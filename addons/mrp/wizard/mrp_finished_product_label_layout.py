from odoo import api, models


class MrpFinishedProductLabelLayout(models.TransientModel):
    _name = 'mrp.finished.product.label.layout'
    _inherit = 'product.label.layout'
    _description = 'Finished Product Label Layout'

    @api.model
    def _process_finished_product_labels(self, productions, print_format):
        wizard = self.create({
            'move_ids': productions.move_finished_ids.ids,
            'move_quantity': 'move',
            'print_format': '4x12' if print_format == 'pdf' else 'zpl',
            'with_price': False,
        })
        return wizard.process()

    def _get_label_template_xml_id(self):
        self.ensure_one()
        return f'mrp.finished_product_{self.print_format}_label'

    def _get_label_requests(self):
        self.ensure_one()
        uom_unit = self.env.ref('uom.product_uom_unit')
        move_lines = self.move_ids.move_line_ids.filtered_domain([
            ('move_id.production_id.state', '=', 'done'),
            ('state', '=', 'done'),
            ('quantity', '!=', 0),
        ])
        label_requests = []
        for move_line in move_lines:
            product = move_line.product_id
            is_unit = product.uom_id._has_common_reference(uom_unit)
            barcode = product.barcode
            if product.tracking != 'none':
                barcode = move_line.lot_name or move_line.lot_id.name
            label_quantity = 1 if is_unit else move_line.quantity
            label_requests.append({
                'product': product,
                'barcode_value': barcode,
                'copies': int(move_line.quantity) if is_unit else 1,
                'packaging': self.env['uom.uom'],
                'secondary_text': f'{label_quantity} {move_line.uom_id.display_name}',
            })
        return label_requests
