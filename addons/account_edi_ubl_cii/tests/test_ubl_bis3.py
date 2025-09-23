from odoo import Command
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

    def _assert_invoice_ubl_file(self, invoice, filename):
        file_path = f'addons/{self.test_module}/tests/test_files/{filename}.xml'

        with misc.file_open(file_path, 'rb') as file:
            expected_content = file.read()
        self.assertTrue(invoice.ubl_cii_xml_id)
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(invoice.ubl_cii_xml_id.raw),
            self.get_xml_tree_from_string(expected_content),
        )

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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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

        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
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
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
        self._assert_invoice_ubl_file(invoice, 'bis3/test_early_pay_discount_with_discount_on_lines')

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
