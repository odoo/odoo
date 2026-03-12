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

    @api.depends('should_withhold_tax', 'country_code')
    def _compute_l10n_th_wth_condition(self):
        """
        Compute the default value only if relevant for the current payment's country.
        """
        for payment in self:
            if payment.should_withhold_tax and payment.country_code == 'TH':
                payment.l10n_th_wth_condition = payment.l10n_th_wth_condition or 'at_source'
            else:
                payment.l10n_th_wth_condition = False
