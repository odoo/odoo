from odoo import models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _compute_inbound_payment_method_line_ids(self):
        super()._compute_inbound_payment_method_line_ids()
        self._update_payment_method_lines_account_for_bank_journals('inbound', 'ma')

    def _compute_outbound_payment_method_line_ids(self):
        super()._compute_outbound_payment_method_line_ids()
        self._update_payment_method_lines_account_for_bank_journals('outbound', 'ma')
