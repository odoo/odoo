# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _


class UomUom(models.Model):
    _inherit = 'uom.uom'

    product_uom_ids = fields.One2many('product.uom', 'uom_id', string='Barcodes', domain=lambda self: ['|', ('product_id', '=', self.env.context.get('product_id')), ('product_id', 'in', self.env.context.get('product_ids', []))])
<<<<<<< master
||||||| 6e4ca1e184db037b191d707ae7a06a2f630ee4ab
    packaging_barcodes_count = fields.Integer('Packaging Barcodes', compute='_compute_packaging_barcodes_count')

    @api.depends('product_uom_ids')
    def _compute_packaging_barcodes_count(self):
        uom_to_barcode_count = dict(self.env['product.uom']._read_group(
            [('uom_id', 'in', self.ids)], ['uom_id'], ['barcode:count'],
        ))
        for uom in self:
            uom.packaging_barcodes_count = uom_to_barcode_count.get(uom, 0)
=======
    packaging_barcodes_count = fields.Integer('Packaging Barcodes', compute='_compute_packaging_barcodes_count')

    @api.depends('product_uom_ids')
    def _compute_packaging_barcodes_count(self):
        uom_to_barcode_count = dict(self.env['product.uom']._read_group(
            [('uom_id', 'in', self.ids)], ['uom_id'], ['barcode:count'],
        ))
        for uom in self:
            uom.packaging_barcodes_count = uom_to_barcode_count.get(uom, 1)  # We always want to show the barcodes smart button
>>>>>>> 20968dd4194fc95ca52509b813a3297220385496

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
