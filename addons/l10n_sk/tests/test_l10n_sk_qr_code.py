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
        """ PAY by square is the method picked for a Slovak account. """
        self.invoice._generate_qr_code()
        self.assertEqual(self.invoice.qr_code_method, 'sk_qr')

        # ... but not for an account located outside of Slovakia, where whichever
        # other method is available gets its turn.
        foreign_invoice = self.invoice.copy({'partner_bank_id': self.foreign_bank_account.id})
        foreign_invoice._generate_qr_code()
        self.assertNotEqual(foreign_invoice.qr_code_method, 'sk_qr')

    def test_l10n_sk_encode_pay_by_square(self):
        """ The encoding matches the codes a reference implementation produces.

        Data models and their expected codes come from the published test vectors
        of the `pay-by-square` package (https://pypi.org/project/pay-by-square/),
        which is an independent implementation of the specification.
        """
        iban = 'SK7700000000000000000000'
        for payment_data, expected_code in [
            # amount, IBAN and due date only
            (f'\t1\t1\t1.00\tEUR\t20200705\t\t\t\t\t\t1\t{iban}\t\t0\t0\t\t\t',
             '000440007S3VT0DFSETNDU5J8KF4EI1MT7B3BBH3P91D830QDBA6IRPF97451V4U'
             '11PHMI423IDK7VVU5P800'),
            # ... with a BIC
            (f'\t1\t1\t1.00\tEUR\t20200705\t\t\t\t\t\t1\t{iban}\tFIOZSKBAXXX\t0\t0\t\t\t',
             '0004Q000DS03UHKLF59M2IK7FUCM3SBUK5FM62CCKLR4QOKAJSBPPL4ND4R66LSI'
             '1K92GURM0FH5E3DASNBTNAKASV94PB5VVU1BRO00'),
            # ... with the variable, constant and specific symbols
            (f'\t1\t1\t1.00\tEUR\t20200705\t11\t22\t33\t\t\t1\t{iban}\t\t0\t0\t\t\t',
             '0004G000EIUCQ7TO82O7GRAEMT06773UPLKOEC76BV3NBBNP7HPVSSJHUNVFBD7G'
             '6DAAMTDL4B8ND4D06QCNS7PHMPBVVVROGU000'),
            # ... with a beneficiary name
            (f'\t1\t1\t1.00\tEUR\t20200705\t11\t22\t33\t\t\t1\t{iban}\t\t0\t0\tFoo\t\t',
             '0004M0006MISSBD0SBV1135OEDE05KA7IM2GBI0U0M5LHD5LIEP7D9CJO6T8GQDF'
             'UKCL7TOEGN8TDOVAJ2GL85IOEA8OV3O1AQOFVU3JKS00'),
            # ... and with every field the invoicing code can fill in
            (f'\t1\t1\t1.00\tEUR\t20200705\t11\t22\t33\t\tmoney\t1\t{iban}\tFIOZSKBAXXX\t0\t0\tFoo\taddress 1\taddress 2',
             '0006Q0006GO7VIPNP2PPLDV1MO04PTB6C4OSM4KU3JKSDNJLJ0GBAT9GTI9DD7MF'
             'QKGMLI4RD7996S1K78MKT8S0F46HK5TF6A6GP881BBMM66JVFMBBSM9KQRM2TN2V'
             'RABUV7KFD22BFFIVVTFKO000'),
        ]:
            with self.subTest(payment_data=payment_data):
                self.assertEqual(
                    self.sk_bank_account._l10n_sk_encode_pay_by_square(payment_data),
                    expected_code,
                )

    def test_l10n_sk_qr_code_payment_data(self):
        """ The generated code holds the payment data of the invoice. """
        self.invoice.qr_code_method = 'sk_qr'
        self.assertTrue(self.invoice._generate_qr_code())

        code = self.sk_bank_account.with_context(invoice_date_due=self.invoice.invoice_date_due)._get_qr_vals(
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

        # PaymentDueDate is optional, and stays empty outside of an invoice.
        code = self.sk_bank_account._get_qr_vals(
            qr_method='sk_qr',
            amount=self.invoice.amount_residual,
            currency=self.invoice.currency_id,
            debtor_partner=self.invoice.partner_id,
            free_communication=self.invoice.payment_reference,
            structured_communication=self.invoice.payment_reference,
        )
        self.assertEqual(decode_pay_by_square(code)[5], '')

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
