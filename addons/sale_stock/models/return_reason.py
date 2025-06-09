# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReturnReason(models.Model):
    _name = 'return.reason'
    _description = "Reason to return a ordered products."
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    barcode = fields.Char(
        string="Barcode",
        copy=False,
        readonly=True,
        index=True,
    )
    sequence = fields.Integer(default=10)

    @api.model
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('barcode'):
                vals['barcode'] = self.env['ir.sequence'].next_by_code('return.reason')

        return super().create(vals_list)
