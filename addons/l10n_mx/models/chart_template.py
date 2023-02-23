# coding: utf-8
# Copyright 2016 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template('mx', 'account.journal')
    def _get_mx_account_journal(self):
        return {
            "cbmx": {
                'type': 'general',
                'name': _('Effectively Paid'),
                'code': 'CBMX',
                'default_account_id': "cuenta118_01",
                'show_on_dashboard': True,
            }
        }

    @template('mx', 'res.company')
    def _get_mx_res_company(self):
        company_data = super()._get_mx_res_company()
        company_data[self.env.company.id].update({
            'tax_cash_basis_journal_id': 'cbmx',
        })
        return company_data


    def _setup_utility_bank_accounts(self, template_code, company, template_data):
        super()._setup_utility_bank_accounts(template_code, company, template_data)
        company.account_journal_suspense_account_id.tag_ids = self.env.ref('l10n_mx.tag_credit_balance_account')
