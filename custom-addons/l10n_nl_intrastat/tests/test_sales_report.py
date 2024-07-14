# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestNlEcSalesReport(AccountSalesReportCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass('nl')
        cls.report = cls.env.ref('l10n_nl_intrastat.dutch_icp_report')
        cls.partner_b.update({
            'country_id': cls.env.ref('base.de').id,
            'vat': "DE123456788",
        })

        cls.tax_goods = cls.env.ref(f'account.{cls.env.company.id}_btw_X0_producten')
        cls.tax_triangular = cls.env.ref(f'account.{cls.env.company.id}_btw_X0_ABC_levering')
        cls.tax_services = cls.env.ref(f'account.{cls.env.company.id}_btw_X0_diensten')

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'vat': 'NL123456782B90',
            'country_id': cls.env.ref('base.nl').id,
        })
        return res

    @freeze_time('2019-12-31')
    def test_ec_sales_report(self):
        invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b.id,
            'invoice_date': '2019-12-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line_1',
                    'price_unit': 1799.0,
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(self.tax_goods.ids)],
                }),
                 Command.create({
                    'name': 'line_2',
                    'price_unit': 200.0,
                    'product_id': False,
                    'quantity': 1.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(self.tax_services.ids)],
                }),
                 Command.create({
                    'name': 'line_3',
                    'price_unit': 300.0,
                    'product_id': False,
                    'quantity': 1.0,
                    'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.set(self.tax_triangular.ids)],
                })
            ]
        })

        invoice_1.action_post()

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
