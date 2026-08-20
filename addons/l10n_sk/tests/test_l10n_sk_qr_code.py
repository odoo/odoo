# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (c) 2026 Data Dance s.r.o. (https://www.datadance.eu)
import base64
import binascii
import lzma

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


def decode_pay_by_square(code):
    """ Reverse of ResPartnerBank._l10n_sk_encode_pay_by_square, used to assert
    on the payment data a banking application will read out of the QR-code.
    """
    raw = base64.b32hexdecode(code + '=' * (-len(code) % 8))
    checked_payload = lzma.decompress(raw[4:], format=lzma.FORMAT_RAW, filters=[{
        'id': lzma.FILTER_LZMA1,
        'lc': 3,
        'lp': 0,
        'pb': 2,
        'dict_size': 128 * 1024,
    }])
    checksum, payload = checked_payload[:4], checked_payload[4:]
    assert checksum == binascii.crc32(payload).to_bytes(4, 'little'), "Wrong CRC-32 in the PAY by square code"
    assert int.from_bytes(raw[2:4], 'little') == len(checked_payload), "Wrong payload length in the PAY by square code"
    return payload.decode().split('\t')


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nSKQRCode(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('sk')
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data['company']
        cls.company.qr_code = True
        cls.env.ref('base.EUR').active = True

        cls.sk_bank_account = cls.env['res.partner.bank'].create({
            'account_number': 'SK7283300000009111111118',
            'bank_bic': 'FIOZSKBAXXX',
            'partner_id': cls.company.partner_id.id,
            'allow_out_payment': True,
        })
        cls.foreign_bank_account = cls.env['res.partner.bank'].create({
            'account_number': 'BE15001559627230',
            'partner_id': cls.company.partner_id.id,
            'country_id': cls.env.ref('base.be').id,
        })

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.EUR').id,
            'partner_bank_id': cls.sk_bank_account.id,
            'invoice_date': '2026-01-15',
            'invoice_date_due': '2026-02-14',
            'payment_reference': 'INV/2026/00042',
            'invoice_line_ids': [Command.create({'quantity': 1, 'price_unit': 123.45})],
        })

    def test_l10n_sk_qr_code_detection(self):
        """ PAY by square is picked over the SEPA QR-code for a Slovak account. """
        self.invoice._generate_qr_code()
        self.assertEqual(self.invoice.qr_code_method, 'sk_qr')

        # ... but not for an account located outside of Slovakia.
        foreign_invoice = self.invoice.copy({'partner_bank_id': self.foreign_bank_account.id})
        foreign_invoice._generate_qr_code()
        self.assertEqual(foreign_invoice.qr_code_method, 'sct_qr')

    def test_l10n_sk_qr_code_payment_data(self):
        """ The generated code holds the payment data of the invoice. """
        self.invoice.qr_code_method = 'sk_qr'
        self.assertTrue(self.invoice._generate_qr_code())

        code = self.sk_bank_account.with_context(l10n_sk_qr_due_date=self.invoice.invoice_date_due)._get_qr_vals(
            qr_method='sk_qr',
            amount=self.invoice.amount_residual,
            currency=self.invoice.currency_id,
            debtor_partner=self.invoice.partner_id,
            free_communication=self.invoice.payment_reference,
            structured_communication=self.invoice.payment_reference,
        )
        self.assertEqual(decode_pay_by_square(code), [
            '', '1', '1', '123.45', 'EUR', '20260214',
            '202600042',                    # variable symbol, digits of the payment reference
            '', '', '',
            'INV/2026/00042',               # payment note
            '1', 'SK7283300000009111111118', 'FIOZSKBAXXX', '0', '0',
            self.company.partner_id.name,
            '', '',
        ])

    def test_l10n_sk_qr_code_eligibility(self):
        """ A PAY by square code is only generated for a Slovak IBAN in EUR. """
        self.invoice.qr_code_method = 'sk_qr'
        self.invoice._generate_qr_code()

        self.invoice.currency_id = self.env.ref('base.USD')
        with self.assertRaises(UserError, msg="PAY by square is a SEPA credit transfer, it only carries EUR."):
            self.invoice._generate_qr_code()

        self.invoice.currency_id = self.env.ref('base.EUR')
        self.invoice.partner_bank_id = self.foreign_bank_account
        with self.assertRaises(UserError, msg="PAY by square should not be usable on a foreign bank account."):
            self.invoice._generate_qr_code()
