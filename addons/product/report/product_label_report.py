import markupsafe

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError


class ReportProductLabelBase(models.AbstractModel):
    _name = 'report.product.label.base'
    _description = 'Base Product Label Report'

    def _show_base_unit_price(self):
        return self.env['res.groups']._is_feature_enabled('product.group_show_uom_price')

    def _prepare_label(self, product, barcode, pricelist, extra_html, price_included):
        currency_id = pricelist.currency_id or product.currency_id
        price = pricelist._get_product_price(product, 1, currency=currency_id)
        base_unit_price = (
            product._get_base_unit_price(price)
            if self._show_base_unit_price() and product.base_unit_count and product.base_unit_name
            else 0
        )
        return {
            'barcode': barcode,
            'identifier_text': barcode or '',
            'base_unit_name': product.base_unit_name or '',
            'base_unit_price': base_unit_price,
            'product_code': product.default_code or '',
            'currency_id': currency_id,
            'extra_html': extra_html,
            'invisible': False,
            'label_class': 'o_label_with_price' if price_included else 'o_label_without_meta_block',
            'price': price,
            'price_included': price_included,
            'title': product.display_name if product.is_product_variant else product.name,
        }

    def _prepare_invisible_label(self):
        return {'invisible': True}

    def _prepare_labels(self, quantity_by_product, pricelist, extra_html, price_included):
        labels = []
        for product, barcodes_qtys in quantity_by_product.items():
            for barcode, quantity in barcodes_qtys:
                for _qty in range(quantity):
                    labels.append(self._prepare_label(
                        product, barcode, pricelist, extra_html, price_included
                    ))
        return labels

    def _organize_labels(self, labels, rows=1, columns=1):
        slots_per_page = rows * columns
        if not labels:
            return []

        organized_pages = []
        for page_start in range(0, len(labels), slots_per_page):
            page_labels = list(labels[page_start:page_start + slots_per_page])
            while len(page_labels) < slots_per_page:
                page_labels.append(self._prepare_invisible_label())
            organized_pages.append([
                page_labels[row_start:row_start + columns]
                for row_start in range(0, slots_per_page, columns)
            ])
        return organized_pages

    def _get_report_label_values(self, labels, rows, columns):
        label_pages = self._organize_labels(labels, rows=rows, columns=columns)
        return {
            'label_pages': label_pages,
            'page_numbers': len(label_pages),
        }

    def _get_product_model(self, data):
        if data.get('active_model') == 'product.template':
            return self.env['product.template'].with_context(display_default_code=False)
        if data.get('active_model') == 'product.product':
            return self.env['product.product'].with_context(display_default_code=False)
        raise UserError(_('Product model not defined, Please contact your administrator.'))

    def _build_quantity_by_product(self, Product, docids, data):
        quantity_by_product = defaultdict(list)
        if data.get("studio") and docids:
            products = self.env['product.template'].with_context(display_default_code=False).browse(docids)
            for product in products:
                quantity_by_product[product].append((product.barcode, 1))

        qty_by_product_in = data.get('quantity_by_product')
        if qty_by_product_in:
            products = Product.search([('id', 'in', [int(p) for p in qty_by_product_in])], order='name desc')
            for product in products:
                quantity_by_product[product].append((product.barcode, qty_by_product_in[str(product.id)]))
        if data.get('custom_barcodes'):
            for product, barcodes_qtys in data.get('custom_barcodes').items():
                quantity_by_product[Product.browse(int(product))] += barcodes_qtys
        return quantity_by_product

    def _prepare_data(self, docids, data):
        layout_wizard = self.env['product.label.layout'].browse(data.get('layout_wizard'))
        if not layout_wizard:
            return {}

        Product = self._get_product_model(data)
        quantity_by_product = self._build_quantity_by_product(Product, docids, data)
        report_values = {
            'quantity': quantity_by_product,
            'price_included': data.get('price_included'),
            'extra_html': layout_wizard.extra_html,
            'pricelist': layout_wizard.pricelist_id,
        }
        labels = self._prepare_labels(
            quantity_by_product, layout_wizard.pricelist_id, layout_wizard.extra_html,
            data.get('price_included'),
        )
        report_values.update(self._get_report_label_values(labels, layout_wizard.rows, layout_wizard.columns))

        return report_values


class ReportProductReport_Producttemplatelabel2x7(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel2x7'
    _inherit = 'report.product.label.base'
    _description = 'Product Label Report 2x7'

    def _get_report_values(self, docids, data):
        return self._prepare_data(docids, data)


class ReportProductReport_Producttemplatelabel4x7(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel4x7'
    _inherit = 'report.product.label.base'
    _description = 'Product Label Report 4x7'

    def _get_report_values(self, docids, data):
        return self._prepare_data(docids, data)


class ReportProductReport_Producttemplatelabel4x12(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel4x12'
    _inherit = 'report.product.label.base'
    _description = 'Product Label Report 4x12'

    def _get_report_values(self, docids, data):
        return self._prepare_data(docids, data)


class ReportProductReport_Producttemplatelabel_Dymo(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel_dymo'
    _inherit = 'report.product.label.base'
    _description = 'Product Label Report'

    def _get_report_label_values(self, labels, rows, columns):
        return {
            'dymo_labels': labels,
            'page_numbers': len(labels),
        }

    def _get_report_values(self, docids, data):
        return self._prepare_data(docids, data)


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


class ReportProductPackagingBarcode(models.AbstractModel):
    _name = 'report.product.report_packagingbarcode'
    _inherit = 'report.product.label.base'
    _description = 'Product Packaging Barcode Report'

    def _prepare_packaging_label(self, packaging):
        product = packaging.product_id
        return {
            'barcode': packaging.barcode,
            'identifier_text': packaging.barcode or '',
            'base_unit_name': '',
            'base_unit_price': 0,
            'product_code': product.default_code or '',
            'currency_id': False,
            'extra_html': False,
            'invisible': False,
            'price': 0,
            'price_included': False,
            'title': product.name,
            'uom_name': packaging.uom_id.name,
        }

    def _prepare_packaging_labels(self, docs):
        return [self._prepare_packaging_label(packaging) for packaging in docs]

    def _prepare_data(self, docids, data):
        docs = self.env['product.uom'].browse(docids)
        label_pages = self._organize_labels(
            self._prepare_packaging_labels(docs),
            rows=7, columns=4,
        )
        return {
            'doc_ids': docids,
            'doc_model': 'product.uom',
            'docs': docs,
            'label_pages': label_pages,
            'page_numbers': len(label_pages),
        }

    def _get_report_values(self, docids, data):
        return self._prepare_data(docids, data)
