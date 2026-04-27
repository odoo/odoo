# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import Command, fields, tools
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests.common import test_xsd
from odoo.tests import tagged


class TestLtSaftReportCommon(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_country('lt')
    def setUpClass(cls):
        super().setUpClass()

        (cls.partner_a + cls.partner_b).write({
            'city': 'Garnich',
            'zip': 'L-8353',
            'country_id': cls.env.ref('base.lu').id,
            'phone': '+352 24 11 11 11',
            'property_supplier_payment_term_id': False,  # use default; weird payment terms mess with expected results
        })

        cls.company_data['company'].write({
            'city': 'Vilnius',
            'zip': 'LT-01000',
            'company_registry': '123456',
            'phone': '+370 11 11 11 11',
            'vat': 'LT949170611'
        })

        cls.env['res.partner'].create({
            'name': 'Mr Big CEO',
            'is_company': False,
            'phone': '+370 11 11 12 34',
            'parent_id': cls.company_data['company'].partner_id.id,
        })

        cls.product_a.default_code = 'PA'
        cls.product_b.default_code = 'PB'

        # Create invoices

        invoices = cls.env['account.move'].create([{
                'move_type': 'out_invoice',
                'invoice_date': '2021-01-01',
                'date': '2021-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 5.0,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2021-03-01',
                'date': '2021-03-01',
                'partner_id': cls.company_data['company'].partner_id.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 2.0,
                        'price_unit': 1500.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'out_refund',
                'invoice_date': '2021-03-01',
                'date': '2021-03-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 3.0,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2021-06-30',
                'date': '2021-06-30',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_b.id,
                        'quantity': 10.0,
                        'price_unit': 800.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    })
                ],
            },
        ])
        invoices.action_post()

    def _generate_xml(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2021-01-01'), fields.Date.from_string('2021-12-31'))
        return self.env[report.custom_handler_model_name].l10n_lt_export_saft_to_xml(options)['file_content']


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestLtSaftReport(TestLtSaftReportCommon):
    @freeze_time('2022-01-01')
    def test_saft_report_values(self):
        with tools.file_open("l10n_lt_saft/tests/xml/expected_test_saft_report.xml", "rb") as expected_xml:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(self._generate_xml()),
                self.get_xml_tree_from_string(expected_xml.read()),
            )

    def test_l10n_lt_saft_ensure_all_account_type_are_handled(self):
        report = self.env.ref('account_reports.general_ledger_report')
        account_selection = [selection[0] for selection in self.env["account.account"]._fields["account_type"].selection]
        for account_type in account_selection:
            self.env[report.custom_handler_model_name]._saft_get_account_type(account_type)


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestLtSaftReportXmlValidity(TestLtSaftReportCommon):
    @test_xsd(url='https://www.vmi.lt/evmi/documents/20142/725548/SAF-T_v2.01_20190306.xsd')
    def test_xml_validity(self):
        return self._generate_xml()
