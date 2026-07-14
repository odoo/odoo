# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_open_l10n_ph_2307_wizard(self):
        self.ensure_one()
        if self.payment_type == 'outbound':
            wizard_action = self.env["ir.actions.act_window"]._for_xml_id("l10n_ph.view_l10n_ph_2307_wizard_act_window")
            wizard_action.update({
                'context': {'default_moves_to_export': self.reconciled_bill_ids.ids}
            })
            return wizard_action
        else:
            raise UserError(_('Only Outbound Payment is available.'))
