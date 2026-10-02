# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _should_distribute_base_delta_for_excluded_mode(self, company):
        # EXTENDS 'account'
        # In France, B2B invoices contractually expose the HT per line.
        # The journal entry HT (balance) must equal the printed invoice
        # subtotal (price_subtotal) on every product line. The rounding
        # delta of the base under `round_globally` is therefore absorbed
        # by the payment_term line (TTC) rather than redistributed on
        # product line balances.
        if company.account_fiscal_country_id.code == 'FR':
            return False
        return super()._should_distribute_base_delta_for_excluded_mode(company)
