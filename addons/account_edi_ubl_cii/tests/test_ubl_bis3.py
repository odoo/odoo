from contextlib import contextmanager
from unittest import mock

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import misc


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblBis3(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.tax_calculation_rounding_method = 'round_globally'
        cls.partner_a.invoice_edi_format = 'ubl_bis3'

        cls.pay_term_epd_mixed = cls.env['account.payment.term'].create({
            'name': "2/7 Net 30",
            'note': "Payment terms: 30 Days, 2% Early Payment Discount under 7 days",
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 7,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30})],
        })

    @classmethod
    def _create_company(cls, **create_values):
        # EXTENDS 'account'
        create_values['currency_id'] = cls.env.ref('base.EUR').id
        return super()._create_company(**create_values)

    def setup_partner_as_be1(self, partner):
        partner.write({
            'street': "Chaussée de Namur 40",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0202239951',
            'company_registry': '0202239951',
            'country_id': self.env.ref('base.be').id,
            'bank_ids': [Command.create({'acc_number': 'BE15001559627230'})],
        })

    def setup_partner_as_fr1(self, partner):
        partner.write({
            'street': "Rue de la Paix 1",
            'zip': "75000",
            'city': "Paris",
            'vat': 'FR23334175221',
            'country_id': self.env.ref('base.fr').id,
            'bank_ids': [Command.create({'acc_number': 'FR15001559627230'})],
        })

    def setup_partner_as_be2(self, partner):
        partner.write({
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'company_registry': '0477472701',
            'country_id': self.env.ref('base.be').id,
            'bank_ids': [Command.create({'acc_number': 'BE90735788866632'})],
        })

    @contextmanager
    def allow_sending_vendor_bills(self):
        old_get_move_constraints = self.env['account.move.send'].__class__._get_move_constraints

        def patched_get_move_constraints(self, move):
            constraints = old_get_move_constraints(self, move)
            if move.is_purchase_document():
                constraints.pop('not_sale_document', None)
            return constraints

        with mock.patch.object(self.env['account.move.send'].__class__, '_get_move_constraints', patched_get_move_constraints):
            yield

    def _assert_invoice_ubl_file(self, invoice, filename):
        file_path = f'addons/{self.test_module}/tests/test_files/{filename}.xml'

        with misc.file_open(file_path, 'rb') as file:
            expected_content = file.read()
        self.assertTrue(invoice.ubl_cii_xml_id)
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(invoice.ubl_cii_xml_id.raw),
            self.get_xml_tree_from_string(expected_content),
        )

    def assert_same_invoice(self, invoice1, invoice2, **invoice_kwargs):
        self.assertEqual(len(invoice1.invoice_line_ids), len(invoice2.invoice_line_ids))
        self.assertRecordValues(invoice2, [{
            'partner_id': invoice1.partner_id.id,
            'invoice_date': fields.Date.from_string(invoice1.date),
            'currency_id': invoice1.currency_id.id,
            'amount_untaxed': invoice1.amount_untaxed,
            'amount_tax': invoice1.amount_tax,
            'amount_total': invoice1.amount_total,
            **invoice_kwargs,
        }])

        default_invoice_line_kwargs_list = [{}] * len(invoice1.invoice_line_ids)
        invoice_line_kwargs_list = invoice_kwargs.get('invoice_line_ids', default_invoice_line_kwargs_list)
        self.assertRecordValues(invoice2.invoice_line_ids, [{
            'quantity': line.quantity,
            'price_unit': line.price_unit,
            'discount': line.discount,
            'product_id': line.product_id.id,
            'product_uom_id': line.product_uom_id.id,
            **invoice_line_kwargs,
        } for line, invoice_line_kwargs in zip(invoice1.invoice_line_ids, invoice_line_kwargs_list)])

    def test_export_invoice_from_account_edi_xml_ubl_bis3(self):
        """ This test checks the result of `export_invoice` rather than `_generate_and_send_invoices`
        because the latter calls `cleanup_xml_node`. This helps us catch nodes with attributes but no
        text, that shouldn't be rendered, but are silently removed by `cleanup_xml_node`.
        """
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        actual_content, _dummy = self.env['account.edi.xml.ubl_bis3'].with_context(lang='en_US')._export_invoice(invoice)
        with misc.file_open(f'addons/{self.test_module}/tests/test_files/bis3/test_invoice.xml', 'rb') as file:
            expected_content = file.read()
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(actual_content),
            self.get_xml_tree_from_string(expected_content),
        )

    def test_product_code_and_barcode(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        self.product_a.write({
            'default_code': 'P123',
            'barcode': '1234567890123',
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_product_code_and_barcode')

    def test_financial_account(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)

        bank_kbc = self.env['res.bank'].create({
            'name': 'KBC',
            'bic': 'KREDBEBB',
        })
        self.env.company.bank_ids[0].bank_id = bank_kbc
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_financial_account')

    # -------------------------------------------------------------------------
    # TAXES
    # -------------------------------------------------------------------------

    def test_taxes_rounding_negative_line_tax_included(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0, price_include_override='tax_included')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1039.99,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': -72.80,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_taxes_rounding_negative_line_tax_included')

    def test_single_fixed_tax_price_excluded(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 99.0,
                    'tax_ids': [Command.set((tax_recupel + tax_21).ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_single_fixed_tax_price_excluded')

    def test_single_fixed_tax_price_included(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True, price_include_override='tax_included')
        tax_21 = self.percent_tax(21.0, price_include_override='tax_included')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 121.0,
                    'tax_ids': [Command.set((tax_recupel + tax_21).ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_single_fixed_tax_price_included')

    def test_multiple_fixed_taxes_price_excluded(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_auvibel = self.fixed_tax(1.0, name="AUVIBEL", include_base_amount=True)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 98.0,
                    'tax_ids': [Command.set((tax_recupel + tax_auvibel + tax_21).ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_multiple_fixed_taxes_price_excluded')

    def test_single_fixed_tax_price_excluded_and_discount(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 2,
                    'discount': 10,
                    'price_unit': 99.0,
                    'tax_ids': [Command.set((tax_recupel + tax_21).ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_single_fixed_tax_price_excluded_and_discount')

    def test_manual_tax_amount_on_invoice(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_12 = self.percent_tax(12.0)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_12.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_12.ids)],
                }),
            ],
        })
        tax_line_21 = invoice.line_ids.filtered(lambda aml: aml.tax_line_id == tax_21)
        tax_line_12 = invoice.line_ids.filtered(lambda aml: aml.tax_line_id == tax_12)
        invoice.write({'line_ids': [
            Command.update(tax_line_21.id, {'amount_currency': tax_line_21.amount_currency + 0.01}),
            Command.update(tax_line_12.id, {'amount_currency': tax_line_12.amount_currency - 0.01}),
        ]})
        invoice.action_post()

        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_manual_tax_amount_on_invoice')

    # -------------------------------------------------------------------------
    # PRICE UNIT
    # -------------------------------------------------------------------------

    def test_price_unit_with_more_decimals(self):
        """ Ensure PriceAmount is well computed according the number of decimals allowed by 'Product Price'."""
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)
        decimal_precision = self.env['decimal.precision'].search([('name', '=', 'Product Price')], limit=1)
        decimal_precision.digits = 4

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 10000,
                    'price_unit': 0.4567,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_price_unit_with_more_decimals')

    # -------------------------------------------------------------------------
    # PAYMENT TERM
    # -------------------------------------------------------------------------

    def test_early_pay_discount_different_taxes(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_6 = self.percent_tax(6.0)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.pay_term_epd_mixed.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'tax_ids': [Command.set(tax_6.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 2400.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_early_pay_discount_different_taxes')

    def test_early_pay_discount_with_fixed_tax(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.pay_term_epd_mixed.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 99.0,
                    'tax_ids': [Command.set((tax_recupel + tax_21).ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_early_pay_discount_with_fixed_tax')

    def test_early_pay_discount_with_discount_on_lines(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.pay_term_epd_mixed.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': quantity,
                    'price_unit': price_unit,
                    'discount': discount,
                    'tax_ids': [Command.set(tax_21.ids)],
                })
                for quantity, price_unit, discount in (
                    (20.0, 180.75, 41.0),
                    (480.0, 25.80, 41.0),
                    (3.0, 532.5, 39.0),
                    (3.0, 74.25, 39.0),
                    (3.0, 369.0, 39.0),
                    (5.0, 79.5, 39.0),
                    (5.0, 107.5, 39.0),
                    (5.0, 160.0, 39.0),
                    (5.0, 276.75, 39.0),
                    (60.0, 8.32, 39.0),
                    (60.0, 8.32, 39.0),
                    (12.0, 37.65, 39.0),
                    (12.0, 89.4, 39.0),
                    (12.0, 149.4, 39.0),
                    (6.0, 124.8, 39.0),
                    (1.0, 253.2, 39.0),
                    (12.0, 48.3, 39.0),
                    (20.0, 34.8, 39.0),
                    (10.0, 48.3, 39.0),
                    (10.0, 72.0, 39.0),
                    (5.0, 96.0, 39.0),
                    (3.0, 115.5, 39.0),
                    (4.0, 50.75, 39.0),
                    (30.0, 21.37, 39.0),
                    (3.0, 40.8, 39.0),
                    (3.0, 40.8, 39.0),
                    (3.0, 39.0, 39.0),
                    (-1.0, 1337.83, 0.0),
                )
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_early_pay_discount_with_discount_on_lines')

    # -------------------------------------------------------------------------
    # CASH ROUDNING
    # -------------------------------------------------------------------------

    def test_export_import_cash_rounding(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21_sale = self.percent_tax(21.0)
        _tax_21_purchase = self.percent_tax(21.0, type_tax_use='purchase')  # for the import
        currency = self.setup_other_currency('USD', rounding=0.001)
        cash_rounding_line = self.env['account.cash.rounding'].create({
            'name': '1.0 Line',
            'rounding': 1.00,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data['default_account_revenue'].copy().id,
            'loss_account_id': self.company_data['default_account_expense'].copy().id,
            'rounding_method': 'HALF-UP',
        })

        cash_rounding_tax = self.env['account.cash.rounding'].create({
            'name': '1.0 Tax',
            'rounding': 1.00,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
        })

        test_data = [
            {
                'invoice_cash_rounding_id': cash_rounding_tax,
                'expected': {
                    'xml_file': 'bis3/test_cash_rounding_tax',
                    'xpaths': None,
                },
                'expected_rounding_invoice_line_values': None,
            },
            {
                'invoice_cash_rounding_id': cash_rounding_line,
                'expected': {
                    'xml_file': 'bis3/test_cash_rounding_line',
                    'xpaths': None,
                },
                # We create an invoice line for the rounding amount.
                # (This adjusts the base amount of the invoice.)
                'expected_rounding_invoice_line_values': {
                    'display_type': 'product',
                    'name': 'Rounding',
                    'quantity': 1,
                    'product_id': False,
                    'price_unit': 0.30,
                    'amount_currency': -0.30,
                    'balance': -0.15,
                    'currency_id': currency.id,
                }
            },
        ]
        for test in test_data:
            cash_rounding_method = test['invoice_cash_rounding_id']
            with self.subTest(sub_test_name=f"cash rounding method: {cash_rounding_method.name}"):
                invoice = self.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'partner_id': self.partner_a.id,
                    'currency_id': currency.id,
                    'invoice_date': '2017-01-01',
                    'invoice_cash_rounding_id': cash_rounding_method.id,
                    'invoice_line_ids': [
                        Command.create({
                            'product_id': self.product_a.id,
                            'quantity': 1,
                            'price_unit': 70.00,
                            'tax_ids': [Command.set([tax_21_sale.id])],
                        }),
                    ],
                })
                invoice.action_post()
                self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])

                attachment = invoice.ubl_cii_xml_id
                self.assertTrue(attachment)
                self._assert_invoice_ubl_file(invoice, test['expected']['xml_file'])

                # Check that importing yields the expected results.

                # For the 'add_invoice_line' strategy we create a dedicated invoice line for the cash rounding.
                rounding_invoice_line_values = test['expected_rounding_invoice_line_values']
                if rounding_invoice_line_values:
                    invoice.button_draft()
                    invoice.invoice_cash_rounding_id = False  # Do not round twice
                    invoice.invoice_line_ids.create([{
                        'company_id': invoice.company_id.id,
                        'move_id': invoice.id,
                        'partner_id': invoice.partner_id.id,
                        **rounding_invoice_line_values,
                    }])
                    invoice.action_post()

                invoice.journal_id.create_document_from_attachment(attachment.ids)
                imported_invoice = self.env['account.move'].search([], order='id desc', limit=1)
                self.assert_same_invoice(invoice, imported_invoice)

                # Check that importing a bill yields the expected results.

                imported_bill = self.company_data['default_journal_purchase']._create_document_from_attachment(attachment.ids)
                self.assertTrue(imported_bill)
                self.assert_same_invoice(invoice, imported_bill, partner_id=self.env.company.partner_id.id)

    # -------------------------------------------------------------------------
    # BASE DELTA DISTRIBUTION
    # -------------------------------------------------------------------------

    def test_dispatch_base_lines_delta(self):
        """ Test that the delta is dispatched evenly on the base lines. """
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10.04,
                    'discount': 10,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ] + [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1.04,
                    'discount': 10,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ] * 10,
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_dispatch_base_lines_delta')

    def test_unit_price_precision(self):
        """ Check that with large quantities, the precision of the rounding on the unit price
            is adapted in order to pass the Peppol schematron's requirement that the line's
            subtotal must be equal to unit price * quantity, to a tolerance of less than 0.02.

            In this case, the line's tax-excluded subtotal is 85.62, there are 8 units, so the raw unit
            price is 85.62 / 8 = 10.7025.
            If we round the unit price to 2 decimals, we get 10.70, but 10.70 * 8 = 85.60 which has
            a difference of 0.02 with the subtotal, so this would not pass the schematron.
            So we need to round the unit price to 3 decimals, which gives 10.703.
        """
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0, price_include_override='tax_included')

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 8,
                    'price_unit': 12.95,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_unit_price_precision')

    # -------------------------------------------------------------------------
    # SELF-BILLED INVOICE
    # -------------------------------------------------------------------------

    def test_export_vendor_bill(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        self_billing_journal = self.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self_billing_journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set([tax_21.id])],
                }),
            ],
        })

        invoice.action_post()
        with self.allow_sending_vendor_bills():
            self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_vendor_bill')

    def test_export_vendor_bill_reverse_charge(self):
        self.setup_partner_as_fr1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21_reverse_charge = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )

        self_billing_journal = self.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'journal_id': self_billing_journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set([tax_21_reverse_charge.id])],
                }),
            ],
        })
        invoice.action_post()
        with self.allow_sending_vendor_bills():
            self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_vendor_bill_reverse_charge')

    def test_export_vendor_credit_note(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)

        self_billing_journal = self.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
            'refund_sequence': False,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'in_refund',
            'journal_id': self_billing_journal.id,
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set([tax_21.id])],
                }),
            ],
        })

        invoice.action_post()
        with self.allow_sending_vendor_bills():
            self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_vendor_credit_note')
