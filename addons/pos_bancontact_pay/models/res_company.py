from odoo import _, api, models
from odoo.exceptions import ValidationError

from odoo.addons.pos_bancontact_pay import const


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.constrains('currency_id')
    def _check_currency(self):
        """Prevent setting an unsupported company currency when Bancontact Pay relies on it."""
        unsupported_companies = self.filtered(lambda c: c.currency_id.name not in const.SUPPORTED_CURRENCIES)
        if not unsupported_companies:
            return

        # If unsupported, check if any Bancontact Pay payment methods are using a journal with no currency set
        if self.env['pos.payment.method'].search_count([
            ('company_id', 'in', unsupported_companies.ids),
            ('journal_id.currency_id', '=', False),
            ('payment_provider', '=', 'bancontact_pay'),
        ], limit=1):
            raise ValidationError(
                _(
                    "A Bancontact Pay payment method is linked to a journal that uses the company's default currency.\n"
                    "This currency is not supported.\n"
                    "Supported currencies: %(currencies)s.",
                    currencies=", ".join(const.SUPPORTED_CURRENCIES),
                ),
            )
