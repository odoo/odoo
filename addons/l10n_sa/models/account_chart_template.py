# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """ If Saudi Arabia chart, we add 3 new journals Tax Adjustments, IFRS 16 and Zakat"""
        if self == self.env.ref('l10n_sa.sa_chart_template_standard'):
            if not journals_dict:
                journals_dict = []
            journals_dict.extend(
                [{'name': 'Tax Adjustments', 'company_id': company.id, 'code': 'TA', 'type': 'general',
                  'favorite': True, 'sequence': 1},
                 {'name': 'IFRS 16 Right of Use Asset', 'company_id': company.id, 'code': 'IFRS', 'type': 'general',
                  'favorite': True, 'sequence': 10},
                 {'name': 'Zakat', 'company_id': company.id, 'code': 'ZAKAT', 'type': 'general', 'favorite': True,
                  'sequence': 10}])
        return super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)

    def _load_template(self, company, code_digits=None, account_ref=None, taxes_ref=None):
        account_ref, taxes_ref = super(AccountChartTemplate, self)._load_template(company=company,
                                                                                  code_digits=code_digits,
                                                                                  account_ref=account_ref,
                                                                                  taxes_ref=taxes_ref)
        if self == self.env.ref('l10n_sa.sa_chart_template_standard'):
            ifrs_journal_id = self.env['account.journal'].search([('company_id', '=', company.id), ('code', '=', 'IFRS')], limit=1)
            if ifrs_journal_id:
                ifrs_account_ids = [self.env.ref('l10n_sa.sa_account_100101').id,
                                    self.env.ref('l10n_sa.sa_account_100102').id,
                                    self.env.ref('l10n_sa.sa_account_400070').id]
                ifrs_accounts = self.env['account.account'].browse([account_ref.get(id) for id in ifrs_account_ids])
                for account in ifrs_accounts:
                    account.allowed_journal_ids = [(4, ifrs_journal_id.id, 0)]
            zakat_journal_id = self.env['account.journal'].search([('company_id', '=', company.id), ('code', '=', 'ZAKAT')], limit=1)
            if zakat_journal_id:
                zakat_account_ids = [self.env.ref('l10n_sa.sa_account_201019').id,
                                    self.env.ref('l10n_sa.sa_account_400072').id]
                zakat_accounts = self.env['account.account'].browse([account_ref.get(id) for id in zakat_account_ids])
                for account in zakat_accounts:
                    account.allowed_journal_ids = [(4, zakat_journal_id.id, 0)]
        return account_ref, taxes_ref
