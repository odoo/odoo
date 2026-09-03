from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _compute_inbound_payment_method_line_ids(self):
        super()._compute_inbound_payment_method_line_ids()
        self._assign_outsanding_account_to_payment_method_lines("inbound", payment_method_codes=['manual'], chart_template="in")

    def _compute_outbound_payment_method_line_ids(self):
        super()._compute_outbound_payment_method_line_ids()
        self._assign_outsanding_account_to_payment_method_lines("outbound", payment_method_codes=['manual'], chart_template="in")
