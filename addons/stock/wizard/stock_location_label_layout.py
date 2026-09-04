from odoo import api, models


class LocationLabelLayout(models.TransientModel):
    _name = 'stock.location.label.layout'
    _description = 'Prepare Location Labels'

    @api.model
    def _process_report_data(self, data, print_format):
        report_xml_id = 'product.report_product_template_label_zpl' if print_format == 'zpl' else 'product.action_report_product_label_pdf'
        action = self.env.ref(report_xml_id).report_action(None, data=data, config=False)
        action['close_on_report_download'] = True
        return action

    @api.model
    def _prepare_report_data_for_locations(self, location_ids, print_format):
        locations = self.env['stock.location'].browse(location_ids)
        data = {
            'labels': [{
                'barcode_value': location.barcode or location.name,
                'barcode_text': location.barcode or '',
                'name': location.display_name,
            } for location in locations],
            'label_template': f"stock.location_barcode_{'zpl' if print_format == 'zpl' else '4x7'}_label",
        }
        if print_format == '4x7':
            data['layout'] = {
                'rows': 7,
                'columns': 4,
            }
        return data

    @api.model
    def _process_location_labels(self, locations, print_format):
        data = self._prepare_report_data_for_locations(locations.ids, print_format)
        return self._process_report_data(data, print_format)
