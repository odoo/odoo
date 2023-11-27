# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, api, _
from odoo.tools import float_round


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

    def _sanitize_vals(self, vals):
        vals = super()._sanitize_vals(vals)

        # Continue only if fiscal country is Egypt
        company = self.env['res.company'].browse(vals.get('company_id')) or self.env.company
        if company.account_fiscal_country_id.code != 'EG':
            return vals

        last_rate = self.env['res.currency.rate']._get_last_rates_for_companies(company)
        inverse_company_rate = None

        # Calculate inverse_company_rate based on the available key
        if 'inverse_company_rate' in vals:
            inverse_company_rate = vals.pop('inverse_company_rate')
        elif 'company_rate' in vals:
            inverse_company_rate = 1 / vals.pop('company_rate')
        elif 'rate' in vals:
            inverse_company_rate = last_rate[company] / vals.pop('rate')

        if inverse_company_rate is not None:
            vals['rate'] = last_rate[company] / float_round(inverse_company_rate, precision_digits=5)

        return vals
