# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError


def _prepare_data(env, docids, data):
    # change product ids by actual product object to get access to fields in xml template
    # we needed to pass ids because reports only accepts native python types (int, float, strings, ...)
    labels = defaultdict(list)
    data_by_product_id = data.get('data_by_product_id', defaultdict(list))

    layout_wizard = env['product.label.layout'].browse(data.get('layout_wizard'))
    if data.get('active_model') == 'product.template':
        Product = env['product.template'].with_context(display_default_code=False)
    elif data.get('active_model') == 'product.product':
        Product = env['product.product'].with_context(display_default_code=False)
    elif data.get("studio") and docids:
        # special case: users trying to customize labels
        products = env['product.template'].with_context(display_default_code=False).browse(docids)
        for product in products:
            labels_data = data_by_product_id.get(str(product.id), [])
            for data in labels_data:
                label_data = {
                    'barcode': data['barcode'],
                    'quantity': data['quantity'],
                }
                labels[product].append(label_data)
        return {
            'labels': labels,
            'page_numbers': 1,
            'pricelist': layout_wizard.pricelist_id,
        }
    else:
        raise UserError(_('Product model not defined, Please contact your administrator.'))

    if not layout_wizard:
        return {}

    total = 0
    # search for products all at once, ordered by name desc since popitem() used in xml to print the labels
    # is LIFO, which results in ordering by product name in the report
    product_ids = [int(str_product_id) for str_product_id in data_by_product_id]
    products = Product.search([('id', 'in', product_ids)], order='name desc')
    for product in products:
        labels_data = data_by_product_id.get(str(product.id), [])
        for data in labels_data:
            label_data = {
                'barcode': data['barcode'],
                'quantity': data['quantity'],
            }
            if data.get('uom_id'):
                # If there is an UoM, the packaging's barcode will be printed instead of the product's barcode.
                uom = env['uom.uom'].browse(int(data['uom_id']))
                packaging = env['product.uom'].browse(int(data.get('packaging_id')))
                label_data.update(uom=uom, packaging=packaging)

            total += data['quantity']
            labels[product].append(label_data)

    # TODO: To adapt
    if data.get('custom_barcodes'):
        # we expect custom barcodes format as: {product: [('product', barcode, qty_of_barcode)]}
        for product_id, barcodes_qtys in data.get('custom_barcodes').items():
            product = Product.browse(int(product_id))
            labels[product].append(barcodes_qtys)
            total += sum(qty for _type, _barcode, qty in barcodes_qtys)

    return {
        'labels': labels,
        'page_numbers': (total - 1) // (layout_wizard.rows * layout_wizard.columns) + 1,
        'price_included': data.get('price_included'),
        'extra_html': layout_wizard.extra_html,
        'pricelist': layout_wizard.pricelist_id,
    }


class ReportProductReport_Producttemplatelabel2x7(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel2x7'
    _description = 'Product Label Report 2x7'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportProductReport_Producttemplatelabel4x7(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel4x7'
    _description = 'Product Label Report 4x7'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportProductReport_Producttemplatelabel4x12(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel4x12'
    _description = 'Product Label Report 4x12'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportProductReport_Producttemplatelabel4x12noprice(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel4x12noprice'
    _description = 'Product Label Report 4x12 No Price'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportProductReport_Producttemplatelabel_Dymo(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel_dymo'
    _description = 'Product Label Report'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)
