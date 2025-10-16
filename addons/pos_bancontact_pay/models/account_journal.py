from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_bancontact_pay import const


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.constrains("currency_id")
    def _check_currency(self):
        """Prevent using an unsupported currency with Bancontact Pay payment methods."""
        for record in self:
            # Currency already supported by Bancontact
            journal_currency = record.currency_id or record.company_id.currency_id
            if journal_currency.name in const.SUPPORTED_CURRENCIES:
                continue

            # If unsupported, check if this journal is used by any Bancontact payment method
            if any(pm.payment_provider == "bancontact_pay" for pm in record.pos_payment_method_ids):
                raise ValidationError(
                    _(
                        "The journal '%(journal)s' is used by a Bancontact Pay payment method.\n"
                        "This payment method does not support the journal's currency.\n"
                        "Supported currencies: %(currencies)s.",
                        journal=record.name,
                        currencies=", ".join(const.SUPPORTED_CURRENCIES),
                    ),
                )
