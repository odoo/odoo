# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_it_get_tax_kind(self):
        if (self.l10n_it_vat_due_date == 'S'
            and (tax_group := self.tax_group_id)
            and (tax_group.get_external_id()[tax_group.id] == f'account.{self.company_id.id}_tax_group_split_payment')):
            return 'split_payment'
        else:
            return super()._l10n_it_get_tax_kind()
