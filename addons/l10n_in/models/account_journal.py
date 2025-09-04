from odoo import api, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _set_l10n_in_payment_accounts_for_type(self, pay_type):
        """Helper to set default outstanding accounts for inbound/outbound."""
        for journal in self.filtered(lambda j: j.type == "bank" and j.company_id.chart_template == "in"):
            self.env['account.chart.template']._set_l10n_in_default_outstanding_payment_accounts(
                journal.company_id,
                bank_journal=journal,
                pay_type=pay_type,
            )

    @api.depends('type', 'currency_id')
    def _compute_inbound_payment_method_line_ids(self):
        super()._compute_inbound_payment_method_line_ids()
        self._set_l10n_in_payment_accounts_for_type("inbound")

    @api.depends('type', 'currency_id')
    def _compute_outbound_payment_method_line_ids(self):
        super()._compute_outbound_payment_method_line_ids()
        self._set_l10n_in_payment_accounts_for_type("outbound")
