from odoo import models, fields


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    product_ids = fields.One2many('product.template', 'serial_sequence_id')

    def write(self, vals):
        res = super().write(vals)
        if 'prefix' in vals:
            self.product_ids.serial_prefix_format = vals['prefix']
        return res
