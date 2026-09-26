from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _delete_collect_extra(self):
        yield self.env['snailmail.letter'].search([
            ('model', '=', 'account.move'),
            ('res_id', 'in', self.ids),
        ])
        yield from super()._delete_collect_extra()
