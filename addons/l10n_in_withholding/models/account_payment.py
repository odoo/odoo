from odoo import models, fields


class AccountPayment(models.Model):
    _inherit = "account.payment"

    l10n_in_total_withholding_amount = fields.Monetary(related='move_id.l10n_in_total_withholding_amount')
    l10n_in_withhold_move_ids = fields.One2many(related='move_id.l10n_in_withhold_move_ids')

    def action_l10n_in_withholding_entries(self):
        self.ensure_one()
        return {
            'name': "TDS Entries",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.l10n_in_withhold_move_ids.ids)],
        }
