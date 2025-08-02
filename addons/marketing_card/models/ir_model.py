from odoo import models


class IrModel(models.Model):
    _inherit = 'ir.model'

    def unlink(self):
        """Remove campaigns on removed models."""
        self.env['card.campaign'].search([
            ('res_model', 'in', self.mapped('model'))
        ]).unlink()

        return super().unlink()
