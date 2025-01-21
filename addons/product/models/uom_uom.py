# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class UomUom(models.Model):
    _inherit = 'uom.uom'

    product_uom_ids = fields.One2many('product.uom', 'uom_id', string='Barcodes', domain=lambda self: ['|', ('product_id', '=', self.env.context.get('product_id')), ('product_id', 'in', self.env.context.get('product_ids', []))])

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
