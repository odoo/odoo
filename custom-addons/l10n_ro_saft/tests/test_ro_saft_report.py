# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged
from odoo import fields, Command
from odoo import tools


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestRoSaftReport(TestAccountReportsCommon):
    """ Test the generation of the SAF-T export for Romania.

        Depending on whether the account_intrastat module is installed, the
        export has a slighly different behaviour for non-service products.
        To handle this, we only use service products in the test.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref='ro'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].write({
            'name': 'Romanian Company',
            'city': 'Bucharest',
            'zip': '010001',
            'vat': 'RO1234567897',
            'company_registry': '1234567897',
            'phone': '+40 723545439',
            'country_id': cls.env.ref('base.ro').id,
            'account_storno': True,
            'l10n_ro_saft_tax_accounting_basis': 'A',
        })

        cls.env['res.partner'].create({
            'name': 'Mr Big CEO',
            'is_company': False,
            'phone': '+40 723545000',
            'parent_id': cls.company_data['company'].partner_id.id,
        })

        cls.partner_a.write({
            'name': 'Romanian Partner',
            'is_company': True,
            'city': 'Bucharest',
            'zip': '010001',
            'country_id': cls.env.ref('base.ro').id,
            'phone': '+40 234285561',
            'vat': 'RO18547290',
            'company_registry': '18547290',
        })

        cls.partner_b.write({
            'name': 'French Partner',
            'is_company': True,
            'city': 'Saint-Étienne',
            'zip': '42000',
            'country_id': cls.env.ref('base.fr').id,
            'phone': '+33 477284765',
            'vat': 'FR23334175221',
            'company_registry': 'FR23334175221',
        })

        bank_ro = cls.env['res.bank'].create({'name': 'Romanian Banking United'})
        cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'RO08429863697813',
            'allow_out_payment': True,
            'bank_id': bank_ro.id,
            'currency_id': cls.env.ref('base.RON').id,
        })

        cls.env.ref('base.EUR').active = True
        cls.env['res.currency.rate'].search([]).unlink()
        cls.env['res.currency.rate'].create({
            'name': '2023-01-01',
            'rate': 0.2,
            'currency_id': cls.env.ref('base.EUR').id,
        })

        cls.product_a.write({
            'default_code': 'PA',
            'type': 'service',
        })
        cls.product_b.write({
            'default_code': 'PB',
            'type': 'service',
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
        })

        cls.fiscal_pos_a.write({
            'account_ids': [
                Command.clear(),
                Command.create({
                    'account_src_id': cls.product_a.property_account_income_id.id,
                    'account_dest_id': cls.product_a.property_account_income_id.id,
                }),
                Command.create({
                    'account_src_id': cls.product_a.property_account_expense_id.id,
                    'account_dest_id': cls.product_a.property_account_expense_id.id,
                }),
            ],
        })

        # Create invoices

        cls.invoices = cls.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-01-01',
                'date': '2023-01-01',
                'partner_id': cls.partner_a.id,
                'currency_id': cls.env.ref('base.EUR').id,
                'invoice_line_ids': [Command.create({
                    'product_id': cls.product_a.id,
                    'quantity': 5.0,
                    'price_unit': 400.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                })],
            },
            {
                'move_type': 'out_refund',
                'invoice_date': '2023-01-11',
                'date': '2023-01-11',
                'partner_id': cls.partner_a.id,
                'invoice_line_ids': [Command.create({
                    'product_id': cls.product_a.id,
                    'quantity': 3.0,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_sale'].ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-01-21',
                'date': '2023-01-21',
                'partner_id': cls.partner_b.id,
                'invoice_line_ids': [Command.create({
                    'product_id': cls.product_b.id,
                    'quantity': 10.0,
                    'price_unit': 800.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-01-26',
                'date': '2023-01-26',
                'partner_id': cls.partner_b.id,
                'l10n_ro_is_self_invoice': True,  # This is a self-invoice
                'invoice_line_ids': [Command.create({
                    'product_id': cls.product_b.id,
                    'quantity': 2.0,
                    'price_unit': 600.0,
                    'tax_ids': [Command.set(cls.company_data['default_tax_purchase'].ids)],
                })]
            }
        ])
        cls.invoices.action_post()

        cls.statement = cls.env['account.bank.statement'].create({
            'name': 'test_statement',
            'line_ids': [
                Command.create({
                    'date': '2023-01-15',
                    'payment_ref': 'Payment Ref',
                    'partner_id': cls.partner_a.id,
                    'journal_id': cls.company_data['default_journal_bank'].id,
                    'foreign_currency_id': cls.env.ref('base.EUR').id,
                    'amount': 1250.0,
                    'amount_currency': 250.0,
                }),
            ],
        })

    def test_saft_report_monthly(self):
        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, fields.Date.from_string('2023-01-01'), fields.Date.from_string('2023-01-31'))
        stringified_xml = self.env[report.custom_handler_model_name].l10n_ro_export_saft_to_xml(options)['file_content']
        with tools.file_open('l10n_ro_saft/tests/expected_xmls/saft_report_monthly.xml', 'rb') as expected_xml_file:
            self.assertXmlTreeEqual(
                self.get_xml_tree_from_string(stringified_xml),
                self.get_xml_tree_from_string(expected_xml_file.read()),
            )
