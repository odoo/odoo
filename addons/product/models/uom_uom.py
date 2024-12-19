# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _


class UomUom(models.Model):
    _inherit = 'uom.uom'

    packaging_barcodes_count = fields.Integer('Packaging Barcodes', compute='_compute_packaging_barcodes_count')

    def _compute_packaging_barcodes_count(self):
        for uom in self:
            uom.packaging_barcodes_count = self.env['product.uom'].search_count([('uom_id', '=', uom.id)])

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
