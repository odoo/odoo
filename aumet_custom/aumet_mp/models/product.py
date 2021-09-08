# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    is_mp = fields.Boolean('Aumet Marketplace', default=False)
    name = fields.Many2one(
        'res.partner', 'Vendor',
        domain=[('mp_distributor', '=', True)],
        ondelete='cascade', required=True,
        help="Vendor of this product", check_company=True)

    mp_product_id = fields.Many2one('marketplace.product', string='MP Product',
                                    help='Matching product for this product in marketplace')
    payment_method_id = fields.Many2one('aumet.payment.method', string='Payment Method')

    price = fields.Float(
        'Price', default=0.0, digits='Product Price', compute='_compute_supplierinfo_price', store=True,
        required=True, help="The price to purchase a product")

    @api.depends('is_mp', 'mp_product_id')
    def _compute_supplierinfo_price(self):
        for info in self:
            if info.is_mp and info.mp_product_id:
                info.price = info.mp_product_id.unit_price

    @api.onchange('name', 'is_mp')
    def onchange_marketplace(self):
        for info in self:
            info.mp_product_id = False
            info.price = 0

    @api.onchange('mp_product_id')
    def onchange_product(self):
        if self.mp_product_id:
            return {'domain': {'payment_method_id': [('id', 'in', self.mp_product_id.aumet_payment_method_ids.ids)]}}
        else:
            self.payment_method_id = False
