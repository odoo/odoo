# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class SaleReport(models.Model):
    _inherit = "sale.report"

    product_public_category_id = fields.Many2one('product.public.category', string='Website Product Category', readonly=True)

    def _select(self):
        return super(SaleReport, self)._select() + ", ppc.product_public_category_id as product_public_category_id"

    def _from(self):
        return super(SaleReport, self)._from() + "left join product_public_category_product_template_rel ppc on (ppc.product_template_id=t.id)"

    def _group_by(self):
        return super(SaleReport, self)._group_by() + ", ppc.product_public_category_id"
