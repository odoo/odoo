import re

from odoo.exceptions import UserError
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCZKQRCode(AccountTestInvoicingCommon):
    """Tests the generation of Czech CZK QR-codes on invoices."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].qr_code = True
        cls.env.ref('base.EUR').active = True
        cls.env.ref('base.CZK').active = True

        cls.acc_czk_iban = cls.env['res.partner.bank'].create({
            'account_number': 'CZ6508000000192000145399',
            'partner_id': cls.company_data['company'].partner_id.id,
            'allow_out_payment': True,
        })

        cls.czk_qr_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.CZK').id,
            'partner_bank_id': cls.acc_czk_iban.id,
            'company_id': cls.company_data['company'].id,
            'invoice_date_due': fields.Date.today(),
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 100}),
            ],
        })

    def test_czk_qr_code_generation(self):
        """Check different cases of CZK QR-code generation."""
        self.czk_qr_invoice.qr_code_method = 'czk_qr'

        # Using a valid CZK IBAN should work.
        self.czk_qr_invoice._generate_qr_code()

        # Using a non-CZK currency shouldn't work.
        self.czk_qr_invoice.currency_id = self.env.ref('base.EUR')
        with self.assertRaises(UserError):
            self.czk_qr_invoice._generate_qr_code()

        # Restore CZK currency.
        self.czk_qr_invoice.currency_id = self.env.ref('base.CZK')

        # Using a non-IBAN account shouldn't work.
        self.czk_qr_invoice.partner_bank_id = self.env['res.partner.bank'].create({
            'account_number': '123456789',
            'partner_id': self.company_data['company'].partner_id.id,
            'allow_out_payment': True,
        })

        with self.assertRaises(UserError):
            self.czk_qr_invoice._generate_qr_code()

    def test_czk_qr_code_detection(self):
        """Check automatic detection of the CZK QR-code method."""
        self.czk_qr_invoice._generate_qr_code()

        self.assertEqual(
            self.czk_qr_invoice.qr_code_method,
            'czk_qr',
            "CZK QR-code generator should have been chosen for this invoice.",
        )

    def test_czk_qr_vals(self):
        """Check the values generated for a CZK QR-code."""
        self.czk_qr_invoice.action_post()

        result = self.acc_czk_iban._get_qr_vals(
            qr_method='czk_qr',
            amount=100.0,
            currency=self.env.ref('base.CZK'),
            debtor_partner=None,
            free_communication=self.czk_qr_invoice.name,
            structured_communication=None,
        )

        expected = (
            'SPD*1.0*'
            'ACC:CZ6508000000192000145399*'
            'AM:100.0*'
            'CC:CZK*'
            f'DT:{fields.Date.today().strftime('%Y%m%d')}*'
            f'MSG:{self.czk_qr_invoice.name[:60]}*'
            f'RN:{self.acc_czk_iban.holder_name or self.acc_czk_iban.partner_id.name}'
            f'*PT:IP*'
            f'X-VS:{re.sub(r'\D+', '', self.czk_qr_invoice.name)}*'
        )

        self.assertEqual(result, expected)
