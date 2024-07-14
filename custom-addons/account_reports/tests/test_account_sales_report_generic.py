# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=C0326

from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged
from odoo.tools.misc import NON_BREAKING_SPACE
from freezegun import freeze_time


@tagged('post_install', '-at_install')
class AccountSalesReportTest(AccountSalesReportCommon):

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        res = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        res['company'].update({
            'country_id': cls.env.ref('base.us').id,
            'vat': 'US123456789047',
            #  Country outside of EU to avoid local reports being chosen over this one (wanted behaviour)
        })
        res['company'].partner_id.update({
            'email': 'jsmith@mail.com',
            'phone': '+32475123456',
        })
        return res

    @freeze_time('2019-12-31')
    def test_ec_sales_report(self):
        l_tax = self.env['account.tax'].create({
            'name': 'goods',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'sale',
            'price_include': False,
            'include_base_amount': False,
        })
        t_tax = self.env['account.tax'].create({
            'name': 'triangular',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'purchase',
            'price_include': False,
            'include_base_amount': False,
        })
        s_tax = self.env['account.tax'].create({
            'name': 'services',
            'amount_type': 'percent',
            'amount': 0,
            'type_tax_use': 'sale',
            'price_include': False,
            'include_base_amount': False,
        })
        bad_tax_1 = self.env['account.tax'].create({
            'name': 'bad_1',
            'amount_type': 'fixed',
            'amount': 0,
            'type_tax_use': 'sale',
            'price_include': False,
            'include_base_amount': False,
        })
        bad_tax_2 = self.env['account.tax'].create({
            'name': 'bad_2',
            'amount_type': 'percent',
            'amount': 10,
            'type_tax_use': 'sale',
            'price_include': False,
            'include_base_amount': False,
        })
        self._create_invoices([
            (self.partner_a, l_tax[:1], 100),
            (self.partner_a, l_tax[:1], 200),
            (self.partner_a, t_tax[:1], 300),  # Should be ignored due to purchase tax
            (self.partner_b, t_tax[:1], 100),  # Should be ignored due to purchase tax
            (self.partner_a, s_tax[:1], 400),
            (self.partner_b, s_tax[:1], 500),
            (self.partner_b, bad_tax_1[:1], 700),  # Should be ignored due to fixed amount
            (self.partner_b, bad_tax_2[:1], 700),  # Should be ignored due to non-null amount
        ])
        report = self.env.ref('account_reports.generic_ec_sales_report')
        options = self._generate_options(report, '2019-12-01', '2019-12-31')

        self.assertLinesValues(
            report._get_lines(options),
            # pylint: disable=C0326
            #   Partner,                country code,             VAT Number,               Amount
            [   0,                      1,                        2,                        3],
            [
                (self.partner_a.name,   self.partner_a.vat[:2],   self.partner_a.vat[2:],   f'${NON_BREAKING_SPACE}700.00'),
                (self.partner_b.name,   self.partner_b.vat[:2],   self.partner_b.vat[2:],   f'${NON_BREAKING_SPACE}500.00'),
                ('Total',               '',                       '',                       f'${NON_BREAKING_SPACE}1,200.00'),
            ],
            options,
        )
