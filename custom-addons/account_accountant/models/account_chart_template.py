# -*- coding: utf-8 -*-
from odoo.addons.account.models.chart_template import template
from odoo import models

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _get_account_accountant_res_company(self, chart_template):
        # Called when installing the Accountant module
        company = self.env.company
        data = self._get_chart_template_data(chart_template)
        company_data = data['res.company'].get(company.id, {})

        # Pre-reload to ensure the necessary xmlids for the load exist in case they were deleted or not created yet.
        required_data = {k: v for k, v in data.items() if k in ['account.journal', 'account.account']}
        self._pre_reload_data(company, data['template_data'], required_data)

        return {
            company.id: {
                'deferred_journal_id': company.deferred_journal_id.id or company_data.get('deferred_journal_id'),
                'deferred_expense_account_id': company.deferred_expense_account_id.id or company_data.get('deferred_expense_account_id'),
                'deferred_revenue_account_id': company.deferred_revenue_account_id.id or company_data.get('deferred_revenue_account_id'),
            }
        }

    def _get_chart_template_data(self, chart_template):
        # OVERRIDE chart template to process the default values for deferred journal and accounts.

        data = super()._get_chart_template_data(chart_template)

        for _company_id, company_data in data['res.company'].items():
            company_data['deferred_journal_id'] = (
                company_data.get('deferred_journal_id')
                or next((xid for xid, d in data['account.journal'].items() if d['type'] == 'general'), None)
            )

            company_data['deferred_expense_account_id'] = (
                company_data.get('deferred_expense_account_id')
                or next((xid for xid, d in data['account.account'].items() if d['account_type'] == 'asset_current'), None)
            )

            company_data['deferred_revenue_account_id'] = (
                company_data.get('deferred_revenue_account_id')
                or next((xid for xid, d in data['account.account'].items() if d['account_type'] == 'liability_current'), None)
            )

        return data
