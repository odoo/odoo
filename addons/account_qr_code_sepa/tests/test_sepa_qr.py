# -*- coding:utf-8 -*-

from odoo.exceptions import UserError
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields

@tagged('post_install', '-at_install')
class TestSEPAQRCode(AccountTestInvoicingCommon):
    """ Tests the generation of Swiss QR-codes on invoices
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].qr_code = True
        cls.acc_sepa_iban = cls.env['res.partner.bank'].create({
            'acc_number': 'BE15001559627230',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.acc_non_sepa_iban = cls.env['res.partner.bank'].create({
            'acc_number': 'SA4420000001234567891234',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.env.ref('base.EUR').active = True

        cls.sepa_qr_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.env.ref('base.EUR').id,
            'partner_bank_id': cls.acc_sepa_iban.id,
            'company_id': cls.company_data['company'].id,
            'invoice_line_ids': [
                (0, 0, {'quantity': 1, 'price_unit': 100})
            ],
        })

    def test_sepa_qr_code_generation(self):
        """ Check different cases of SEPA QR-code generation, when qr_method is
        specified beforehand.
        """
        self.sepa_qr_invoice.qr_code_method = 'sct_qr'

        # Using a SEPA IBAN should work
        self.sepa_qr_invoice._generate_qr_code()

        # Using a non-SEPA IBAN shouldn't
        self.sepa_qr_invoice.partner_bank_id = self.acc_non_sepa_iban
        with self.assertRaises(UserError, msg="It shouldn't be possible to generate a SEPA QR-code for IBAN of countries outside SEPA zone."):
            self.sepa_qr_invoice._generate_qr_code()

        # Changing the currency should break it as well
        self.sepa_qr_invoice.partner_bank_id = self.acc_sepa_iban
        self.sepa_qr_invoice.currency_id = self.env.ref('base.USD').id
        with self.assertRaises(UserError, msg="It shouldn't be possible to generate a SEPA QR-code for another currency as EUR."):
            self.sepa_qr_invoice._generate_qr_code()

    def test_sepa_qr_code_detection(self):
        """ Checks SEPA QR-code auto-detection when no specific QR-method
        is given to the invoice.
        """
        self.sepa_qr_invoice._generate_qr_code()
        self.assertEqual(self.sepa_qr_invoice.qr_code_method, 'sct_qr', "SEPA QR-code generator should have been chosen for this invoice.")

    def test_out_invoice_create_refund_qr_code(self):
        self.sepa_qr_invoice._generate_qr_code()
        self.sepa_qr_invoice.action_post()
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=self.sepa_qr_invoice.ids).create({
            'date': fields.Date.from_string('2019-02-01'),
            'reason': 'no reason',
            'journal_id': self.sepa_qr_invoice.journal_id.id,
        })
        reversal = move_reversal.refund_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertFalse(reverse_move.qr_code_method, "qr_code_method for credit note should be None")

    def test_get_qr_vals_communication(self):
        """ The aim of this test is making sure that we only provide a structured
            reference (or communication) in the qr code values if the communication
            is well-structured. If the communication is not structured, we provide
            it through the unstructured communication value.
        """
        result = self.acc_sepa_iban._get_qr_vals(
            qr_method='sct_qr',
            amount=100.0,
            currency=self.env.ref('base.EUR'),
            debtor_partner=None,
            free_communication='A free communication',
            structured_communication='A free communication',
        )
        self.assertEqual(
            result,
            [
                'BCD',
                '002',
                '1',
                'SCT',
                '',
                'company_1_data',
                'BE15001559627230',
                'EUR100.0',
                '',
                '',
                'A free communication',
                '',
            ]
        )

        result = self.acc_sepa_iban._get_qr_vals(
            qr_method='sct_qr',
            amount=100.0,
            currency=self.env.ref('base.EUR'),
            debtor_partner=None,
            free_communication=' 5 000 0567 89012345 ',  # NL Structured reference
            structured_communication=' 5 000 0567 89012345 ',  # NL Structured reference
        )
        self.assertEqual(
            result,
            [
                'BCD',
                '002',
                '1',
                'SCT',
                '',
                'company_1_data',
                'BE15001559627230',
                'EUR100.0',
                '',
                '5000056789012345',
                '',
                '',
            ]
        )
