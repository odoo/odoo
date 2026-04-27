from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _fill_transaction_vals_line_ofx(self, transaction, length_transactions, partner_bank):
        """
        Override of account_bank_statement_import_ofx as the FITID is not always unique in Brazil. For example, PIX
        transfer statement lines may have the same FITID as the PIX fee statement line for that transfer. Therefore,
        the field unique_import_id should not be filled with the FITID values, as they are not necessarily unique.
        """
        res = super()._fill_transaction_vals_line_ofx(transaction, length_transactions, partner_bank)
        if self.company_id.country_id.code == 'BR':
            res.pop('unique_import_id', None)
        return res
