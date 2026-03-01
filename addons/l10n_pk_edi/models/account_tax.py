from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_pk_edi_is_further_tax = fields.Boolean(string="Is FBR Further Tax")

    def _l10n_pk_edi_total_tax_group(self):
        self.ensure_one()
        if self.amount < 0:
            return 'withholding_tax_total'
        if self.l10n_pk_edi_is_further_tax:
            return 'further_tax_total'
        return 'sales_tax_total'
