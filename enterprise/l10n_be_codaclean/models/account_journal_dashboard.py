from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        for journal in self.browse(dashboard_data.keys()):
            dashboard_data[journal.id]["l10n_be_codaclean_is_connected"] = journal.company_id.l10n_be_codaclean_is_connected
