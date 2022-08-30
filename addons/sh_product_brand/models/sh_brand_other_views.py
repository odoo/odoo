# -*- coding: utf-8 -*-
# JUAN PABLO YAÑEZ CHAPITAL

from odoo import models, fields, api


class ShProductTemplate(models.Model):
    _inherit = "product.template"

    sh_brand_id = fields.Many2one("sh.product.brand", string="Brand")


class ResPartner(models.Model):
    _inherit = "res.partner"

    sh_brand_id = fields.Many2many("sh.product.brand", 'rel_product_branch', string="Brand")

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    sh_brand_id = fields.Many2one(
        "sh.product.brand", string="Brand", related="product_id.sh_brand_id")

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(PurchaseOrderLine, self).onchange_product_id()
        if not self.product_id:
            return
        if self.product_id.sh_brand_id and self.order_id.partner_id not in self.product_id.sh_brand_id.sh_partner_ids:
            warning_mess = {
                'message': ('Vendor Probably don’t SELL that Brand.'),
                'title': "Warning"
            }

            return {'warning': warning_mess}
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sh_brand_id = fields.Many2one(
        "sh.product.brand", string="Brand", related="product_id.sh_brand_id")

    def open_brand_view(self):
        ctx = {
            'default_name': self.sh_brand_id.name,
            'default_sh_brand_image': self.sh_brand_id.sh_brand_image,
            'default_sh_partner_ids': self.sh_brand_id.sh_partner_ids.ids,
        }

        return{
            'name': 'Brand',
            'res_model': 'sh.product.brand',
            'view_mode': 'form',
            'view_id': self.env.ref('sh_product_brand.sh_product_brand_form_view2').id,
            'context': ctx,
            'target': 'new',
            'type': 'ir.actions.act_window'
        }
