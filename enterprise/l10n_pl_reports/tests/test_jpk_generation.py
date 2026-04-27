# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged, freeze_time
from odoo import Command, fields, tools

import json


@freeze_time('2023-02-10 18:00:00')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestJpkExport(TestAccountReportsCommon):

    @classmethod
    @TestAccountReportsCommon.setup_country('pl')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'name': 'Polish Company',
            'city': 'Warsow',
            'zip': '01-857',
            'vat': 'PL1234567883',
            'email': 'test@mail.com',
            'l10n_pl_reports_tax_office_id': cls.env.ref('l10n_pl.pl_tax_office_0206'),
        })

        cls.partner_a.write({
            'country_id': cls.env.ref('base.pl').id,
            'vat': 'PL0123456789',
        })

        cls.partner_b.write({
            'country_id': cls.env.ref('base.be').id,
        })

        cls.product_b.write({
            'l10n_pl_vat_gtu': 'GTU_01',
        })
        tax_importation = cls.env.ref(f'account.{cls.company_data["company"].id}_vz_imp_tow')

        invoices = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-01-01',
                'date': '2023-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 4.0,
                        'price_unit': 750.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-01-01',
                'date': '2023-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_b.id,
                        'quantity': 5.0,
                        'price_unit': 1000.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                    })
                ],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-01-01',
                'date': '2023-01-01',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_a.id,
                        'quantity': 10.0,
                        'price_unit': 800.0,
                        'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                    })
                ],
            },
            # importation invoice
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-01-01',
                'date': '2023-01-01',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [
                    Command.create({
                        'product_id': cls.product_b.id,
                        'quantity': 10.0,
                        'price_unit': 800.0,
                        'tax_ids': [Command.set(tax_importation.ids)],
                    })
                ],
            },
        ])
        invoices.action_post()

        # We need the create_date for the bills, so we put it by hand in psql.
        cls.env.cr.execute(f""" UPDATE account_move SET create_date = '2023-02-10' where id IN {tuple(invoices.ids)}""")

    def test_jpk_monthly_generation(self):
        """ Test that the generation of the JPK_v7m corresponds to the expectations """
        report = self.env.ref('l10n_pl.tax_report')
        options = self._generate_options(report, fields.Date.from_string('2023-01-01'), fields.Date.from_string('2023-01-31'))
        wizard_action = self.env[report.custom_handler_model_name].print_tax_report_to_xml(options)
        wizard = self.env['l10n_pl_reports.periodic.vat.xml.export'].with_context(wizard_action.get('context')).browse(wizard_action.get('res_id'))

        wizard.l10n_pl_paid_before_deadline = True  # To test the options passing to the export (in P_67 here)

        report_action = wizard.print_xml()
        result_print = report.dispatch_report_action(json.loads(report_action.get('data', {}).get('options')), report_action.get('data', {}).get('file_generator'))

        stringified_xml = result_print['file_content']
        with tools.file_open('l10n_pl_reports/tests/expected_xmls/jpk_monthly.xml', 'rb') as expected_xml_file:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(stringified_xml),
                self.get_xml_tree_from_string(expected_xml_file.read()),
            )

    def test_jpk_quarterly_generation_first_month(self):
        """ Test that the generation of the JPK_v7k corresponds to the expectations
            In quarterly, only the third month should have the the amount of taxes aggregated
            So, no Declarakja node """
        report = self.env.ref('l10n_pl.tax_report')
        options = self._generate_options(report, fields.Date.from_string('2023-01-01'), fields.Date.from_string('2023-01-31'))
        wizard_action = self.env[report.custom_handler_model_name].print_tax_report_to_xml(options)
        wizard = self.env['l10n_pl_reports.periodic.vat.xml.export'].with_context(wizard_action.get('context')).browse(wizard_action.get('res_id'))

        self.company_data['company'].account_tax_periodicity = 'trimester'
        wizard.l10n_pl_paid_before_deadline = True  # To test the options passing to the export (in P_67 here)

        report_action = wizard.print_xml()
        result_print = report.dispatch_report_action(json.loads(report_action.get('data', {}).get('options')), report_action.get('data', {}).get('file_generator'))

        stringified_xml = result_print['file_content']
        with tools.file_open('l10n_pl_reports/tests/expected_xmls/jpk_quarterly_first_month.xml', 'rb') as expected_xml_file:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(stringified_xml),
                self.get_xml_tree_from_string(expected_xml_file.read()),
            )

    def test_jpk_quarterly_generation_last_month(self):
        """ Test that the generation of the JPK_v7k corresponds to the expectations
            In quarterly, the third month should have the the amount of taxes aggregated for the whole quarter
            Here, we have no invoices to declare for this period, but we have taxes """
        report = self.env.ref('l10n_pl.tax_report')
        options = self._generate_options(report, fields.Date.from_string('2023-03-01'), fields.Date.from_string('2023-03-31'))
        wizard_action = self.env[report.custom_handler_model_name].print_tax_report_to_xml(options)
        wizard = self.env['l10n_pl_reports.periodic.vat.xml.export'].with_context(wizard_action.get('context')).browse(wizard_action.get('res_id'))

        self.company_data['company'].account_tax_periodicity = 'trimester'
        wizard.l10n_pl_paid_before_deadline = True  # To test the options passing to the export (in P_67 here)

        report_action = wizard.print_xml()
        result_print = report.dispatch_report_action(json.loads(report_action.get('data', {}).get('options')), report_action.get('data', {}).get('file_generator'))

        stringified_xml = result_print['file_content']
        with tools.file_open('l10n_pl_reports/tests/expected_xmls/jpk_quarterly_last_month.xml', 'rb') as expected_xml_file:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(stringified_xml),
                self.get_xml_tree_from_string(expected_xml_file.read()),
            )
