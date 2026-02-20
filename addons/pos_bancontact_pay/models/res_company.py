from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_bancontact_pay import const


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.constrains('currency_id')
    def _check_currency(self):
        """Prevent setting an unsupported company currency when Bancontact Pay relies on it."""
        for record in self:
            # Currency already supported by Bancontact Pay
            if record.currency_id.name in const.SUPPORTED_CURRENCIES:
                return

            # If unsupported, check if any Bancontact Pay payment methods are using a journal with no currency set
            payment_method_ids = self.env['pos.payment.method'].search_count(
                [
                    ('company_id', '=', record.id),
                    ('journal_id.currency_id', '=', False),
                    ('payment_provider', '=', 'bancontact_pay'),
                ], limit=1,
            )
            if payment_method_ids:
                raise ValidationError(
                    _(
                        "A Bancontact Pay payment method is linked to a journal that uses the company's default currency.\n"
                        "This currency is not supported.\n"
                        "Supported currencies: %(currencies)s.",
                        currencies=", ".join(const.SUPPORTED_CURRENCIES),
                    ),
                )
