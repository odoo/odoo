# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ChooseDeliveryPackage(models.TransientModel):
    _name = 'choose.delivery.package'
    _description = 'Delivery Package Selection Wizard'

    stock_quant_package_id = fields.Many2one(
        'stock.quant.package',
        default=lambda self: self._default_stock_quant_package_id()
    ) 
    delivery_packaging_id = fields.Many2one(
        'product.packaging',
        default=lambda self: self._default_delivery_packaging_id()
    )
    shipping_weight = fields.Float(
        string='Shipping Weight',
        default=lambda self: self._default_shipping_weight()
    )

    def _default_stock_quant_package_id(self):
        if self.env.context.get('default_stock_quant_package_id'):
            return self.env['stock.quant.package'].browse(self.env.context['stock_quant_package_id'])

    def _default_delivery_packaging_id(self):
        res = None
        if self.env.context.get('default_delivery_packaging_id'):
            res = self.env['product.packaging'].browse(self.env.context['default_delivery_packaging_id'])
        if self.env.context.get('default_stock_quant_package_id'):
            stock_quant_package = self.env['stock.quant.package'].browse(self.env.context['default_stock_quant_package_id'])
            res = stock_quant_package.packaging_id
        return res

    def _default_shipping_weight(self):
        if self.env.context.get('default_stock_quant_package_id'):
            stock_quant_package = self.env['stock.quant.package'].browse(self.env.context['default_stock_quant_package_id'])
            return stock_quant_package.shipping_weight
        else:
            picking_id = self.env['stock.picking'].browse(self.env.context['active_id'])
            pack_operation_product_ids = [po for po in picking_id.pack_operation_product_ids if po.qty_done > 0 and not po.result_package_id]
            pack_operation_pack_ids = [po for po in picking_id.pack_operation_pack_ids if po.qty_done > 0 and not po.result_package_id]
            total_weight = sum([po.qty_done * po.product_id.weight for po in pack_operation_product_ids]) + sum([po.package_id.weight for po in pack_operation_pack_ids])
            return total_weight

    def put_in_pack(self):
        picking_id = self.env['stock.picking'].browse(self.env.context['active_id'])
        if not self.stock_quant_package_id:
            stock_quant_package = picking_id._put_in_pack()
            self.stock_quant_package_id = stock_quant_package
        # write shipping weight and product_packaging on 'stock_quant_package' if needed
        if self.delivery_packaging_id:
            self.stock_quant_package_id.packaging_id = self.delivery_packaging_id
            if self.shipping_weight:
                self.stock_quant_package_id.shipping_weight = self.shipping_weight
