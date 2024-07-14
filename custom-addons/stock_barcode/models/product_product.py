# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.osv import expression


class Product(models.Model):
    _inherit = 'product.product'
    _barcode_field = 'barcode'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        # sudo is added for external users to get the products
        domain = self.env.company.sudo().nomenclature_id._preprocess_gs1_search_args(domain, ['product'])
        return super()._search(domain, offset=offset, limit=limit, order=order, access_rights_uid=access_rights_uid)

    @api.model
    def _get_fields_stock_barcode(self):
        return ['barcode', 'default_code', 'categ_id', 'code', 'detailed_type', 'tracking', 'display_name', 'uom_id']

    def _get_stock_barcode_specific_data(self):
        return {
            'uom.uom': self.uom_id.read(self.env['uom.uom']._get_fields_stock_barcode(), load=False)
        }

    def prefilled_owner_package_stock_barcode(self, lot_id=False, lot_name=False):
        domain = [
            lot_id and ('lot_id', '=', lot_id) or lot_name and ('lot_id.name', '=', lot_name),
            ('product_id', '=', self.id),
            '|', ('package_id', '!=', False), ('owner_id', '!=', False),
        ]

        location_id = self.env.context.get('location_id', {}).get('id')
        if location_id:
            domain = expression.AND([domain, [('location_id', '=', location_id)]])
        else:
            domain = expression.AND([domain, [('location_id.usage', '=', 'internal')]])

        quant = self.env['stock.quant'].search_read(
            domain,
            ['package_id', 'owner_id'],
            limit=1, load=False, order='package_id',
        )
        if quant:
            quant = quant[0]
        res = {'quant': quant, 'records': {}}
        if quant and quant['package_id']:
            res['records']['stock.quant.package'] = self.env['stock.quant.package'].browse(quant['package_id']).read(self.env['stock.quant.package']._get_fields_stock_barcode(), load=False)
        if quant and quant['owner_id']:
            res['records']['res.partner'] = self.env['res.partner'].browse(quant['owner_id']).read(self.env['res.partner']._get_fields_stock_barcode(), load=False)

        return res
