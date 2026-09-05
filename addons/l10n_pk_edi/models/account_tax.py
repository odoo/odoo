from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_pk_edi_total_tax_group(self):
        self.ensure_one()
        if self.amount < 0:
            return 'withholding_tax_total'
        # l10n_pk flags further tax on the chart template (GST FT 4%); it is the field the
        # e-invoicing and e-receipt payloads are meant to consume.
        if self.l10n_pk_is_further_tax:
            return 'further_tax_total'
        return 'sales_tax_total'
