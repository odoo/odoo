# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ChooseDeliveryPackage(models.TransientModel):
    _name = 'choose.delivery.package'
    _description = 'Delivery Package Selection Wizard'

    stock_quant_package_id = fields.Many2one(
        'stock.quant.package',
        string="Physical Package",
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
    weight_uom_name = fields.Char(string='Weight unit of measure label', compute='_compute_weight_uom_name')

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
            move_line_ids = [po for po in picking_id.move_line_ids if po.qty_done > 0 and not po.result_package_id]
            total_weight = sum([po.qty_done * po.product_id.weight for po in move_line_ids])
            return total_weight

    @api.depends('stock_quant_package_id', 'delivery_packaging_id')
    def _compute_weight_uom_name(self):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        for package in self:
            package.weight_uom_name = weight_uom_id.name

    @api.onchange('delivery_packaging_id', 'shipping_weight')
    def _onchange_packaging_weight(self):
        if self.delivery_packaging_id.max_weight and self.shipping_weight > self.delivery_packaging_id.max_weight:
            warning_mess = {
                'title': _('Package too heavy!'),
                'message': _('The weight of your package is higher than the maximum weight authorized for this package type. Please choose another package type.')
            }
            return {'warning': warning_mess}

    def put_in_pack(self):
        # write shipping weight and product_packaging on 'stock_quant_package' if needed
        if self.delivery_packaging_id:
            self.stock_quant_package_id.packaging_id = self.delivery_packaging_id
            if self.shipping_weight:
                self.stock_quant_package_id.shipping_weight = self.shipping_weight
