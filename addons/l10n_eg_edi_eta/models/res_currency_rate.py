from odoo import _, api, models
from odoo.tools import float_compare


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    @api.onchange("company_rate")
    def _onchange_company_rate(self):
        # We send the ETA a rate that is 5 decimal accuracy, so to ensure consistency, Odoo should also operate with 5 decimal accuracy rate
        if (
            self.company_id.account_config_id.account_fiscal_country_id.code == "EG"
            and float_compare(
                self.inverse_company_rate,
                round(self.inverse_company_rate, 5),
                precision_digits=10,
            )
            != 0
        ):
            return {
                "warning": {
                    "title": _("Warning for %s", self.currency_id.name),
                    "message": _(
                        "Please make sure that the EGP per unit is within 5 decimal accuracy.\n"
                        "Higher decimal accuracy might lead to inconsistency with the ETA invoicing portal!"
                    ),
                }
            }
        return super()._onchange_company_rate()
