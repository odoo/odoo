from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_payconiq import const


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.constrains("currency_id")
    def _check_currency(self):
        """
        Ensure that Payconiq payment methods use a supported currency.
        """
        for record in self:
            if record.currency_id.name in const.SUPPORTED_CURRENCIES:
                return

            payment_method_ids = record.env["pos.payment.method"].search(
                [
                    ("journal_id.currency_id", "=", False),
                    ("use_payment_terminal", "=", "payconiq"),
                ],
            )
            if payment_method_ids:
                raise ValidationError(
                    record.env._(
                        "This company has a journal using the default currency of the company, "
                        "and it's linked to a Payconiq payment method, which only supports the following currencies: %s.\n"
                        "Please either set a supported currency on the journal or remove Payconiq from the associated payment method.",
                    )
                    % ", ".join(const.SUPPORTED_CURRENCIES),
                )
