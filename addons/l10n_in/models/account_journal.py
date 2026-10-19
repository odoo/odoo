from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_in_self_invoice = fields.Boolean(
        string='Self Invoice',
        help="This journal is for self-invoices."
             "Invoices will be created using a different sequence as you configured.",
    )

    @api.constrains('l10n_in_self_invoice', 'type', 'company_id')
    def _check_l10n_in_self_invoice(self):
        for journal in self.filtered('l10n_in_self_invoice'):
            if journal.country_code != 'IN' or journal.type != 'purchase':
                raise ValidationError(self.env._(
                    "Self Invoice can only be enabled on purchase journals of Indian companies (journal: %(journal)s).",
                    journal=journal.display_name,
                ))

    def _compute_inbound_payment_method_line_ids(self):
        super()._compute_inbound_payment_method_line_ids()
        self._assign_outstanding_account_to_payment_method_lines("inbound", payment_method_codes=['manual'], chart_template="in")

    def _compute_outbound_payment_method_line_ids(self):
        super()._compute_outbound_payment_method_line_ids()
        self._assign_outstanding_account_to_payment_method_lines("outbound", payment_method_codes=['manual'], chart_template="in")

    def _get_onboarding_action_data(self):
        """E-invoicing onboarding is only relevant for GST-registered (regular) taxpayers."""
        self.ensure_one()
        if self.country_code == 'IN' and self.company_id.l10n_in_gst_registration_type != 'regular':
            return None
        return super()._get_onboarding_action_data()
