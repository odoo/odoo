# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class UomUom(models.Model):
    _inherit = 'uom.uom'

    @api.model
    def _domain_product_uom_ids(self):
        domain = []
        if self.env.context.get('product_ids'):
            domain = [('product_id', 'in', self.env.context['product_ids'])]
        elif self.env.context.get('product_id'):
            domain = [('product_id', '=', self.env.context['product_id'])]
        return domain

    product_uom_ids = fields.One2many(
        'product.uom', 'uom_id', string='Barcodes',
        domain=lambda self: self._domain_product_uom_ids(),
    )

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
