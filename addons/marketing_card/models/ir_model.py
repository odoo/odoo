from odoo import models


class IrModel(models.Model):
    _inherit = 'ir.model'

    def _delete_collect_extra(self):
        yield self.env['card.campaign'].search([
            ('res_model', 'in', self.mapped('model'))
        ])
        yield from super()._delete_collect_extra()
