# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    supplier_id = fields.Many2one("product.supplierinfo", string="Vendor")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        product_id = self.env['product.product'].browse(res.get('product_id'))
        product_tmpl_id = product_id.product_tmpl_id
        orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', product_tmpl_id.product_variant_id.id)])
        if orderpoint:
            res['supplier_id'] = orderpoint.supplier_id.id
        elif product_tmpl_id.seller_ids:
            res['supplier_id'] = product_tmpl_id.seller_ids[0].id
        return res

    def _prepare_run_values(self):
        res = super()._prepare_run_values()
        res['supplierinfo_partner_id'] = self.supplier_id.partner_id
        return res
