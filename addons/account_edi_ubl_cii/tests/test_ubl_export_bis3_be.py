from odoo import Command
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon
try:
    from odoo.addons.test_mimetypes.tests.test_guess_mimetypes import contents
except ImportError:
    contents = None

from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblExportBis3BE(TestUblBis3Common, TestUblCiiBECommon):

    def test_invoice_item_description_name(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(
            lst_price=100.0,
            default_code='P123',
            barcode='1234567890123',
            taxes_id=tax_21,
        )
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_item_description_name')

    def test_invoice_payee_financial_account(self):
        bank_kbc = self.env['res.bank'].create({
            'name': 'KBC',
            'bic': 'KREDBEBB',
        })
        self.env.company.bank_ids[0].bank_id = bank_kbc

        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_payee_financial_account')

    def test_invoice_negative_price_unit(self):
        """ Ensure the price_unit and the quantity sign are inversed during the generation of the
        xml because 'PriceAmount' cannot be negative.
        """
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(taxes_id=tax_21)
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=product, price_unit=100.0),
                self._prepare_invoice_line(product_id=product, price_unit=-10.0),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_negative_price_unit')

    def test_invoice_price_unit_more_decimals(self):
        tax_21 = self.percent_tax(21.0)
        decimal_precision = self.env['decimal.precision'].search([('name', '=', 'Product Price')], limit=1)
        decimal_precision.digits = 4
        product = self._create_product(lst_price=0.4567, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            product_id=product,
            quantity=10000.0,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_price_unit_more_decimals')

    def test_invoice_price_amount_rounding_precision_with_price_included_taxes(self):
        tax_21 = self.percent_tax(21.0, price_include_override='tax_included')
        product = self._create_product(lst_price=1039.99, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_price_amount_rounding_precision_with_price_included_taxes')

    def test_invoice_price_amount_rounding_precision_with_price_included_taxes_plus_free_product(self):
        tax_6 = self.percent_tax(6.0, price_include_override='tax_included')
        tax_21 = self.percent_tax(21.0, price_include_override='tax_included')
        product_1 = self._create_product(lst_price=0.0, taxes_id=tax_6)
        product_2 = self._create_product(lst_price=1.45, taxes_id=tax_21)
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=product_1, quantity=20.0, name="Miel des Cabanes - 250gr"),
                self._prepare_invoice_line(product_id=product_2, quantity=50.0, name="Conditionnement spécial - pots de 50gr"),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_price_amount_rounding_precision_with_price_included_taxes_plus_free_product')

    def test_invoice_tax_exempt(self):
        tax_0 = self.percent_tax(0.0)
        product = self._create_product(lst_price=990.0, taxes_id=tax_0)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_tax_exempt')

    def test_invoice_tax_reverse_charge(self):
        tax_21 = self.percent_tax(21.0)
        tax_minus_10_67 = self.percent_tax(-10.67)
        product = self._create_product(lst_price=1000.0, taxes_id=tax_21 + tax_minus_10_67)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_tax_reverse_charge')

    def test_invoice_allowance_charge_fixed_tax_recycling_contribution(self):
        """ Ensure the recycling contribution taxes are turned into allowance/charges at the document line level. """
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_auvibel = self.fixed_tax(2.0, name="AUVIBEL", include_base_amount=True)
        tax_bebat = self.fixed_tax(3.0, name="BEBAT", include_base_amount=True)
        tax_21 = self.percent_tax(21.0)
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=99.0,
                    tax_ids=tax_recupel + tax_21,
                ),
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=98.0,
                    quantity=4.0,
                    discount=25.0,
                    tax_ids=tax_auvibel + tax_21,
                ),
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=97.0,
                    tax_ids=tax_bebat + tax_21,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_allowance_charge_fixed_tax_recycling_contribution')

    def test_invoice_allowance_charge_custom_tax_recycling_contribution(self):
        """ Ensure the recycling contribution taxes are turned into allowance/charges at the document line level. """
        tax_recupel = self.python_tax("quantity * 1.0", name="RECUPEL", include_base_amount=True)
        tax_auvibel = self.python_tax("quantity * 2.0", name="AUVIBEL", include_base_amount=True)
        tax_21 = self.percent_tax(21.0)
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=99.0,
                    tax_ids=tax_recupel + tax_21,
                ),
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=98.0,
                    quantity=4.0,
                    discount=25.0,
                    tax_ids=tax_auvibel + tax_21,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_allowance_charge_custom_tax_recycling_contribution')

    def test_invoice_fixed_tax_emptying_turned_as_extra_invoice_lines(self):
        """ Ensure the emptying taxes (a.k.a 'vidange') are turned into extra invoice lines inside the xml. """
        tax_emptying = self.fixed_tax(0.10, name="Vidange")
        tax_21 = self.percent_tax(21.0)
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=100.0,
                    quantity=4.0,
                    tax_ids=tax_emptying + tax_21,
                ),
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=100.0,
                    quantity=1.0,
                    tax_ids=tax_emptying + tax_21,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_fixed_tax_emptying_turned_as_extra_invoice_lines')

    def test_invoice_custom_tax_emptying_turned_as_extra_invoice_lines(self):
        """ Ensure the emptying taxes (a.k.a 'vidange') are turned into extra invoice lines inside the xml. """
        tax_emptying = self.python_tax("quantity * 0.10", name="Vidange")
        tax_21 = self.percent_tax(21.0)
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=100.0,
                    quantity=4.0,
                    tax_ids=tax_emptying + tax_21,
                ),
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=100.0,
                    quantity=1.0,
                    tax_ids=tax_emptying + tax_21,
                ),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_custom_tax_emptying_turned_as_extra_invoice_lines')

    def test_invoice_manual_tax_amount(self):
        tax_12 = self.percent_tax(12.0)
        tax_21 = self.percent_tax(21.0)
        product_1 = self._create_product(lst_price=200.0, taxes_id=tax_21)
        product_2 = self._create_product(lst_price=100.0, taxes_id=tax_12)
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=product_1),
                self._prepare_invoice_line(product_id=product_1),
                self._prepare_invoice_line(product_id=product_2),
                self._prepare_invoice_line(product_id=product_2),
            ],
        )
        tax_line_21 = invoice.line_ids.filtered(lambda aml: aml.tax_line_id == tax_21)
        tax_line_12 = invoice.line_ids.filtered(lambda aml: aml.tax_line_id == tax_12)
        invoice.write({'line_ids': [
            Command.update(tax_line_21.id, {'amount_currency': tax_line_21.amount_currency + 0.01}),
            Command.update(tax_line_12.id, {'amount_currency': tax_line_12.amount_currency - 0.01}),
        ]})
        invoice.action_post()

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_manual_tax_amount')

    def test_invoice_early_pay_discount_multiple_taxes(self):
        tax_6 = self.percent_tax(6.0)
        tax_21 = self.percent_tax(21.0)
        mixed_early_payment_term = self._create_mixed_early_payment_term()
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_payment_term_id=mixed_early_payment_term.id,
            invoice_line_ids=[
                self._prepare_invoice_line(product_id=self.product_a, price_unit=200.0, tax_ids=tax_6),
                self._prepare_invoice_line(product_id=self.product_a, price_unit=2400.0, tax_ids=tax_21),
            ],
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_early_pay_discount_multiple_taxes')

    def test_invoice_early_pay_discount_with_recycling_contribution_tax(self):
        tax_recupel = self.fixed_tax(1.0, name="RECUPEL", include_base_amount=True)
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=99.0, taxes_id=tax_recupel + tax_21)
        mixed_early_payment_term = self._create_mixed_early_payment_term()
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            invoice_payment_term_id=mixed_early_payment_term.id,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_early_pay_discount_with_recycling_contribution_tax')

    def test_invoice_early_pay_discount_with_discount_on_lines(self):
        tax_21 = self.percent_tax(21.0)
        mixed_early_payment_term = self._create_mixed_early_payment_term()
        invoice = self._create_invoice(
            partner_id=self.partner_be,
            invoice_payment_term_id=mixed_early_payment_term.id,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    product_id=self.product_a,
                    price_unit=price_unit,
                    quantity=quantity,
                    discount=discount,
                    tax_ids=tax_21,
                )
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
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_early_pay_discount_with_discount_on_lines')

    def test_invoice_cash_rounding_add_invoice_line(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=1039.99, taxes_id=tax_21)
        cash_rounding = self._create_add_invoice_line_cash_rounding()
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            invoice_cash_rounding_id=cash_rounding,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_cash_rounding_add_invoice_line')

    def test_invoice_cash_rounding_biggest_tax(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=1039.99, taxes_id=tax_21)
        cash_rounding = self._create_biggest_tax_cash_rounding()
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            invoice_cash_rounding_id=cash_rounding,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_cash_rounding_biggest_tax')

    def test_invoice_tax_currency_code_tax_totals_foreign_currency(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=1039.99, taxes_id=tax_21)
        foreign_currency = self.setup_other_currency('RON')
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            currency_id=foreign_currency,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_tax_currency_code_tax_totals_foreign_currency')

    def test_invoice_sent_to_luxembourg_dig(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_lu_dig,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_sent_to_luxembourg_dig')

    def test_invoice_sent_to_partner_with_gln(self):
        self.ensure_installed('account_add_gln')
        self.partner_be.global_location_number = "222222222222"

        tax_21 = self.percent_tax(21.0)
        product = self._create_product(
            lst_price=100.0,
            taxes_id=tax_21,
        )
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_sent_to_partner_with_gln')

    def test_invoice_send_and_print_additional_documents(self):
        """ Ensure an additional document is added to the UBL under AdditionalDocumentReference. """
        self.ensure_installed('test_mimetypes')

        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=1039.99, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=self.partner_be,
            post=True,
        )

        # Supported
        xlsx_attachment = self.env['ir.attachment'].create({
            'name': 'xlsx attachment',
            'raw': contents('xlsx'),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        # Not supported
        docx_attachment = self.env['ir.attachment'].create({
            'name': 'docx attachment',
            'raw': contents('docx'),
            'mimetype': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        })
        xml_attachment = self.env['ir.attachment'].create({
            'name': 'xml attachment',
            'raw': "<?xml version='1.0' encoding='UTF-8'?><test/>",
            'mimetype': 'application/xml',
        })
        txt_attachment = self.env['ir.attachment'].create({
            'name': 'txt attachment',
            'raw': b'txt attachment'
        })

        wizard = self._create_account_move_send_wizard_single(invoice, sending_methods=['manual'])
        wizard.mail_attachments_widget = wizard.mail_attachments_widget + [{
            'id': attachment.id,
            'name': attachment.name,
            'mimetype': attachment.mimetype,
            'placeholder': False,
            'manual': True,
        } for attachment in [xlsx_attachment, docx_attachment, xml_attachment, txt_attachment]]
        wizard.action_send_and_print()

        self._assert_invoice_ubl_file(invoice, 'test_invoice_send_and_print_additional_documents')

    def test_invoice_negative_discount_upsell(self):
        """ Ensure a negative discount (upsell) is correctly handled as a Charge
        with the appropriate UNCL 7161 reason code (ADK) instead of an Allowance.
        """
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=10.0, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            product_id=product,
            quantity=10.0,
            price_unit=5.76,
            discount=-1.09,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)

        self._assert_invoice_ubl_file(invoice, 'test_invoice_negative_discount_upsell')
