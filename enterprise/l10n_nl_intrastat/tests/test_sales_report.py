# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNlEcSalesReport(AccountSalesReportCommon):

    @classmethod
    @AccountSalesReportCommon.setup_country('nl')
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref('l10n_nl_intrastat.dutch_icp_report')
        cls.company.vat = 'NL123456782B90'
        cls.partner_b.update({
            'country_id': cls.env.ref('base.de').id,
            'vat': "DE123456788",
        })

        cls.goods_tax = cls.env.ref(f'account.{cls.env.company.id}_btw_X0_producten')
        cls.goods_tag = cls.env.ref('l10n_nl.tax_report_rub_3bg_tag')
        cls.services_tax = cls.env.ref(f'account.{cls.env.company.id}_btw_X0_diensten')
        cls.services_tag = cls.env.ref('l10n_nl.tax_report_rub_3bs_tag')
        cls.triangular_tax = cls.env.ref(f'account.{cls.env.company.id}_btw_X0_ABC_levering')
        cls.triangular_tag = cls.env.ref('l10n_nl.tax_report_rub_3bt_tag')
    
    def _create_invoice(self, invoice_date):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b.id,
            'invoice_date': invoice_date,
            'invoice_line_ids': [
                Command.create({
                    'name': 'Goods Line',
                    'price_unit': 1799.0,
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(self.goods_tax.ids)],
                }),
                Command.create({
                    'name': 'Services Line',
                    'price_unit': 200.0,
                    'product_id': False,
                    'quantity': 1.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(self.services_tax.ids)],
                }),
                Command.create({
                    'name': 'Triangular Line',
                    'price_unit': 300.0,
                    'product_id': False,
                    'quantity': 1.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(self.triangular_tax.ids)],
                }),
            ]
        })
        invoice.action_post()
        return invoice

    @freeze_time('2019-12-31')
    def test_ec_sales_report(self):
        self._create_invoice('2019-12-01')

        options = self.report.get_options({'date': {'mode': 'range', 'filter': 'this_month'}})
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Line Name                                     Amount Product                       Amount Services                           Amount Triangular                              Amount_total
            [   0,                                                         4,                                    5,                                          6,                                        7],
            [
                (self.partner_b.name,       f'1,799.00{NON_BREAKING_SPACE}€',       f'200.00{NON_BREAKING_SPACE}€',             f'300.00{NON_BREAKING_SPACE}€',         f'2,299.00{NON_BREAKING_SPACE}€'),
                ('Total',                   f'1,799.00{NON_BREAKING_SPACE}€',       f'200.00{NON_BREAKING_SPACE}€',             f'300.00{NON_BREAKING_SPACE}€',         f'2,299.00{NON_BREAKING_SPACE}€'),
            ],
            options,
        )

    def test_l10n_nl_ec_sales_report_use_taxes_instead_of_tags(self):
        """ Ensure that if the tax report line is missing, making impossible to retrieve associated tags),
         taxes are used as fallback to retrieve goods, services and triangular sales """
        self._create_invoice('2025-01-01')
        self.goods_tag.unlink()
        options = self._generate_options(self.report, '2025-01-01', '2025-12-31')
        expected_sales_report_taxes = {
            'goods': [self.goods_tax.id],
            'services': [self.services_tax.id],
            'triangular': [self.triangular_tax.id],
            'use_taxes_instead_of_tags': True,
        }
        self.assertEqual(options['sales_report_taxes'], expected_sales_report_taxes)
        self.assertLinesValues(
            self.report._get_lines(options),
            #   Line Name                   [ Amount Product ] [ Amount Services ] [ Amount Triangular ] [ Amount_total ]
            [0,                                     4,                  5,                 6,                    7],
            [
                (self.partner_b.name,              1799,                200,             300,                   2299),
                ('Total',                          1799,                200,             300,                   2299),
            ],
            options,
        )