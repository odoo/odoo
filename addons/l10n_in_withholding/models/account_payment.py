from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_l10n_in_withholding_entries(self):
        self.ensure_one()
        return {
            'name': "TDS Entries",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.l10n_in_withhold_move_ids.ids)],
        }
