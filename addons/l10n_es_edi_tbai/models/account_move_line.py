from odoo import models
from odoo.addons import account


class AccountMoveLine(account.AccountMoveLine):

    def _l10n_es_tbai_is_ignored(self):
        self.ensure_one()

        return 'ignore' in self.tax_ids.mapped('l10n_es_type')
