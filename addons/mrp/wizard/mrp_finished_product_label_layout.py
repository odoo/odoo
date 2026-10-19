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
        moves = self.move_ids.filtered_domain([
            ('production_id.state', '=', 'done'),
            ('state', '=', 'done'),
            ('quantity', '!=', 0),
        ])
        label_requests = []
        for move in moves:
            product = move.product_id
            label_uom = move.production_id.uom_id if product == move.production_id.product_id else move.uom_id
            label_values = [(product.barcode, move.quantity, move.uom_id)]
            if product.tracking != 'none':
                label_values = [
                    (line.lot_name or line.lot_id.name, line.quantity, line.uom_id)
                    for line in move.move_line_ids
                    if line.quantity
                ]
            for barcode, quantity, quantity_uom in label_values:
                label_quantity = quantity_uom._compute_quantity(quantity, label_uom)
                label_requests.append({
                    'product': product,
                    'barcode_value': barcode,
                    'copies': 1,
                    'packaging': self.env['uom.uom'],
                    'secondary_text': f'{label_quantity:g} {label_uom.display_name}',
                })
        return label_requests
