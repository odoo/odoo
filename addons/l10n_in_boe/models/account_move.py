from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = "account.move"

    # BOE related field
    l10n_in_boe_feature_enabled = fields.Boolean(related='company_id.l10n_in_boe_feature')

    def action_l10n_in_open_boe_wizard(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _("Create Bill Of Entry"),
            'res_model': 'l10n_in.boe.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_l10n_in_shipping_bill_number': self.l10n_in_shipping_bill_number,
                'default_l10n_in_shipping_bill_date': self.l10n_in_shipping_bill_date,
                'default_l10n_in_shipping_port_code_id': self.l10n_in_shipping_port_code_id.id,
            },
        }
