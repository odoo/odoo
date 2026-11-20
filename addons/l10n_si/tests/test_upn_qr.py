import base64
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tools.image import binary_to_image

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_si.models.res_partner_bank import ResPartnerBank


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nSiUpnQr(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('si')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.company.write({
            'name': "Združenje bank Slovenije",
            'street': "Šubičeva 2",
            'zip': '1000',
            'city': "Ljubljana",
            'qr_code': True,
        })
        cls.si_bank_account = cls.env['res.partner.bank'].create({
            'account_number': 'SI56 0510 0801 0486 080',
            'partner_id': cls.company.partner_id.id,
            'allow_out_payment': True,
        })
        cls.si_customer = cls.env['res.partner'].create({
            'name': "Novo podjetje d.o.o.",
            'street': "Lepa cesta 15",
            'zip': '3698',
            'city': "Loški Potok",
            'country_id': cls.env.ref('base.si').id,
        })
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.si_customer.id,
            'partner_bank_id': cls.si_bank_account.id,
            'invoice_date': '2026-11-16',
            'invoice_date_due': '2026-12-16',
            'invoice_line_ids': [Command.create({'name': "Consulting", 'price_unit': 1280.67, 'tax_ids': []})],
        })
        cls.invoice.action_post()
        cls.invoice.payment_reference = 'SI01 315-26-101'

    def _get_upn_qr_fields(self, invoice):
        """ The fields of the UPN QR code of an invoice, read from the content
        the printed code is drawn from.
        """
        with patch.object(
            ResPartnerBank, '_l10n_si_render_upn_qr',
            autospec=True, side_effect=ResPartnerBank._l10n_si_render_upn_qr,
        ) as render:
            self.assertTrue(invoice._generate_qr_code())
        content = render.call_args.args[1]
        self.assertEqual(content[-1], '\n', "Every field ends with a line feed, the last one included.")
        return content[:-1].split('\n')

    def test_upn_qr_content(self):
        self.assertEqual(self._get_upn_qr_fields(self.invoice), [
            'UPNQR',                        # 1. Leading style
            '',                             # 2. Payer's IBAN
            '',                             # 3. Deposit
            '',                             # 4. Withdrawal
            '',                             # 5. Payer's reference
            "Novo podjetje d.o.o.",         # 6. Payer's name
            "Lepa cesta 15",                # 7. Payer's street
            "3698 Loški Potok",             # 8. Payer's city
            '00000128067',                  # 9. Amount, in cents
            '',                             # 10. Payment date
            '',                             # 11. Urgent
            'GDSV',                         # 12. Purpose code
            'INV/2026/00001',               # 13. Payment purpose: the invoice number
            '16.12.2026',                   # 14. Payment deadline
            'SI56051008010486080',          # 15. Recipient's IBAN
            'SI01315-26-101',               # 16. Recipient's reference, without spaces
            "Združenje bank Slovenije",     # 17. Recipient's name
            "Šubičeva 2",                   # 18. Recipient's street
            "1000 Ljubljana",               # 19. Recipient's city
            '193',                          # 20. Length of fields 1 to 19, line feeds included
        ])

    def test_upn_qr_image(self):
        """ The code is drawn in full size (77 modules of 10 pixels) with its
        white margin of 4 modules, and nothing covers it on the invoice.
        """
        data_uri = self.invoice._generate_qr_code()
        image = binary_to_image(base64.b64decode(data_uri.split(',')[1])).convert('L')
        self.assertEqual(image.size, (850, 850))
        self.assertEqual(image.crop((0, 0, 850, 40)).getextrema(), (255, 255), "The margin is white.")
        self.assertEqual(image.getpixel((40, 40)), 0, "The code starts right after the margin.")

        report = self.env['ir.actions.report']._render_qweb_html('account.account_invoices', self.invoice.ids)[0].decode()
        self.assertIn('width: 45mm', report)
        self.assertNotIn('qrcode_odoo_logo', report)

    def test_upn_qr_reference(self):
        """ A valid SI01 or RF reference goes in the reference field, else the
        "no reference" model SI99 does, and the text becomes the payment purpose.
        """
        for payment_reference, expected_reference, expected_purpose in (
            ('SI01 315-26-101', 'SI01315-26-101', 'INV/2026/00001'),
            ('RF18 5390 0754 7034', 'RF18539007547034', 'INV/2026/00001'),
            ('SI01 315-26-102', 'SI99', 'SI01 315-26-102'),  # Wrong check digit
            ('SI00 225268-32526-222', 'SI99', 'SI00 225268-32526-222'),  # Only SI01 is recognized
            ('Order 42 – November', 'SI99', 'Order 42 - November'),
        ):
            with self.subTest(payment_reference=payment_reference):
                self.invoice.payment_reference = payment_reference
                fields = self._get_upn_qr_fields(self.invoice)
                self.assertEqual((fields[15], fields[12]), (expected_reference, expected_purpose))

    def test_upn_qr_text_fields(self):
        """ Texts are cut to the length the standard allows, their characters
        replaced when ISO 8859-2 lacks them, and missing addresses give empty lines.
        """
        self.si_customer.write({
            'name': "Ørsted Østergaard — Energija za prihodnost d.o.o.",
            'street': False,
            'zip': False,
            'city': False,
        })
        self.invoice.payment_reference = "Order 42 for “Ljubljana” office … to pay in €, by the end of the year"
        fields = self._get_upn_qr_fields(self.invoice)
        self.assertEqual(fields[5:8], ["?rsted ?stergaard - Energija za p", '', ''])
        self.assertEqual(fields[12], 'Order 42 for "Ljubljana" office ... to pay')

    def test_upn_qr_purpose_code(self):
        self.assertTrue(self.invoice.l10n_si_show_upn_qr_purpose_code)
        self.invoice.l10n_si_upn_qr_purpose_code = 'RENT'
        self.assertEqual(self._get_upn_qr_fields(self.invoice)[11], 'RENT')

    def test_upn_qr_applicability(self):
        """ UPN QR replaces the SEPA QR code for Slovenian customers paying in EUR
        to a Slovenian account. Otherwise, SEPA keeps its place, if it applies.
        """
        self.assertEqual(self.invoice._get_qr_code_method(), 'si_upn_qr')

        be_customer = self.env['res.partner'].create({'name': "Belgian customer", 'country_id': self.env.ref('base.be').id})
        be_bank_account = self.env['res.partner.bank'].create({
            'account_number': 'BE15001559627230',
            'partner_id': self.company.partner_id.id,
        })
        usd = self.setup_other_currency('USD')
        for case, values, expected_method in (
            ("Foreign customer", {'partner_id': be_customer.id}, 'sct_qr'),
            ("Foreign bank account", {'partner_bank_id': be_bank_account.id}, 'sct_qr'),
            ("Foreign currency", {'currency_id': usd.id}, None),
        ):
            with self.subTest(case=case):
                invoice = self.invoice.copy(values)
                self.assertEqual(invoice._get_qr_code_method(), expected_method)
                self.assertFalse(invoice.l10n_si_show_upn_qr_purpose_code)

    def test_upn_qr_without_invoice(self):
        """ Payment QR codes made outside of an invoice (e.g. for a wire transfer
        on the portal) lack the invoice's data, and still make a valid UPN QR code.
        """
        content = self.si_bank_account.build_qr_code_value(
            100.0, "Order 42", None, self.env.ref('base.EUR'), self.si_customer, qr_method='si_upn_qr',
        )
        fields = content[:-1].split('\n')
        self.assertEqual((fields[11], fields[12], fields[13], fields[15]), ('GDSV', "Order 42", '', 'SI99'))
