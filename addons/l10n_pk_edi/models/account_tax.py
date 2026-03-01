from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_pk_edi_total_tax_group(self):
        self.ensure_one()
        if self.is_withholding_tax:
            return 'withholding_tax_total'
        if self.l10n_pk_is_further_tax:
            return 'further_tax_total'
        return 'sales_tax_total'
