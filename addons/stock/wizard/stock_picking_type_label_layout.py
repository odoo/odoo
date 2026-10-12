from odoo import api, models


class PickingTypeLabelLayout(models.TransientModel):
    _name = 'stock.picking.type.label.layout'
    _description = 'Prepare Operation Type Labels'

    @api.model
    def _process_report_data(self, data, print_format):
        report_xml_id = 'product.report_product_template_label_zpl' if print_format == 'zpl' else 'product.action_report_product_label_pdf'
        action = self.env.ref(report_xml_id).report_action(None, data=data, config=False)
        action['close_on_report_download'] = True
        return action

    @api.model
    def _prepare_report_data_for_picking_types(self, picking_type_ids, print_format):
        picking_types = self.env['stock.picking.type'].browse(picking_type_ids)
        data = {
            'labels': [{
                'barcode_value': picking_type.barcode or '',
                'barcode_text': picking_type.barcode or '',
                'name': picking_type.display_name,
            } for picking_type in picking_types],
            'label_template': f"stock.picking_type_barcode_{'zpl' if print_format == 'zpl' else '4x7'}_label",
        }
        if print_format == '4x7':
            data['layout'] = {
                'rows': 7,
                'columns': 4,
            }
        return data

    @api.model
    def _process_picking_type_labels(self, picking_types, print_format):
        data = self._prepare_report_data_for_picking_types(picking_types.ids, print_format)
        return self._process_report_data(data, print_format)
