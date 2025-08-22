from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_payconiq import const


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains("currency_id")
    def _check_currency(self):
        """
        Ensure that journals linked to Payconiq payment methods use supported currencies.
        """
        for record in self:
            # Skip validation if the currency is supported by Payconiq
            journal_currency = record.currency_id or record.company_id.currency_id
            if journal_currency.name in const.SUPPORTED_CURRENCIES:
                continue

            # If unsupported, check if this journal is used by any Payconiq payment method
            is_used_with_payconiq = record.env["pos.payment.method"].search_count(
                [
                    ("journal_id", "=", record.id),
                    ("use_payment_terminal", "=", "payconiq"),
                ],
            )

            if is_used_with_payconiq:
                raise ValidationError(
                    self.env._(
                        "The journal '%(journal)s' is linked to a Payconiq payment method, which only "
                        "supports the following currencies: %(currencies)s.\n"
                        "Please assign a supported currency to the journal or update the payment method.",
                    )
                    % {
                        "journal": record.name,
                        "currencies": ", ".join(const.SUPPORTED_CURRENCIES),
                    },
                )
