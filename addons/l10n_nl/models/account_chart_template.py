# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load_all_templates(self):
        # OVERRIDE
        # Add tag to 999999 account
        res = super()._load_all_templates()
        company = self.env.company
        if company.account_fiscal_country_id.code == 'NL':
            account = self.env['account.account'].search([('code', '=', '999999'), ('company_id', '=', company.id)])
            if account:
                account.tag_ids = [(4, self.env.ref('l10n_nl.account_tag_12').id)]
        return res

    @api.model
    def _prepare_payment_acquirer_account(self):
        # OVERRIDE
        vals = super()._prepare_payment_acquirer_account()
        if self.env.company.account_fiscal_country_id.code == 'NL':
            vals.setdefault('tag_ids', [])
            vals['tag_ids'].append((4, self.env.ref('l10n_nl.account_tag_25').id))
        return vals
