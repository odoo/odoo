# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_th_wth_condition = fields.Selection(
        string="Withholding Condition",
        selection=[
            ('at_source', 'Withhold at source'),
            ('forever', 'Paid by payer (Forever/Gross-up)'),
            ('one_time', 'Paid by payer (One-time)'),
        ],
        compute='_compute_l10n_th_wth_condition',
        store=True,
        readonly=False,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('can_edit_wizard', 'should_withhold_tax', 'country_code')
    def _compute_l10n_th_wth_condition(self):
        """
        Compute the default value only if relevant for the current payment's country.
        """
        for wizard in self:
            if wizard.can_edit_wizard and wizard.should_withhold_tax and wizard.country_code == 'TH':
                wizard.l10n_th_wth_condition = wizard.l10n_th_wth_condition or 'at_source'
            else:
                wizard.l10n_th_wth_condition = False

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _create_payment_vals_from_wizard(self, batch_result):
        """
        Update the computation of the payment vals in order to correctly set the outstanding account as well as the
        withholding line when needed.
        """
        # EXTEND 'account'
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)

        if not self.should_withhold_tax or self.country_code != 'TH':
            return payment_vals

        payment_vals['l10n_th_wth_condition'] = self.l10n_th_wth_condition
        return payment_vals
