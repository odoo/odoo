# -*- coding: utf-8 -*-
# JUAN PABLO YAÑEZ CHAPITAL

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    brand_id = fields.Many2one("product.brand", string="Brand")


class ResPartner(models.Model):
    _inherit = "res.partner"

    brand_id = fields.Many2many("product.brand", 'rel_product_branch', string="Brand")

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    brand_id = fields.Many2one(
        "product.brand", string="Brand", related="product_id.brand_id")

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if not self.product_id:
            return
        if self.product_id.brand_id and self.order_id.partner_id not in self.product_id.brand_id.partner_ids:
            warning_mess = {
                'message': ('Vendor Probably don’t SELL that Brand.'),
                'title': "Warning"
            }

            return {'warning': warning_mess}
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    brand_id = fields.Many2one(
        "product.brand", string="Brand", related="product_id.brand_id")

    def open_brand_view(self):
        ctx = {
            'default_name': self.brand_id.name,
            'default_brand_image': self.brand_id.brand_image,
            'default_partner_ids': self.brand_id.partner_ids.ids,
        }

        return{
            'name': 'Brand',
            'res_model': 'product.brand',
            'view_mode': 'form',
            'view_id': self.env.ref('product_brand.product_brand_form_view2').id,
            'context': ctx,
            'target': 'new',
            'type': 'ir.actions.act_window'
        }
