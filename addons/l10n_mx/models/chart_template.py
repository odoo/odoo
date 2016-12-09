# coding: utf-8
# Copyright 2016 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.multi
    def _load_template(
            self, company, code_digits=None, transfer_account_id=None,
            account_ref=None, taxes_ref=None):
        """
        Set the 'use_cash_basis' and 'cash_basis_account' fields on account.account. This hack is needed due to the fact
        that the tax template does not have the fields 'use_cash_basis' and 'cash_basis_account'.

        This hunk should be removed in master, as the account_tax_cash_basis module has been merged already in account
        module
        """
        self.ensure_one()
        accounts, taxes = super(AccountChartTemplate, self)._load_template(
            company, code_digits=code_digits,
            transfer_account_id=transfer_account_id, account_ref=account_ref,
            taxes_ref=taxes_ref)
        if not self == self.env.ref('l10n_mx.mx_coa'):
            return accounts, taxes
        account_tax_obj = self.env['account.tax']
        account_obj = self.env['account.account']
        taxes_acc = {
            'ITAX_010-IN': account_obj.search([('code', '=', '208.01.01')]),
            'ITAX_160-IN': account_obj.search([('code', '=', '208.01.01')]),
            'ITAXR_04-OUT': account_obj.search([('code', '=', '216.13.01')]),
            'ITAXR_10-OUT': account_obj.search([('code', '=', '216.13.01')]),
            'ITAX_1067-OUT': account_obj.search([('code', '=', '216.13.01')]),
            'ITAX_167-OUT': account_obj.search([('code', '=', '216.13.01')]),
            'ITAX_010-OUT': account_obj.search([('code', '=', '208.01.01')]),
            'ITAX_160-OUT': account_obj.search([('code', '=', '208.01.01')])}

        for tax in self.tax_template_ids:
            if tax.description not in taxes_acc:
                continue
            account_tax_obj.browse(taxes.get(tax.id)).write({
                'use_cash_basis': True,
                'cash_basis_account': taxes_acc.get(tax.description).id,
            })
        return accounts, taxes

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        """Set the tax_cash_basis_journal_id on the company"""
        res = super(AccountChartTemplate, self).generate_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_mx.mx_coa'):
            return res
        journal_basis = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('code', '=', 'CBMX')], limit=1)
        company.write({'tax_cash_basis_journal_id': journal_basis.id})
        return res

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """Create the tax_cash_basis_journal_id"""
        res = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_mx.mx_coa'):
            return res
        res.append({
            'type': 'general',
            'name': _('Effectively Paid'),
            'code': 'CBMX',
            'company_id': company.id,
            'default_credit_account_id': acc_template_ref.get(
                self.income_currency_exchange_account_id.id),
            'default_debit_account_id': acc_template_ref.get(
                self.expense_currency_exchange_account_id.id),
            'show_on_dashboard': True,
        })
        return res
