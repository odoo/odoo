# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.osv import expression


class UomUom(models.Model):
    _inherit = 'uom.uom'

    product_uom_ids = fields.One2many('product.uom', 'uom_id', string='Barcodes', domain=lambda self: self._domain_product_uoms())

    def _domain_product_uoms(self):
        clauses = []
        if self.env.context.get("product_id"):
            clauses.append([("product_id", "=", self.env.context["product_id"])])
        if self.env.context.get("product_ids"):
            clauses.append([("product_id", "in", self.env.context["product_ids"])])
        return expression.OR(clauses) if clauses else []

    def action_open_packaging_barcodes(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Packaging Barcodes'),
            'res_model': 'product.uom',
            'view_mode': 'list',
            'view_id': self.env.ref('product.product_uom_list_view').id,
            'domain': [('uom_id', '=', self.id)],
        }
