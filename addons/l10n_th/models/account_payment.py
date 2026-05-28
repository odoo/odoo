# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

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
        tracking=True,
    )

    # --------------------------------
    # Compute, inverse, search methods
    # --------------------------------

    @api.depends('withhold', 'country_code')
    def _compute_l10n_th_wth_condition(self):
        """
        Compute the default value only if relevant for the current payment's country.
        """
        for payment in self:
            if payment.withhold != 'payment' and payment.country_code == 'TH':
                payment.l10n_th_wth_condition = payment.l10n_th_wth_condition or 'at_source'
            else:
                payment.l10n_th_wth_condition = False

    # --------------
    # Action methods
    # --------------

    def action_l10n_th_print_50_tawi(self):
        """
        Triggered by the 'Print 50 Tawi' button.
        """
        return self.env.ref('l10n_th.action_report_50_tawi').report_action(self, config=False)
