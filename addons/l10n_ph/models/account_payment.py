from odoo import models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_view_l10n_ph_2307_wizard(self):
        self.check_singleton()
        if self.payment_type == "outbound":
            wizard_action = self.env[
                "ir.actions.act_window"
            ]._get_action_dict_by_xml_id("l10n_ph.view_l10n_ph_2307_wizard_act_window")
            wizard_action.update(
                {"context": {"default_moves_to_export": self.reconciled_bill_ids.ids}}
            )
            return wizard_action
        else:
            raise UserError(self.env._("Only Outbound Payment is available."))
