# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestLocalizationCompanyFixtures(TransactionCase):

    def test_localization_company_fixtures(self):
        class FixtureCommon(AccountTestInvoicingCommon):
            env = self.env

        ChartTemplate = self.env['account.chart.template']
        installed_modules = set(self.env['ir.module.module']._installed())
        for code, template in ChartTemplate._get_chart_template_mapping().items():
            if not template['module'].startswith('l10n_') or template['module'] not in installed_modules:
                continue
            country = self.env['res.country'].browse(template['country_id'])
            xmlid = (
                f'base.test_company_{country.code.lower()}'
                if country and code == ChartTemplate._guess_chart_template(country)
                else f'base.test_company_chart_{code}'
            )
            FixtureCommon.chart_template = code
            with self.subTest(chart=code), patch.object(
                FixtureCommon, '_use_chart_template', side_effect=AssertionError('Chart must already be loaded'),
            ):
                first = FixtureCommon._create_company(name=f'Fixture {code} First')
                second = FixtureCommon._create_company(name=f'Fixture {code} Second')
                self.assertEqual(first, self.env.ref(xmlid))
                self.assertEqual(second, self.env.ref(f'{xmlid}_2'))
                self.assertNotEqual(first, second)
                for company in first | second:
                    self.assertEqual(company.chart_template, code)
                    self.assertTrue(company.account_fiscal_country_id)
                    self.assertTrue(company.currency_id)
                    if country:
                        self.assertEqual(company.country_id, country)
                    self.assertTrue(self.env['account.account'].search_count([
                        ('company_ids', 'in', company.ids),
                    ]))

    def test_forced_company_creation(self):
        class FixtureCommon(AccountTestInvoicingCommon):
            env = self.env
            _force_new_company = True

        with patch.object(FixtureCommon, '_use_chart_template') as load_chart:
            company = FixtureCommon._create_company()
        self.assertNotIn(company, self.env.ref('base.test_company') | self.env.ref('base.test_company_with_branch'))
        load_chart.assert_called_once_with(company, False)

    def test_localization_company_without_chart_loading(self):
        first = self.setup_localization_company('in', {'name': 'Fixture IN First'})
        second = self.setup_localization_company('in', {'name': 'Fixture IN Second'})
        third = self.setup_localization_company('in', {'name': 'Fixture IN Third'})
        self.assertEqual(first, self.env.ref('base.test_company_in'))
        self.assertEqual(second, self.env.ref('base.test_company_in_2'))
        self.assertNotIn(third, first | second)
        self.assertFalse(third.chart_template)
        fourth = self.setup_localization_company('in')
        self.assertNotIn(fourth, first | second | third)
        self.assertFalse(fourth.chart_template)

    def test_implicit_localization_country(self):
        if self.env.ref('base.test_company_in').chart_template != 'in':
            self.skipTest('Indian accounting localization is not installed')

        class FixtureCommon(AccountTestInvoicingCommon):
            env = self.env
            country_code = False
            chart_template = False

        FixtureCommon.__module__ = 'odoo.addons.l10n_in.tests.common'
        with patch.object(FixtureCommon, '_use_chart_template', side_effect=AssertionError('Chart must already be loaded')):
            company = FixtureCommon.setup_independent_company(name='Implicit Indian Company')
        self.assertEqual(company, self.env.ref('base.test_company_in'))
        self.assertEqual(FixtureCommon.country_code, 'IN')

    def test_regional_chart_with_country(self):
        fixture = self.env.ref('base.test_company_chart_syscebnl')
        if fixture.chart_template != 'syscebnl':
            self.skipTest('OHADA accounting localization is not installed')

        class FixtureCommon(AccountTestInvoicingCommon):
            env = self.env
            country_code = 'BJ'
            chart_template = 'syscebnl'

        with patch.object(FixtureCommon, '_use_chart_template', side_effect=AssertionError('Chart must already be loaded')):
            company = FixtureCommon.setup_independent_company(name='Regional Chart Company')
        self.assertEqual(company, fixture)
        self.assertEqual(company.account_fiscal_country_id, self.env.ref('base.bj'))
