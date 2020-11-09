# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    @api.model
    def _prepare_payment_acquirer_account(self):
        # OVERRIDE
        vals = super()._prepare_payment_acquirer_account()
        if self.env.company.account_fiscal_country_id.code == 'DK':
            vals.setdefault('tag_ids', [])
            vals['tag_ids'].append((4, self.env.ref('l10n_dk.account_tag_liquidity').id))
            vals['name'] = "Bank i transfer"
        return vals
