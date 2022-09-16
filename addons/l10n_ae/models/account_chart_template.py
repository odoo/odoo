# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """ If UAE chart, we add 2 new journals TA and IFRS"""
        if self == self.env.ref('l10n_ae.uae_chart_template_standard'):
            if not journals_dict:
                journals_dict = []
            journals_dict.extend(
                [{"name": "Tax Adjustments", "company_id": company.id, "code": "TA", "type": "general", "sequence": 1,
                  "favorite": True},
                 {"name": "IFRS 16", "company_id": company.id, "code": "IFRS", "type": "general", "favorite": True,
                  "sequence": 10}])
        return super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)

    def _load_template(self, company, code_digits=None, account_ref=None, taxes_ref=None):
        account_ref, taxes_ref = super(AccountChartTemplate, self)._load_template(company=company,
                                                                                  code_digits=code_digits,
                                                                                  account_ref=account_ref,
                                                                                  taxes_ref=taxes_ref)
        if self == self.env.ref('l10n_ae.uae_chart_template_standard'):
            ifrs_journal = self.env['account.journal'].search(
                [('company_id', '=', company.id), ('code', '=', 'IFRS')]).id
            if ifrs_journal:
                ifrs_account_ids = [self.env.ref('l10n_ae.uae_account_100101').id,
                                    self.env.ref('l10n_ae.uae_account_100102').id,
                                    self.env.ref('l10n_ae.uae_account_400070').id]
                ifrs_accounts = self.env['account.account'].browse([account_ref.get(id) for id in ifrs_account_ids])
                for account in ifrs_accounts:
                    account.allowed_journal_ids = [(4, ifrs_journal, 0)]
            self.env.ref('l10n_ae.ae_tax_group_5').write(
                {'property_tax_payable_account_id': account_ref.get(self.env.ref('l10n_ae.uae_account_202003').id),
                 'property_tax_receivable_account_id': account_ref.get(self.env.ref('l10n_ae.uae_account_100103').id)})
        return account_ref, taxes_ref

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        if not self == self.env.ref('l10n_ae.uae_chart_template_standard'):
            return super()._create_cash_discount_loss_account(company, code_digits)
        cash_discount_loss_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '400071')], limit=1)
        if not cash_discount_loss_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Loss"),
                'code': 400071,
                'account_type': 'expense',
                'company_id': company.id,
            })
        return cash_discount_loss_account

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        if not self == self.env.ref('l10n_ae.uae_chart_template_standard'):
            return super()._create_cash_discount_gain_account(company, code_digits)
        cash_discount_gain_account = self.env['account.account'].search([('company_id', '=', company.id), ('code', 'like', '500014')], limit=1)
        if not cash_discount_gain_account:
            return self.env['account.account'].create({
                'name': _("Cash Discount Gain"),
                'code': 500014,
                'account_type': 'income_other',
                'company_id': company.id,
            })
        return cash_discount_gain_account
