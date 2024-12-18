# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict, namedtuple

from odoo import _, models
from odoo.exceptions import UserError

import markupsafe


class ReportProductReport_Producttemplatelabel_Zpl(models.AbstractModel):
    _name = 'report.product.report_producttemplatelabel_zpl'
    _description = 'Product Label Report ZPL'

    def _get_report_values(self, docids, data):
        if data.get('active_model') == 'product.template':
            Product = self.env['product.template']
        elif data.get('active_model') == 'product.product':
            Product = self.env['product.product']
        else:
            raise UserError(_('Product model not defined, Please contact your administrator.'))

        ProductInfo = namedtuple('ProductInfo', ('barcode', 'quantity', 'display_name_markup', 'default_code'))
        quantity_by_product = defaultdict(list)
        for p, q in data.get('quantity_by_product').items():
            product = Product.browse(int(p))
            default_code_markup = markupsafe.Markup(product.default_code) if product.default_code else ''
            quantity_by_product[product].append(ProductInfo(markupsafe.Markup(product.barcode) if product.barcode else '',
                                                            q,
                                                            markupsafe.Markup(product.display_name),
                                                            (default_code_markup[:15], default_code_markup[15:30])))
        if data.get('custom_barcodes'):
            # we expect custom barcodes to be: {product: [(barcode, qty_of_barcode)]}
            for product, barcodes_qtys in data.get('custom_barcodes').items():
                product = Product.browse(int(product))
                default_code_markup = markupsafe.Markup(product.default_code) if product.default_code else ''
                for barcode_qty in barcodes_qtys:
                    quantity_by_product[product].append(ProductInfo(markupsafe.Markup(barcode_qty[0]),
                                                                    barcode_qty[1],
                                                                    markupsafe.Markup(product.display_name),
                                                                    (default_code_markup[:15], default_code_markup[15:30])))
        data['quantity'] = quantity_by_product
        layout_wizard = self.env['product.label.layout'].browse(data.get('layout_wizard'))
        data['pricelist'] = layout_wizard.pricelist_id

        return data


class ReportStockLabel_Lot_Template_View(models.AbstractModel):
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
