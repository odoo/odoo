from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.ondelete(at_uninstall=False)
    def unlink_snailmail_letters(self):
        snailmail_letters = self.env['snailmail.letter'].search([
            ('model', '=', 'account.move'),
            ('res_id', 'in', self.ids),
        ])
        snailmail_letters.unlink()
