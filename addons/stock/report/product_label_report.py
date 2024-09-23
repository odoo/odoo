# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError

import markupsafe

class ReportProductLabel(models.AbstractModel):
    _name = 'report.stock.label_product_product_view'
    _description = 'Product Label Report'

    def _get_report_values(self, docids, data):
        if data.get('active_model') == 'product.template':
            Product = self.env['product.template']
        elif data.get('active_model') == 'product.product':
            Product = self.env['product.product']
        else:
            raise UserError(_('Product model not defined, Please contact your administrator.'))

        quantity = defaultdict(list)
        for p, q in data.get('quantity_by_product').items():
            product = Product.browse(int(p))
            default_code_markup = markupsafe.Markup(product.default_code) if product.default_code else ''
            product_info = {
                'barcode': markupsafe.Markup(product.barcode) if product.barcode else '',
                'quantity': q,
                'display_name_markup': markupsafe.Markup(product.display_name),
                'default_code': (default_code_markup[:15], default_code_markup[15:30]),
                'type': 'product'
            }
            quantity[product].append(product_info)
        if data.get('custom_barcodes'):
            # we expect custom barcodes to be: {product: [(barcode, qty_of_barcode)]}
            for product, barcodes_qtys in data.get('custom_barcodes').items():
                product = Product.browse(int(product))
                default_code_markup = markupsafe.Markup(product.default_code) if product.default_code else ''
                for (barcode, qty) in barcodes_qtys:
                    quantity[product].append({
                        'barcode': markupsafe.Markup(barcode),
                        'quantity': qty,
                        'display_name_markup': markupsafe.Markup(product.display_name),
                        'default_code': (default_code_markup[:15], default_code_markup[15:30]),
                        'type': 'product'
                    })

        if data.get('quantity_by_packaging'):
            packaging_ids = [int(p) for p in data['quantity_by_packaging']]
            packagings = self.env['product.packaging'].search([('id', 'in', packaging_ids)], order='name desc')
            for packaging in packagings:
                default_code_markup = markupsafe.Markup(packaging.product_id.default_code) if packaging.product_id.default_code else ''
                quantity[packaging].append({
                    'barcode': markupsafe.Markup(packaging.barcode) if packaging.barcode else '',
                    'quantity': packaging.qty,
                    'display_name_markup': markupsafe.Markup(packaging.display_name),
                    'default_code': (default_code_markup[:15], default_code_markup[15:30]),
                    'type': 'packaging'
                })

        data['quantity'] = quantity
        layout_wizard = self.env['product.label.layout'].browse(data.get('layout_wizard'))
        data['pricelist'] = layout_wizard.pricelist_id

        return data


class ReportLotLabel(models.AbstractModel):
    _name = 'report.stock.label_lot_template_view'
    _description = 'Lot Label Report'

    def _get_report_values(self, docids, data):
        lots = self.env['stock.lot'].browse(docids)
        lot_list = []
        for lot in lots:
            lot_list.append({
                'display_name_markup': markupsafe.Markup(lot.product_id.display_name),
                'name': markupsafe.Markup(lot.name),
                'lot_record': lot
            })
        return {
            'docs': lot_list,
        }
