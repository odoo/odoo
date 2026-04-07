from odoo import models


class AccountReturn(models.Model):
    _inherit = 'account.return'

    def _get_amount_to_pay_additional_tax_domain(self):
        return super()._get_amount_to_pay_additional_tax_domain() + [('l10n_it_pension_fund_type', '=', False)]
