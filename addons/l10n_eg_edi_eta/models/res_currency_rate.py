# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, api, _


class ResCurrencyRate(models.Model):
    _inherit = 'res.currency.rate'

    @api.onchange('company_rate')
    def _onchange_rate_warning(self):
        # We send the ETA a rate that is 5 decimal accuracy, so to ensure consistency, Odoo should also operate with 5 decimal accuracy rate
        if self.company_id.account_fiscal_country_id.code == 'EG' and self.inverse_company_rate != round(self.inverse_company_rate, 5):
            return {
                'warning': {
                    'title': _("Warning for %s", self.currency_id.name),
                    'message': _(
                        "Please make sure that the EGP per unit is within 5 decimal accuracy.\n"
                        "Higher decimal accuracy might lead to inconsistency with the ETA invoicing portal!"
                    )
                }
            }
        return super()._onchange_rate_warning()
