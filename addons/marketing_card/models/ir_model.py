from odoo import models


class IrModel(models.Model):
    _inherit = 'ir.model'

    def _delete_extra(self):
        yield from super()._delete_extra()
        yield self.env['card.campaign'].search([('res_model', 'in', self.mapped('model'))])
