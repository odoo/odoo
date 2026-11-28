# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    purchase_requisition_id = fields.Many2one('purchase.requisition', related='purchase_requisition_line_id.requisition_id', string='Agreement')
    purchase_requisition_line_id = fields.Many2one('purchase.requisition.line', index='btree_not_null')

    def write(self, vals):
        res = super().write(vals)
        if 'date_start' in vals or 'date_end' in vals:
            # keep the validity of the blanket order in sync with its pricelists
            for supplierinfo in self.filtered('purchase_requisition_id'):
                requisition = supplierinfo.purchase_requisition_id
                if requisition.date_start != supplierinfo.date_start or requisition.date_end != supplierinfo.date_end:
                    requisition.sudo().write({
                        'date_start': supplierinfo.date_start,
                        'date_end': supplierinfo.date_end,
                    })
        return res

    @api.depends('purchase_requisition_line_id.remaining_qty')
    def _compute_is_valid(self):
        super()._compute_is_valid()
        precision = self.env['decimal.precision'].precision_get('Product Unit')
        for supplierinfo in self.filtered('is_valid'):
            if supplierinfo.purchase_requisition_line_id and float_compare(
                supplierinfo.purchase_requisition_line_id.remaining_qty, 0.0, precision_digits=precision
            ) <= 0:
                supplierinfo.is_valid = False
