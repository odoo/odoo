import markupsafe

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError


def _prepare_data(env, docids, data):
    # change product ids by actual product object to get access to fields in xml template
    # we needed to pass ids because reports only accepts native python types (int, float, strings, ...)

    layout_wizard = env['product.label.layout'].browse(data.get('layout_wizard'))
    if data.get('active_model') == 'product.template':
        Product = env['product.template'].with_context(display_default_code=False)
    elif data.get('active_model') == 'product.product':
        Product = env['product.product'].with_context(display_default_code=False)
    elif data.get("studio") and docids:
        # special case: users trying to customize labels
        products = env['product.template'].with_context(display_default_code=False).browse(docids)
        quantity_by_product = defaultdict(list)
        for product in products:
            quantity_by_product[product].append((product.barcode, 1))
        return {
            'quantity': quantity_by_product,
            'page_numbers': 1,
            'pricelist': layout_wizard.pricelist_id,
        }
    else:
        raise UserError(_('Product model not defined, Please contact your administrator.'))

    if not layout_wizard:
        return {}

    total = 0
    qty_by_product_in = data.get('quantity_by_product')
    # search for products all at once, ordered by name desc since popitem() used in xml to print the labels
    # is LIFO, which results in ordering by product name in the report
    products = Product.search([('id', 'in', [int(p) for p in qty_by_product_in.keys()])], order='name desc')
    quantity_by_product = defaultdict(list)
    for product in products:
        q = qty_by_product_in[str(product.id)]
        quantity_by_product[product].append((product.barcode, q))
        total += q
    if data.get('custom_barcodes'):
        # we expect custom barcodes format as: {product: [(barcode, qty_of_barcode)]}
        for product, barcodes_qtys in data.get('custom_barcodes').items():
            quantity_by_product[Product.browse(int(product))] += (barcodes_qtys)
            total += sum(qty for _, qty in barcodes_qtys)

    return {
        'quantity': quantity_by_product,
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


class ReportProductReport_Producttemplatelabel_Dymo(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel_dymo'
    _description = 'Product Label Report'

    def _get_report_values(self, docids, data):
        return _prepare_data(self.env, docids, data)


class ReportProductReport_Producttemplatelabel_Zpl(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel_zpl'
    _description = 'Product Label Report ZPL'

    def _get_report_values(self, docids, data):
        if data.get('active_model') == 'product.template':
            Product = self.env['product.template']
        elif data.get('active_model') == 'product.product':
            Product = self.env['product.product']
        else:
            raise UserError(self.env._('Product model not defined, Please contact your administrator.'))

        quantity_by_product = defaultdict(list)
        for p, q in data.get('quantity_by_product').items():
            product = Product.browse(int(p))
            default_code_markup = markupsafe.Markup(product.default_code) if product.default_code else ''
            product_info = {
                'barcode': markupsafe.Markup(product.barcode) if product.barcode else '',
                'quantity': q,
                'display_name_markup': markupsafe.Markup(product.display_name),
                'default_code': (default_code_markup[:15], default_code_markup[15:30])
            }
            quantity_by_product[product].append(product_info)
        if data.get('custom_barcodes'):
            # we expect custom barcodes to be: {product: [(barcode, qty_of_barcode)]}
            for product, barcodes_qtys in data.get('custom_barcodes').items():
                product = Product.browse(int(product))
                default_code_markup = markupsafe.Markup(product.default_code) if product.default_code else ''
                for barcode_qty in barcodes_qtys:
                    quantity_by_product[product].append({
                        'barcode': markupsafe.Markup(barcode_qty[0]),
                        'quantity': barcode_qty[1],
                        'display_name_markup': markupsafe.Markup(product.display_name),
                        'default_code': (default_code_markup[:15], default_code_markup[15:30])
                    })
        data['quantity'] = quantity_by_product
        layout_wizard = self.env['product.label.layout'].browse(data.get('layout_wizard'))
        data['pricelist'] = layout_wizard.pricelist_id

        return data
