from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_in_self_invoice = fields.Boolean(
        string='Self Invoice',
        help="This journal is for self-invoices."
             "Invoices will be created using a different sequence as you configured.",
    )

    def _compute_inbound_payment_method_line_ids(self):
        super()._compute_inbound_payment_method_line_ids()
        self._assign_outsanding_account_to_payment_method_lines("inbound", payment_method_codes=['manual'], chart_template="in")

    def _compute_outbound_payment_method_line_ids(self):
        super()._compute_outbound_payment_method_line_ids()
        self._assign_outsanding_account_to_payment_method_lines("outbound", payment_method_codes=['manual'], chart_template="in")
