# coding: utf-8
# Copyright 2016 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_journals(self, loaded_data):
        # OVERRIDE
        res = super()._prepare_journals(loaded_data)
        company = self.env.company
        if company.account_fiscal_country_id.code == 'MX':
            accounts_mapping = loaded_data['account.account.template']['records']
            res['general'].append({
                'type': 'general',
                'name': _('Effectively Paid'),
                'code': 'CBMX',
                'company_id': company.id,
                'default_account_id': accounts_mapping[self.env.ref('l10n_mx.cuenta118_01')].id,
                'show_on_dashboard': True,
            })
        return res

    def _update_company_after_loading(self, loaded_data):
        # OVERRIDE
        res = super()._update_company_after_loading(loaded_data)
        company = self.env.company
        if company.account_fiscal_country_id.code == 'MX':
            company.tax_cash_basis_journal_id = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('type', '=', 'general'),
                ('code', '=', 'CBMX'),
            ], limit=1)
        return res

    @api.model
    def _prepare_payment_acquirer_account(self):
        # OVERRIDE
        vals = super()._prepare_payment_acquirer_account()
        if self.env.company.account_fiscal_country_id.code == 'MX':
            vals.setdefault('tag_ids', [])
            vals['tag_ids'].append((4, self.env.ref('l10n_mx.account_tag_102_01').id))
        return vals
