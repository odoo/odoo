# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nVeTemplateRegister(TransactionCase):

    def test_ve_template_data(self):
        tpl = self.env['account.chart.template']
        funcs = tpl._template_register['ve']['template_data']
        data = funcs[0](tpl)
        self.assertEqual(data.get('code_digits'), '7')
        self.assertEqual(data.get('property_account_receivable_id'), 'account_account_1106001')
        self.assertEqual(data.get('property_account_income_categ_id'), 'account_account_4101001')

    def test_ve_res_company_template(self):
        tpl = self.env['account.chart.template']
        funcs = tpl._template_register['ve']['res.company']
        data = funcs[0](tpl)
        row = data[self.env.company.id]
        self.assertEqual(row['account_fiscal_country_id'], 'base.ve')
        self.assertEqual(row['currency_id'], 'base.VED')
        self.assertEqual(row['account_sale_tax_id'], 'tax1sale')
        self.assertEqual(row['account_purchase_tax_id'], 'tax1purchase')


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nVeChart(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='ve'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_company_currency_ved(self):
        company = self.company_data['company']
        self.assertEqual(company.currency_id, self.env.ref('base.VED'))
        self.assertEqual(company.country_id.currency_id, self.env.ref('base.VED'))

    def test_default_taxes(self):
        company = self.company_data['company']
        self.assertEqual(company.account_sale_tax_id.amount, 16.0)
        self.assertEqual(company.account_purchase_tax_id.amount, 16.0)
        self.assertEqual(company.account_sale_tax_id.tax_group_id.name, 'IVA 16%')

    def test_main_accounts(self):
        company = self.company_data['company']
        receivable = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('code', '=', '1106001'),
        ])
        payable = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('code', '=', '2101002'),
        ])
        vat_payable = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('code', '=', '2102004'),
        ])
        self.assertEqual(len(receivable), 1)
        self.assertEqual(receivable.account_type, 'asset_receivable')
        self.assertEqual(len(payable), 1)
        self.assertEqual(payable.account_type, 'liability_payable')
        self.assertEqual(len(vat_payable), 1)
        self.assertEqual(company.account_sale_tax_id.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == 'tax'
        ).account_id, vat_payable)

    def test_vat_rates(self):
        company = self.company_data['company']
        sale_taxes = self.env['account.tax'].search([
            ('company_id', '=', company.id),
            ('type_tax_use', '=', 'sale'),
        ])
        self.assertEqual(sorted(sale_taxes.mapped('amount')), [0.0, 8.0, 16.0, 31.0])
