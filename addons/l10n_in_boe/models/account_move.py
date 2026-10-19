from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_l10n_in_open_boe_wizard(self):
        move = self.filtered(lambda move: move.l10n_in_shipping_bill_number)[:1]
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Create Bill Of Entry"),
            'res_model': 'l10n_in.boe.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_ids': self.ids,
                'default_l10n_in_shipping_bill_number': move.l10n_in_shipping_bill_number,
                'default_l10n_in_shipping_bill_date': move.l10n_in_shipping_bill_date,
                'default_l10n_in_shipping_port_code_id': move.l10n_in_shipping_port_code_id.id,
            },
        }
