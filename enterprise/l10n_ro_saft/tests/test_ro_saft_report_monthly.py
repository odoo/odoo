# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account_saft.tests.common import TestSaftReport
from odoo.tests import tagged
from odoo import Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestRoSaftReport(TestSaftReport):
    """ Test the generation of the SAF-T export for Romania.

        Depending on whether the account_intrastat module is installed, the
        export has a slighly different behaviour for non-service products.
        To handle this, we only use service products in the test.
    """

    @classmethod
    @TestSaftReport.setup_country('ro')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'name': 'Romanian Company',
            'city': 'Bucharest',
            'zip': '010001',
            'vat': 'RO1234567897',
            'company_registry': '1234567897',
            'phone': '+40 723545439',
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

        cls.bank_ro = cls.env['res.bank'].create({'name': 'Romanian Banking United'})
        cls.partner_bank = cls.env['res.partner.bank'].create({
            'acc_type': 'iban',
            'partner_id': cls.company_data['company'].partner_id.id,
            'acc_number': 'RO08 4298 6369 7813',
            'allow_out_payment': True,
            'bank_id': cls.bank_ro.id,
            'currency_id': cls.env.ref('base.RON').id,
        })

        cls.setup_other_currency('EUR', rates=[('2023-10-01', 0.2)])

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

    def test_saft_report_monthly(self):
        invoices = self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-10-01',
                'date': '2023-10-01',
                'partner_id': self.partner_a.id,
                'currency_id': self.env.ref('base.EUR').id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 5.0,
                    'price_unit': 400.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                })],
            },
            {
                'move_type': 'out_refund',
                'invoice_date': '2023-10-11',
                'date': '2023-10-11',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 3.0,
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-10-21',
                'date': '2023-10-21',
                'partner_id': self.partner_b.id,
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'price_unit': 800.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                })],
            },
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-10-26',
                'date': '2023-10-26',
                'partner_id': self.partner_b.id,
                'l10n_ro_is_self_invoice': True,  # This is a self-invoice
                'invoice_line_ids': [Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 2.0,
                    'price_unit': 600.0,
                    'tax_ids': [Command.set(self.company_data['default_tax_purchase'].ids)],
                })]
            }
        ])
        invoices.action_post()

        self.statement = self.env['account.bank.statement'].create({
            'name': 'test_statement',
            'line_ids': [
                Command.create({
                    'date': '2023-10-15',
                    'payment_ref': 'Payment Ref',
                    'partner_id': self.partner_a.id,
                    'journal_id': self.company_data['default_journal_bank'].id,
                    'foreign_currency_id': self.env.ref('base.EUR').id,
                    'amount': 1250.0,
                    'amount_currency': 250.0,
                }),
            ],
        })
        self._report_compare_with_test_file(
            self.report_handler.l10n_ro_export_saft_to_xml_monthly(self._generate_options()),
            'saft_report_monthly.xml'
        )

    def test_saft_report_errors_01(self):
        self.company_data['company'].write({
            'l10n_ro_saft_tax_accounting_basis': False,
            'phone': False,
            'bank_ids': False,
        })
        with self.assertRaises(self.ReportException) as cm:
            self.report_handler.l10n_ro_export_saft_to_xml_monthly(self._generate_options())
        self.assertEqual(set(cm.exception.errors), {
            'settings_accounting_basis_missing',
            'company_phone_missing',
            'company_bank_account_missing',
        })

    def test_saft_report_errors_02(self):
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-10-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        }).action_post()
        intrastat_installed = 'intrastat_code_id' in self.product_b
        self.partner_a.write({
            'city': False,
            'country_id': False,
            'vies_valid': False,
        })
        self.product_b.write({
            'default_code': False,
            'type': 'consu',
        })
        if intrastat_installed:
            self.product_b.intrastat_code_id = False
        with self.assertRaises(self.ReportException) as cm:
            self.report_handler.l10n_ro_export_saft_to_xml_monthly(self._generate_options())
        expected = {
            'partner_city_missing',
            'partner_country_missing',
            'product_internal_reference_missing',
        }
        if intrastat_installed:
            expected.add('product_intrastat_code_missing')
        self.assertEqual(set(cm.exception.errors), expected)

    def test_saft_report_errors_03(self):
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-10-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        }).action_post()
        self.company_data['default_tax_sale'].l10n_ro_saft_tax_type_id = False
        (self.company_data['company'].partner_id + self.partner_a).write({
            "vat": False,
            "company_registry": 'XXXX',
        })
        self.product_b.default_code = 'PA'

        with self.assertRaises(self.ReportException) as cm:
            self.report_handler.l10n_ro_export_saft_to_xml_monthly(self._generate_options())
        self.assertEqual(set(cm.exception.errors), {
            'partner_registry_incorrect',
            'company_registry_number_invalid',
            'taxes_tax_type_missing',
            'product_internal_reference_duplicated',
        })

    def test_saft_report_errors_04(self):
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-10-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                }),
            ],
        }).action_post()
        self.company_data['company'].write({
            'vat': False,
            'company_registry': False,
        })
        self.partner_a.country_id = self.env.ref('base.fr')
        with self.assertRaises(self.ReportException) as cm:
            self.report_handler.l10n_ro_export_saft_to_xml_monthly(self._generate_options())
        self.assertEqual(set(cm.exception.errors), {
            'company_vat_registry_number_missing',
            'partner_vat_doesnt_match_country',
        })

    def test_saft_zero_balance_partner(self):
        self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-10-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'product',
                        'price_unit': 100,
                    }),
                ],
            },
            {
                'move_type': 'out_refund',
                'invoice_date': '2023-10-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'product',
                        'price_unit': 100,
                    }),
                ],
            },
        ]).action_post()

        self._report_compare_with_test_file(
            self.report_handler.l10n_ro_export_saft_to_xml_monthly(self._generate_options()),
            'saft_report_zero_balance_partner.xml'
        )

    def test_saft_zero_line(self):
        self.env['account.move'].create([
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-10-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'product',
                        'price_unit': 100,
                    }),
                ],
            },
            {
                'move_type': 'out_invoice',
                'invoice_date': '2023-10-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'product',
                        'price_unit': 0,
                    }),
                ],
            },
        ]).action_post()

        self._report_compare_with_test_file(
            self.report_handler.l10n_ro_export_saft_to_xml_monthly(self._generate_options()),
            'saft_report_zero_line.xml'
        )

    def test_saft_reverse_charge(self):
        """The TaxInformation of a reverse charge should be the amount of the tax and not 0."""
        reverse_chart_tax = self.env['account.chart.template'].ref('tvati_intrap19b')
        self.env['account.move'].create([
            {
                'move_type': 'in_invoice',
                'invoice_date': '2023-10-01',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': 'product',
                        'price_unit': 100,
                        'tax_ids': [Command.set(reverse_chart_tax.ids)]
                    }),
                ],
            },
        ]).action_post()

        self._report_compare_with_test_file(
            self.report_handler.l10n_ro_export_saft_to_xml_monthly(self._generate_options()),
            'saft_report_reverse_charge.xml'
        )
