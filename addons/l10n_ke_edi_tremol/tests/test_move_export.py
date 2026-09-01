# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from freezegun import freeze_time

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestKeMoveExport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ke')
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_a.write({
            'name': 'Sirius Cybernetics Corporation',
            'street': 'Test Street',
            'street2': 'Further Test Street',
            'city': 'Nairobi',
            'zip': '00500',
            'country_id': cls.env.ref('base.ke').id,
            'vat': 'A000123456F',
        })

        cls.product_a.write({
            'name': 'Infinite Improbability Drive',
        })

        cls.spaceship_tax = cls.env['account.tax'].create({
            'name': 'Exempt Spaceship tax',
            'amount': 0,
            'amount_type': 'percent',
            'l10n_ke_item_code_id': cls.env.ref('l10n_ke.item_code_2023_00391153').id,
        })

    @classmethod
    def line_dict_to_bytes(cls, line_dict):
        """ Helper method for creating the expected lines """
        msg = b'1' + b';'.join([                       # 0x31, command to add a line
            line_dict.get('name', b''.ljust(36)),      # 36 characters for the name
            line_dict.get('vat_class', b'B'),          # 1 symbol for vat class (b, the KRA byte for the 16% standard rate, when no item code is set)
            line_dict.get('price', b'1'),              # up to 15 symbols for the unit price, tax included (up to 5 decimal places)
            line_dict.get('uom', b'Uni'),              # 3 symbols for uom
            line_dict.get('item_code', b''.ljust(10)), # 10 symbols for item code (only reported when the tax is not 16.0%)
            line_dict.get('item_desc', b''.ljust(20)), # item description (only reported when the tex is not 16.0%)
            line_dict.get('vat_rate', b'16.0'),        # vat rate
        ])
        if line_dict.get('quantity'):
            msg += b'*' + line_dict.get('quantity')    # 1 to 10 symbols for quantity
        if line_dict.get('discount'):
            msg += b',' + line_dict.get('discount')    # 1 to 7 symbols for discount/addition
        return msg

    @freeze_time('2023-01-01')
    def test_export_simple_invoice(self):
        """ The _l10n_ke_get_cu_messages function serialises the data from the invoice as a series
            of messages representing commands to the device. The proxy must only wrap these messages
            (with the checksum, etc) and send them to the device, and issue a response.
        """
        simple_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'quantity': 10,
                    'price_unit': 1234.56,
                    'tax_ids': [(6, 0, [self.spaceship_tax.id])],
                    'discount': 25,
                }),
            ],
        })
        simple_invoice.action_post()
        generated_messages = simple_invoice._l10n_ke_get_cu_messages()
        expected_sale_line = self.line_dict_to_bytes({
            'name': b'Infinite Improbability Drive        ',
            'price': b'1234.56', # This is the unit price, (though this is tax exempt)
            'item_code': b'0039.11.53',
            'item_desc': b'Spacecraft including',
            'quantity': b'10.0',
            'discount': b'-25.0%',
            'vat_rate': b'0.0',
            'vat_class': b'A',  # item_code_2023_00391153 is stored as tax_rate='E' (Exempted), remapped to the KRA byte 'A'
        })
        expected_messages = [
            # open invoice
            b'01;     0;0;1;Sirius Cybernetics Corporation;A000123456F   ;Test StreetFurther Test Street;Test StreetFurther Test Street;00500Nairobi                  ;                              ;INV202300001   ',
            # sale of article
            expected_sale_line,
            # close invoice
            b'8',
            # read date / time
            b'h',
        ]
        self.assertEqual(generated_messages, expected_messages)

        # Next assign the invoice a control unit number, and create a credit note from the invoice
        simple_invoice.l10n_ke_cu_invoice_number = '42424200420000004242'
        simple_credit_note = simple_invoice._reverse_moves()
        simple_credit_note.action_post()
        generated_messages = simple_credit_note._l10n_ke_get_cu_messages()

        # The credit note of the simple invoice should have the same content, excepting that
        expected_credit_note_header = [b''.join([
            b'0', b'1;', b'     0;', b'0;',
            b'A;',                              # This reserved 'field' is a capital 'A' instead of a '1'
            b'Sirius Cybernetics Corporation;',
            b'A000123456F   ;',
            b'Test StreetFurther Test Street;',
            b'Test StreetFurther Test Street;',
            b'00500Nairobi                  ;',
            b'                              ;',
            b'4242420042000000424;',            # The 'Related invoice number' is the control unit number of the reversed invoice
            b'RINV202300001  ',                 # The invoice number is the number of the credit note
        ])]
        expected_messages = expected_credit_note_header + expected_messages[1:]
        self.assertEqual(generated_messages, expected_messages)

    @freeze_time('2023-01-01')
    def test_export_global_discount_invoice(self):
        """ Negative lines can be used as global discounts, the function that serialises the invoice
            should recognise these discount lines, and subtract them from positive lines,
            representing the subtraction as a discount. Existing discounts on lines should be
            handled correctly too.
        """
        global_discount_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'quantity': 10,
                    'price_unit': 10,
                    'tax_ids': [(6, 0, [self.company_data['company'].account_sale_tax_id.id])],
                    'discount': 10
                }),
                (0, 0, {
                    'name': "don't panic",
                    'quantity': 1,
                    'price_unit': -10,
                    'tax_ids': [(6, 0, [self.company_data['company'].account_sale_tax_id.id])],
                }),
            ],
        })
        global_discount_invoice.action_post()
        generated_messages = global_discount_invoice._l10n_ke_get_cu_messages()
        expected_discounted_line = self.line_dict_to_bytes({
            'name': b'Infinite Improbability Drive        ',
            'price': b'11.6',
            'quantity': b'10.0',
            # The discount is -20%, because there is an existing discount on the line of 10%, and
            # another negative line with the amount -10 would be another -10% discount.
            'discount': b'-20.0%',
        })
        expected_messages = [
            b'01;     0;0;1;Sirius Cybernetics Corporation;A000123456F   ;Test StreetFurther Test Street;Test StreetFurther Test Street;00500Nairobi                  ;                              ;INV202300001   ',
            expected_discounted_line,
            b'8',
            b'h'
        ]
        self.assertEqual(generated_messages, expected_messages)

        # A copy of the invoice where the positive line is the product of a double negative
        # (negative price and negative quantity) should yeild exactly the same representation.
        double_negative_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'quantity': -10,
                    'price_unit': -10,
                    'tax_ids': [(6, 0, [self.company_data['company'].account_sale_tax_id.id])],
                    'discount': 10
                }),
                (0, 0, {
                    'name': "don't panic",
                    'quantity': 1,
                    'price_unit': -10,
                    'tax_ids': [(6, 0, [self.company_data['company'].account_sale_tax_id.id])],
                }),
            ],
        })
        double_negative_invoice.action_post()
        generated_messages = double_negative_invoice._l10n_ke_get_cu_messages()
        # There representation is exactly the same, excepting that the name of the invoice is different
        expected_double_negative_header = [b'01;     0;0;1;Sirius Cybernetics Corporation;A000123456F   ;Test StreetFurther Test Street;Test StreetFurther Test Street;00500Nairobi                  ;                              ;INV202300002   ']
        expected_messages = expected_double_negative_header + expected_messages[1:]
        self.assertEqual(generated_messages, expected_messages)

    def test_export_multi_tax_line_invoice(self):
        """ When handling invoices with multiple taxes per line, the export should handle the
            reported amounts correctly. Using only the VAT taxes in its calculation and not, for
            instance, the 2% tourism levy, or the 4% drinks service charge, or the 10% food service
            charge.
        """
        tourism_levy = self.env['account.tax'].create({
            'name': 'Tourism levy',
            'amount': 2,
            'company_id': self.company_data['company'].id,
        })
        multi_tax_line_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'quantity': 10,
                    'price_unit': 1000,
                    'tax_ids': [
                        (6, 0, [
                            self.company_data['company'].account_sale_tax_id.id,
                            tourism_levy.id,
                        ]),
                    ],
                    'discount': 25,
                }),
            ],
        })
        multi_tax_line_invoice.action_post()
        generated_messages = multi_tax_line_invoice._l10n_ke_cu_lines_messages()
        expected_sale_line = self.line_dict_to_bytes({
            'name': b'Infinite Improbability Drive        ',
            'price': b'1160',  # This is the unit price, tax included, but only the 16% VAT
            'quantity': b'10.0',
            'discount': b'-25.0%',
        })
        self.assertEqual(generated_messages, [expected_sale_line])

    def test_export_wire_tax_rate_remap(self):
        """ The vat class byte sent to the device is not l10n_ke.item.code's stored tax_rate
            value as-is: it is remapped to the byte KRA actually expects for that category
            (see L10N_KE_WIRE_TAX_RATE), since the stored values predate that mapping and
            don't match it 1:1. This should hold for every stored value, and for lines with
            no item code at all (implying the standard 16% rate).
        """
        test_cases = [
            # (item_code xmlid, tax amount, expected wire vat_class byte, expected vat_rate byte)
            ('l10n_ke.item_code_2023_00391153', 0, b'A', b'0.0'),    # stored 'E' (Exempted) -> wire 'A'
            ('l10n_ke.item_code_2023_00011301', 8, b'E', b'8.0'),    # stored 'B' (Taxable at 8%) -> wire 'E'
            ('l10n_ke.item_code_2023_00011200', 0, b'C', b'0.0'),    # stored 'C' (Zero Rated) -> wire 'C'
            ('l10n_ke.item_code_2023_00016500', 16, b'B', b'16.0'),  # stored 'A' (Taxable at 16%) -> wire 'B'
            ('l10n_ke.item_code_2023_00015400', 0, b'D', b'0.0'),    # stored 'D' (Special Category) -> wire 'D'
            (None, 16, b'B', b'16.0'),                                # no item code (standard rate) -> wire 'B'
        ]
        expected_prices = {0: b'100', 8: b'108', 16: b'116'}
        for xmlid, amount, expected_vat_class, expected_vat_rate in test_cases:
            with self.subTest(xmlid=xmlid):
                item_code = self.env.ref(xmlid) if xmlid else self.env['l10n_ke.item.code']
                tax = self.env['account.tax'].create({
                    'name': f'Test tax {xmlid or "no code"}',
                    'amount': amount,
                    'amount_type': 'percent',
                    'company_id': self.company_data['company'].id,
                    'l10n_ke_item_code_id': item_code.id,
                })
                invoice = self.env['account.move'].create({
                    'move_type': 'out_invoice',
                    'partner_id': self.partner_a.id,
                    'invoice_line_ids': [(0, 0, {
                        'product_id': self.product_a.id,
                        'quantity': 1,
                        'price_unit': 100,
                        'tax_ids': [(6, 0, [tax.id])],
                    })],
                })
                invoice.action_post()
                generated_messages = invoice._l10n_ke_cu_lines_messages()
                expected_sale_line = self.line_dict_to_bytes({
                    'name': b'Infinite Improbability Drive        ',
                    'price': expected_prices[amount],
                    'quantity': b'1.0',
                    # Formatting of item_code/item_desc is covered by the other tests; delegate to the
                    # actual helper here so this test stays focused on the vat_class/vat_rate remap.
                    'item_code': (item_code.code or '').ljust(10).encode('cp1251'),
                    'item_desc': invoice._l10n_ke_fmt(item_code.description, 20),
                    'vat_rate': expected_vat_rate,
                    'vat_class': expected_vat_class,
                })
                self.assertEqual(generated_messages, [expected_sale_line])
