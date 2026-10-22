# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import TransactionCase, tagged

SE_TEMPLATES = ('se_K1', 'se_K2', 'se_K3', 'se_K2_HB', 'se_K2_NPO')
EXPECTED_SRU_TYPE = {'se_K1': 'ne', 'se_K2': 'ink2', 'se_K3': 'ink2', 'se_K2_HB': 'ink4', 'se_K2_NPO': 'ink3'}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSeChartTemplates(TransactionCase):
    """Every Swedish chart of accounts must install and be usable."""

    def _install(self, template_code):
        company = self.env['res.company'].create({
            'name': f'SE {template_code}',
            'country_id': self.env.ref('base.se').id,
        })
        self.env.user.company_ids |= company
        self.env['account.chart.template'].try_loading(template_code, company, install_demo=False)
        return company

    def test_templates_install(self):
        for template_code in SE_TEMPLATES:
            with self.subTest(template=template_code):
                company = self._install(template_code)
                self.assertEqual(company.chart_template, template_code)
                self.assertTrue(company.account_sale_tax_id, "default sale tax from the base template")
                self.assertTrue(company.account_purchase_tax_id, "default purchase tax from the base template")
                self.assertTrue(company.receivable_account_id)
                self.assertTrue(company.payable_account_id)
                self.assertTrue(company.income_account_id)
                self.assertTrue(company.expense_account_id)
                taxes = self.env['account.tax'].search([('company_id', '=', company.id)])
                self.assertTrue(taxes, "taxes from the base template must be loaded")
                fiscal_positions = self.env['account.fiscal.position'].search([('company_id', '=', company.id)])
                self.assertTrue(fiscal_positions, "fiscal positions from the base template must be loaded")

    def test_base_template_hidden(self):
        """'se' only holds shared data and must not be offered as a chart of accounts."""
        mapping = self.env['account.chart.template']._get_chart_template_mapping()
        self.assertNotIn('se', mapping)
        for template_code in SE_TEMPLATES:
            self.assertIn(template_code, mapping)

    def test_sru_type_derived_from_template(self):
        mapping_model = self.env['l10n_se.sru.mapping']
        for template_code, sru_type in EXPECTED_SRU_TYPE.items():
            with self.subTest(template=template_code):
                company = self._install(template_code)
                self.assertEqual(company.l10n_se_sru_type, sru_type, "defaults from the chart of accounts")
                self.assertEqual(mapping_model._get_sru_type(company), sru_type)
                self.assertEqual(mapping_model._get_sru_type(company, 'ink3'), 'ink3')

    def test_sru_type_chosen_on_company(self):
        """A form chosen in Settings (e.g. INK3 for a foundation) wins over the chart default."""
        company = self._install('se_K2')
        company.l10n_se_sru_type = 'ink3'
        self.assertEqual(self.env['l10n_se.sru.mapping']._get_sru_type(company), 'ink3')
        settings = self.env['res.config.settings'].with_company(company).create({})
        self.assertEqual(settings.l10n_se_sru_type, 'ink3')
        settings.action_l10n_se_load_sru_mapping()
        mappings = self.env['l10n_se.sru.mapping'].search([('company_id', '=', company.id)])
        self.assertTrue(mappings)
        self.assertEqual(set(mappings.mapped('sru_type')), {'ink3'})

    def test_triangular_trade(self):
        """The intermediary reports the purchase in box 37 and the sale in box 38, never Swedish VAT."""
        company = self._install('se_K2')
        ChartTemplate = self.env['account.chart.template'].with_company(company)
        sale = ChartTemplate.ref('triangular_tax_0_goods')
        purchase = ChartTemplate.ref('triangular_purchase_tax_0_goods')
        self.assertEqual(sale.amount, 0)
        self.assertEqual(purchase.amount, 0)
        self.assertEqual(sale.type_tax_use, 'sale')
        self.assertEqual(purchase.type_tax_use, 'purchase')
        sale_tags = sale.invoice_repartition_line_ids.tag_ids.mapped('name')
        purchase_tags = purchase.invoice_repartition_line_ids.tag_ids.mapped('name')
        self.assertTrue(any('38' in tag for tag in sale_tags) and not any('37' in tag for tag in sale_tags))
        self.assertTrue(any('37' in tag for tag in purchase_tags) and not any('38' in tag for tag in purchase_tags))
        self.assertIn('Trepartshandel', sale.invoice_legal_notes or '')
        for removed in ('triangular_tax_25_goods', 'triangular_tax_12_goods', 'triangular_tax_6_goods'):
            self.assertFalse(ChartTemplate.ref(removed, raise_if_not_found=False))
