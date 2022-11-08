# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _create_bank_journals(self, company, acc_template_ref):
        # we don't want to create new Cash and Bank accounts when
        # creating journals, so we have to pass the default_account_id to avoid it
        if company.account_fiscal_country_id.code == 'KZ':
            self.ensure_one()
            bank_journals = self.env['account.journal']
            journal_data = [
                {'acc_name': _('Cash'), 'account_type': 'cash', 'default_account_id': self.env['account.account'].search(
                    [('code', '=', '1010'), ('company_id', '=', company.id)], limit=1).id},
                {'acc_name': _('Bank'), 'account_type': 'bank', 'default_account_id': self.env['account.account'].search(
                    [('code', '=', '1030'), ('company_id', '=', company.id)], limit=1).id},
            ]
            for acc in journal_data:
                bank_journals += self.env['account.journal'].create({
                    'name': acc['acc_name'],
                    'type': acc['account_type'],
                    'default_account_id': acc['default_account_id'],
                    'company_id': company.id,
                    'currency_id': acc.get('currency_id', self.env['res.currency']).id,
                    'sequence': 10,
                })
            return bank_journals

        return super()._create_bank_journals(company, acc_template_ref)
