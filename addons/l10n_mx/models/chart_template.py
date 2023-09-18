# coding: utf-8
# Copyright 2016 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        if company.chart_template_id == self.env.ref('l10n_mx.mx_coa'):
            company.write({
                'account_sale_tax_id': self.env.ref(f'l10n_mx.{company.id}_tax12'),
                'account_purchase_tax_id': self.env.ref(f'l10n_mx.{company.id}_tax14'),
            })
        return res

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        """Set the tax_cash_basis_journal_id on the company"""
        res = super(AccountChartTemplate, self).generate_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_mx.mx_coa'):
            return res
        journal_basis = self.env['account.journal'].search([
            ('company_id', '=', company.id),
            ('type', '=', 'general'),
            ('code', '=', 'CBMX')], limit=1)
        company.write({'tax_cash_basis_journal_id': journal_basis.id})
        return res

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """Create the tax_cash_basis_journal_id"""
        res = super(AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)
        if not self == self.env.ref('l10n_mx.mx_coa'):
            return res
        account = acc_template_ref.get(self.env.ref('l10n_mx.cuenta118_01').id)
        res.append({
            'type': 'general',
            'name': _('Effectively Paid'),
            'code': 'CBMX',
            'company_id': company.id,
            'default_account_id': account,
            'show_on_dashboard': True,
        })
        return res

    @api.model
    def _create_liquidity_journal_suspense_account(self, company, code_digits):
        if not self == self.env.ref('l10n_mx.mx_coa'):
            return super()._create_liquidity_journal_suspense_account(company, code_digits)
        return self.env['account.account'].create({
            'name': _("Bank Suspense Account"),
            'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'tag_ids': [(6, 0, self.env.ref('l10n_mx.account_tag_102_01').ids)],
            'company_id': company.id,
        })

    @api.model
    def _prepare_transfer_account_template(self, prefix=None):
        res = super()._prepare_transfer_account_template(prefix)
        if self == self.env.ref('l10n_mx.mx_coa'):
            res['tag_ids'] = [(6, 0, self.env.ref('l10n_mx.account_tag_102_01').ids)]
        return res

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        res = super()._load(sale_tax_rate, purchase_tax_rate, company)
        if self == self.env.ref('l10n_mx.mx_coa'):
            company.account_journal_payment_debit_account_id.tag_ids = [(6, 0, self.env.ref('l10n_mx.account_tag_102_01').ids)]
            company.account_journal_payment_credit_account_id.tag_ids = [(6, 0, self.env.ref('l10n_mx.account_tag_102_01').ids)]
        return res
