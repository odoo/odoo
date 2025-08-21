from freezegun import freeze_time
from lxml import etree

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

    def test_product_intrastat_code(self):
        if self.env['ir.module.module']._get('account_intrastat').state != 'installed':
            self.skipTest("module account_intrastat is not installed")

        self.product_a.intrastat_code_id = self.env['account.intrastat.code'].sudo().create({
            'name': 'An Intrastat Code',
            'type': 'commodity',
            'code': 456,
            'supplementary_unit': 'l',
        })

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
        self._assert_invoice_ubl_file(invoice, 'bis3/test_product_intrastat_code')

    def test_product_intrastat_code_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_product_intrastat_code()

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
    # PAYMENT Method
    # -------------------------------------------------------------------------
    def test_payment_means(self):
        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_6 = self.percent_tax(6.0)

        payment_method = self.env.ref('account_edi_ubl_cii.account_payment_method_standing_agreement_in')
        payment_method_line = self.env['account.payment.method.line'].create({
            'name': 'Standing Agreement Test',
            'payment_method_id': payment_method.id,
            'payment_type': 'inbound',
            'journal_id': self.company_data['default_journal_bank'].id,
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'preferred_payment_method_line_id': payment_method_line.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'tax_ids': [Command.set(tax_6.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods={'manual'})
        self._assert_invoice_ubl_file(invoice, 'bis3/test_payment_means')

    def test_payment_means_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_payment_means()

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

    @freeze_time('2017-01-01')
    def test_sale_order_discount(self):
        if self.env['ir.module.module']._get('sale').state != 'installed':
            self.skipTest("module sale is not installed")

        self.setup_partner_as_be1(self.env.company.partner_id)
        self.setup_partner_as_be2(self.partner_a)
        tax_21 = self.percent_tax(21.0)
        tax_6 = self.percent_tax(6.0)

        sale_order = self.env['sale.order'].create({
            'name': 'My SO',
            'partner_id': self.partner_a.id,
            'client_order_ref': 'PO/1234',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'name': 'Product A description',
                    'product_uom_qty': 1.0,
                    'price_unit': 100.0,
                    'tax_id': [Command.set(tax_21.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'name': 'Product A description',
                    'product_uom_qty': 1.0,
                    'price_unit': 100.0,
                    'tax_id': [Command.set(tax_6.ids)],
                })
            ]
        })

        discount_wizard = self.env['sale.order.discount'].create({
            'sale_order_id': sale_order.id,
            'discount_percentage': 0.1,
            'discount_type': 'so_discount',
        })
        discount_wizard.action_apply_discount()

        sale_order.action_confirm()

        invoice = sale_order._create_invoices()
        invoice.action_post()

        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self._assert_invoice_ubl_file(invoice, 'bis3/test_sale_order_discount')

    def test_sale_order_discount_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_sale_order_discount()

    # -------------------------------------------------------------------------
    # Business Expert Group (BEG)
    # -------------------------------------------------------------------------
    def _get_xml_tree_from_file(self, filename):
        file_path = f'addons/{self.test_module}/tests/test_files/{filename}.xml'
        with misc.file_open(file_path, 'rb') as file:
            expected_content = file.read()
        return self.get_xml_tree_from_string(expected_content)

    def _setup_beg_supplier(self, partner, **vals):
        bank = self.env['res.bank'].create({
            'name': 'KBC',
            'bic': 'BPOTBEB1',
        })

        partner.write({
            'name': "Demo Shop NV",
            'street': "Main street 123",
            'zip': "1000",
            'city': "BRUSSELS",
            'company_registry': '0123456749',
            'country_id': self.env.ref('base.be').id,
            'bank_ids': [Command.create({'acc_number': 'BE54000000000097', 'bank_id': bank.id})],
            'email': 'myname@demoshop.be',
            'peppol_endpoint': '0123456749',
            **vals,
        })

    def _setup_beg_customer(self, partner, **vals):
        partner.with_context(no_vat_validation=True).write({
            'name': "Hotel Local SPRL",
            'street': "Rue de la Mairie 456",
            'zip': "4000",
            'city': "LIEGE",
            'vat': 'BE0214168947',  # Fails the VAT validation
            'company_registry': '0214168947',
            'country_id': self.env.ref('base.be').id,
            'peppol_endpoint': '0214168947',
            **vals,
        })

    def test_beg_testcase01_minimal_invoice(self):
        tax_21 = self.percent_tax(21.0)
        tax_6 = self.percent_tax(6.0)
        pay_term_30days = self.env['account.payment.term'].create({
            'name': "30 Days",
            'note': "30 days after invoice date",
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30})],
        })

        self._setup_beg_supplier(self.env.company.partner_id, vat='BE0123456749')
        self._setup_beg_customer(self.partner_a)
        partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Hotel Local SPRL - Nom commercial',
            'parent_id': self.partner_a.id,
        })

        self.product_a.name = "Good Y"
        self.product_b.write({
            'name': "Good X",
            'uom_id': self.env.ref('uom.product_uom_unit'),  # dozen by default
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '2018-04-09',
            'delivery_date': '2018-04-01',
            'invoice_payment_term_id': pay_term_30days.id,
            'narration': 'Testcase 1',
            'ref': 'YR127129',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 60,
                    'quantity': 40,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 20,
                    'quantity': 10,
                    'tax_ids': [Command.set(tax_6.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self.assertTrue(invoice.ubl_cii_xml_id)

        self.assertXmlTreeEqual(
            etree.fromstring(invoice.ubl_cii_xml_id.raw),
            self._get_xml_tree_from_file('bis3_from_BEG/testcase01_minimal_invoice'),
        )

    def test_beg_testcase01_minimal_invoice_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_beg_testcase01_minimal_invoice()

    def test_beg_testcase05_cash_discount(self):
        tax_21 = self.percent_tax(21.0)
        tax_6 = self.percent_tax(6.0)

        pay_term_cash_discount = self.env['account.payment.term'].create({
            'name': "2/14 Net 31",
            'note': "Payment terms: 31 Days, 2% Early Payment Discount under 14 days",
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 14,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 31})],
        })

        self._setup_beg_supplier(self.env.company.partner_id, vat='BE0123456749')
        self._setup_beg_customer(self.partner_a)
        partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Hotel Local SPRL - Nom commercial',
            'parent_id': self.partner_a.id,
            'email': 'dupont@hotel-local.be',
        })

        self.product_a.name = "good X"
        self.product_b.write({
            'name': "good Y",
            'uom_id': self.env.ref('uom.product_uom_unit'),  # dozen by default
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '2018-07-25',
            'delivery_date': '2018-07-01',
            'invoice_payment_term_id': pay_term_cash_discount.id,
            'narration': 'Testcase 5',
            'ref': '123456789',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_6.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 2400,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self.assertTrue(invoice.ubl_cii_xml_id)

        xpath = ""
        with_new_helpers = misc.str2bool(
            self.env['ir.config_parameter'].sudo().get_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True),
            default=True,
        )
        if with_new_helpers:
            # We create 2 VAT-exempt AllowanceCharge nodes (each non VAT-exempt AllowanceCharge node has a dedicated counterpart node)
            # In the example there is only 1 VAT-exempt AllowanceCharge node (over the sum of the 2 non VAT-exempt AllowanceCharge nodes)
            xpath = '''
                <xpath expr="//*[local-name()='AllowanceCharge'
                                 and ./*[local-name()='TaxCategory']/*[local-name()='Percent' and text()='0.0']
                                 and ./*[local-name()='AllowanceChargeReasonCode' and text()='ZZZ']
                                 and ./*[local-name()='Amount' and @currencyID='EUR' and text()='4.00']]" position="replace"
                    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"/>
                <xpath expr="//*[local-name()='AllowanceCharge'
                                 and ./*[local-name()='TaxCategory']/*[local-name()='Percent' and text()='0.0']
                                 and ./*[local-name()='AllowanceChargeReasonCode' and text()='ZZZ']
                                ]/*[local-name()='Amount' and @currencyID='EUR' and text()='48.00']" position="replace"
                    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
                    <cbc:Amount currencyID="EUR">52.00</cbc:Amount>
                </xpath>
            '''

        adjusted_output_tree = self.with_applied_xpath(
            etree.fromstring(invoice.ubl_cii_xml_id.raw),
            xpath,
        )

        self.assertXmlTreeEqual(
            adjusted_output_tree,
            self._get_xml_tree_from_file('bis3_from_BEG/testcase05_cash_discount'),
        )

    def test_beg_testcase05_cash_discount_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_beg_testcase05_cash_discount()

    def test_beg_testcase06_discount_with_cash_payment(self):
        tax_21 = self.percent_tax(21.0)
        tax_6 = self.percent_tax(6.0)

        pay_term_cash_discount = self.env['account.payment.term'].create({
            'name': "2/14 Net 31",
            'note': "Payment terms: 31 Days, 2% Early Payment Discount under 14 days",
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 14,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 31})],
        })

        self._setup_beg_supplier(self.env.company.partner_id, vat='BE0123456749')
        self._setup_beg_customer(self.partner_a)
        partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Hotel Local SPRL - Nom commercial',
            'parent_id': self.partner_a.id,
            'email': 'dupont@hotel-local.be',
        })

        self.product_a.name = "goed X"
        self.product_b.write({
            'name': "goed Y",
            'uom_id': self.env.ref('uom.product_uom_unit'),  # dozen by default
        })

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'invoice_date': '2018-07-25',
            'delivery_date': '2018-07-01',
            'invoice_payment_term_id': pay_term_cash_discount.id,
            'narration': 'Testcase 6',
            'ref': '123456789',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_6.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 2400,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()

        self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'payment_date': '2018-07-01'})\
            ._create_payments()
        # The invoice is fully paid; but we only paid the discounted amount
        self.assertRecordValues(invoice, [{
                'amount_residual': 0.0,
                'amount_total': 3105.68,
        }])
        self.assertRecordValues(invoice.matched_payment_ids, [{'amount': 3053.68}])

        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self.assertTrue(invoice.ubl_cii_xml_id)

        self.assertXmlTreeEqual(
            # Note: in the original test XML `PaymentID` is `Invoice 2019000005` even though `ID` is `2019000006`
            etree.fromstring(invoice.ubl_cii_xml_id.raw),
            self._get_xml_tree_from_file('bis3_from_BEG/testcase06_discount_with_cash_payment'),
        )

    def test_beg_testcase06_discount_with_cash_payment_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_beg_testcase06_discount_with_cash_payment()

    def test_beg_testcase10_invoice_in_usd_and_eur_vat_21(self):
        currency = self.setup_other_currency('USD', rounding=0.01, rates=[('2018-01-01', 3_272.22 / 2_931.68)])
        tax_21 = self.percent_tax(21.0)
        pay_term_30days = self.env['account.payment.term'].create({
            'name': "30 Days",
            'note': "30 days after invoice date",
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30})],
        })

        self._setup_beg_supplier(self.env.company.partner_id, vat='BE0000000196')
        self._setup_beg_customer(self.partner_a)
        partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Hotel Local SPRL - Nom commercial',
            'parent_id': self.partner_a.id,
            'email': 'dupont@hotel-local.be',
        })
        shipping_partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Delivery location name',
            'parent_id': self.partner_a.id,
        })

        self.product_a.name = "Something"

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'partner_shipping_id': shipping_partner.id,
            'invoice_date': '2018-04-09',
            'delivery_date': '2018-04-01',
            'invoice_payment_term_id': pay_term_30days.id,
            'narration': 'Testcase 10',
            'currency_id': currency.id,
            'ref': 'YR127129',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 15_582,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self.assertTrue(invoice.ubl_cii_xml_id)

        self.assertXmlTreeEqual(
            etree.fromstring(invoice.ubl_cii_xml_id.raw),
            self._get_xml_tree_from_file('bis3_from_BEG/testcase10_invoice_in_usd_and_eur_vat_21'),
        )

    def test_beg_testcase10_invoice_in_usd_and_eur_vat_21_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_beg_testcase10_invoice_in_usd_and_eur_vat_21()

    def test_beg_testcase11_invoice_in_usd_and_eur_vat_6_and_vat_21(self):
        currency = self.setup_other_currency('USD', rounding=0.01, rates=[('2018-01-01', 3_278.22 / 2_937.08)])
        tax_21 = self.percent_tax(21.0)
        tax_6 = self.percent_tax(6.0)
        pay_term_30days = self.env['account.payment.term'].create({
            'name': "30 Days",
            'note': "30 days after invoice date",
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30})],
        })

        self._setup_beg_supplier(self.env.company.partner_id, vat='BE0000000196')
        self._setup_beg_customer(self.partner_a)
        partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Hotel Local SPRL - Nom commercial',
            'parent_id': self.partner_a.id,
            'email': 'dupont@hotel-local.be',
        })
        shipping_partner = self.env['res.partner'].with_context(no_vat_validation=True).create({
            'name': 'Delivery location name',
            'parent_id': self.partner_a.id,
        })

        self.product_a.name = "Something"
        self.product_b.name = "Something else"

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'partner_shipping_id': shipping_partner.id,
            'invoice_date': '2018-04-09',
            'delivery_date': '2018-04-01',
            'invoice_payment_term_id': pay_term_30days.id,
            'narration': 'Testcase 11',
            'currency_id': currency.id,
            'ref': 'YR127129',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 15_582,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'quantity': 1,
                    'tax_ids': [Command.set(tax_6.ids)],
                }),
            ],
        })
        invoice.action_post()
        self.env['account.move.send']._generate_and_send_invoices(invoice, sending_methods=['manual'])
        self.assertTrue(invoice.ubl_cii_xml_id)

        self.assertXmlTreeEqual(
            etree.fromstring(invoice.ubl_cii_xml_id.raw),
            self._get_xml_tree_from_file('bis3_from_BEG/testcase11_invoice_in_usd_and_eur_vat_6_and_vat_21'),
        )

    def test_beg_testcase11_invoice_in_usd_and_eur_vat_6_and_vat_21_new(self):
        self.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        self.test_beg_testcase11_invoice_in_usd_and_eur_vat_6_and_vat_21()
