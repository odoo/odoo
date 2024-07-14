from odoo import models


class AccountJournal(models.Model):

    _inherit = 'account.journal'

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()
        for journal in self.filtered(lambda journal: journal.type == 'bank'):
            dashboard_data[journal.id]['has_bank_account_on_bank_journal'] = bool(journal.bank_account_id)
            dashboard_data[journal.id]['country_code'] = journal.company_id.country_code
        return dashboard_data
