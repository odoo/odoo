# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    l10n_ar_adjustment_warning = fields.Boolean(compute="_compute_l10n_ar_adjustment_warning")

    @api.depends('l10n_latam_move_check_ids.amount', 'amount', 'l10n_account_withholding_net_amount', 'l10n_latam_new_check_ids.amount', 'payment_method_code')
    def _compute_l10n_ar_adjustment_warning(self):
        wizard_register = self
        for wizard in self:
            checks = wizard.l10n_latam_new_check_ids if wizard.filtered(lambda x: x._is_latam_check_payment(check_subtype='new_check')) else wizard.l10n_latam_move_check_ids
            checks_amount = sum(checks.mapped('amount'))
            if checks_amount and wizard.l10n_account_withholding_net_amount != checks_amount:
                wizard.l10n_ar_adjustment_warning = True
                wizard_register -= wizard
        wizard_register.l10n_ar_adjustment_warning = False
