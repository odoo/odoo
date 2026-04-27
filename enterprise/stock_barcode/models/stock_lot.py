# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockLot(models.Model):
    _inherit = 'stock.lot'
    _barcode_field = 'name'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        # sudo is added for external users to get the lots
        domain = self.env.company.sudo().nomenclature_id._preprocess_gs1_search_args(domain, ['lot'], field='name')
        return super()._search(domain, offset=offset, limit=limit, order=order)

    def _get_stock_barcode_specific_data(self):
        products = self.product_id
        return {
            'product.product': products.read(self.env['product.product']._get_fields_stock_barcode(), load=False),
            'uom.uom': products.uom_id.read(self.env['uom.uom']._get_fields_stock_barcode(), load=False)
        }

    @api.model
    def _get_fields_stock_barcode(self):
        return ['name', 'ref', 'product_id']
