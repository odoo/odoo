from odoo import api, models


class PackageTypeLabelLayout(models.TransientModel):
    _name = 'stock.package.type.label.layout'
    _description = 'Prepare Package Type Labels'

    @api.model
    def _process_report_data(self, data, print_format):
        report_xml_id = 'product.report_product_template_label_zpl' if print_format == 'zpl' else 'product.action_report_product_label_pdf'
        action = self.env.ref(report_xml_id).report_action(None, data=data, config=False)
        action['close_on_report_download'] = True
        return action

    @api.model
    def _prepare_report_data_for_package_types(self, package_type_ids, print_format):
        package_types = self.env['stock.package.type'].browse(package_type_ids)
        data = {
            'labels': [{
                'barcode_value': package_type.barcode or '',
                'barcode_text': package_type.barcode or '',
                'name': package_type.name,
            } for package_type in package_types],
            'label_template': f"stock.package_type_barcode_{'zpl' if print_format == 'zpl' else '4x7'}_label",
        }
        if print_format == '4x7':
            data['layout'] = {
                'rows': 7,
                'columns': 4,
            }
        return data

    @api.model
    def _process_package_type_labels(self, package_types, print_format):
        data = self._prepare_report_data_for_package_types(package_types.ids, print_format)
        return self._process_report_data(data, print_format)
