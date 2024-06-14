# -*- coding: utf-8 -*-
# JUAN PABLO YAÑEZ CHAPITAL

from odoo import models, fields
from odoo.tools.translate import html_translate


class ShProductBrand(models.Model):
    _name = "sh.product.brand"
    _description = "Product Brand"
    _rec_name = "name"
    _order = "sh_sequence, id desc"

    name = fields.Char("Name", index=True, required=True, translate=True)
    sh_brand_image = fields.Image("Medium Sized Image", attachment=True)
    sh_sequence = fields.Integer("Sequence", default=1)
    product_ids = fields.One2many(
        "product.template", "sh_brand_id", string="Products ")
    sh_partner_ids = fields.Many2many(
        "res.partner", 'rel_product_branch', string="Vendors")
    sh_description = fields.Html("Description", translate=html_translate)
    active = fields.Boolean(
        "Active", default=True,
        help="If unchecked, it will allow you to hide the product without removing it.")
    sh_cover_image = fields.Image("Cover Image", attachment=True)
    sh_product_count = fields.Integer(
        "Products", compute="_compute_product_counts", translate=True)
    # company_id = fields.Many2one(
    #     "res.company",string="Company",
    #     default=lambda self: self.env.company)
    def _compute_product_counts(self):
        if self:
            for rec in self:
                products = self.env["product.template"].sudo().search(
                    [("sh_brand_id", "=", rec.id)])
                rec.sh_product_count = len(products.ids)

    def action_view_products(self):
        return {
            "name": "Products",
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_type": "form",
            "view_mode": "tree,form",
            "domain": [("sh_brand_id", "in", self.ids)],
            "target": "current"
        }
