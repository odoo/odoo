# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model_create_multi
    def create(self, vals_list):
        orders = super(SaleOrder, self).create(vals_list)
        for order in orders:
            for line in order.order_line:
                if (line.product_id.min_qty and (line.product_uom_qty < line.product_id.min_qty)) or (line.product_id.max_qty and (line.product_uom_qty > line.product_id.max_qty)):
                    raise ValidationError(_("Please Check Minimum and Maximum Quantity Limit of %s " % (line.product_id.name)))
        return orders

    def action_confirm(self):
        for order in self:
            for line in order.order_line:
                if (line.product_id.min_qty and (line.product_uom_qty < line.product_id.min_qty)) or (line.product_id.max_qty and (line.product_uom_qty > line.product_id.max_qty)):
                    raise ValidationError(_("Please Check Minimum and Maximum Quantity Limit of %s " % (line.product_id.name)))
        return super(SaleOrder, self).action_confirm()

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_uom_qty')
    def onchange_product_uom_qty(self):
        for line in self:
             if (line.product_id.min_qty and (line.product_uom_qty < line.product_id.min_qty)) or (line.product_id.max_qty and (line.product_uom_qty > line.product_id.max_qty)):
                    raise ValidationError(_("Please Check Minimum and Maximum Quantity Limit of %s " % (line.product_id.name)))