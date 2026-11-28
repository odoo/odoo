from odoo import api, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.depends('withholding_line_ids.tax_id.l10n_ge_is_gross')
    def _compute_withholding_net_amount(self):
        super()._compute_withholding_net_amount()
        # The company bears the gross withholding: the vendor receives it on top of the net.
        for wizard in self.filtered(lambda w: w.can_edit_wizard and w.withhold != 'withhold'):
            wizard.withholding_net_amount += sum(wizard.withholding_line_ids.filtered('tax_id.l10n_ge_is_gross').mapped('amount'))

    def _create_payments(self):
        # Paying without withholding lines would leave the gross withholding due on the bills, with no way to withhold it.
        for wizard in self.filtered(lambda w: w.withhold == 'payment' or not w.display_withholding):
            if wizard.line_ids.move_id._l10n_ge_filter_gross_withholding_due():
                # l10n_account_withholding_tax._compute_display_withholding hides the withholding when bills and credit notes are paid together.
                if len(set(wizard.line_ids.mapped('is_refund'))) > 1:
                    raise UserError(self.env._("Register the payments of the bills and the credit notes separately."))
                if wizard.can_group_payments and not wizard.group_payment:
                    raise UserError(self.env._("Tick Group Payments to withhold the gross withholding taxes of these bills."))
                raise UserError(self.env._("For bills and credit notes with a gross withholding tax, only 'Withhold and Pay' is allowed."))
        return super()._create_payments()
