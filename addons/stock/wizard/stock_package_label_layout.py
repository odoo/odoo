from odoo import api, models
from odoo.tools import format_date


class PackageLabelLayout(models.TransientModel):
    _name = 'stock.package.label.layout'
    _description = 'Prepare Package Labels'

    @api.model
    def _process_report_data(self, data, print_format):
        report_xml_id = 'product.report_product_template_label_zpl' if print_format == 'zpl' else 'product.action_report_product_label_pdf'
        action = self.env.ref(report_xml_id).report_action(None, data=data, config=False)
        action['close_on_report_download'] = True
        return action

    @api.model
    def _prepare_package_label_values(self, package):
        barcode = package.name
        if package.valid_sscc:
            barcode = f'00{barcode}'
            if package.pack_date:
                barcode += f"13{package.pack_date.strftime('%y%m%d')}"
        return {
            'barcode_type': 'datamatrix' if package.valid_sscc else 'barcode',
            'barcode_value': barcode,
            'barcode_text': package.name,
            'copies': 1,
            'is_sscc': package.valid_sscc,
            'name': package.name,
            'pack_date': format_date(self.env, package.pack_date) if package.pack_date else '',
            'package_type': package.package_type_id.display_name or '',
        }

    @api.model
    def _prepare_report_data_for_packages(self, package_ids, print_format):
        packages = self.env['stock.package'].browse(package_ids)
        return {
            'labels': [self._prepare_package_label_values(package) for package in packages],
            'label_template': 'stock.package_zpl_label' if print_format == 'zpl' else 'stock.package_pdf_label',
            'layout': {
                'rows': 1,
                'columns': 1,
            },
        }

    @api.model
    def _process_package_labels(self, packages, print_format):
        data = self._prepare_report_data_for_packages(packages.ids, print_format)
        return self._process_report_data(data, print_format)
