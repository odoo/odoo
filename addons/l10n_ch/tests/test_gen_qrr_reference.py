# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged

QR_IBAN = 'CH21 3080 8001 2345 6782 7'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestGenQRRReference(AccountTestInvoicingCommon):
    """Check condition of generation of and content of the structured ref"""

    @classmethod
    def setUpClass(cls, chart_template_ref="ch"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.bank = cls.env["res.bank"].create(
            {
                "name": "Alternative Bank Schweiz AG",
                "bic": "ALSWCH21XXX",
            }
        )
        cls.partner = cls.env['res.partner'].create({
            'name': 'Bobby',
            'country_id': cls.env.ref('base.ch').id,
        })
        cls.bank_acc_qriban = cls.env["res.partner.bank"].create(
            {
                "acc_number": QR_IBAN,
                "bank_id": cls.bank.id,
                "partner_id": cls.partner.id,
            }
        )
        cls.qr_bank_account = cls.env['res.partner.bank'].create({
            'acc_number': "CH4431999123000889012",
            'partner_id': cls.partner.id,
        })

        cls.invoice = cls.init_invoice("out_invoice", products=cls.product_a+cls.product_b)

    def test_qrr(self):
        test_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'partner_bank_id': self.bank_acc_qriban.id,
            'currency_id': self.env.ref('base.EUR').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        test_invoice.name = "INV/01234567890"
        expected_qrr = "000000000000000012345678903"
        self.assertEqual(test_invoice.get_l10n_ch_qrr_number(), expected_qrr)

    def test_qrr_long_reference(self):
        test_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'partner_bank_id': self.bank_acc_qriban.id,
            'currency_id': self.env.ref('base.EUR').id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {'product_id': self.product_a.id})],
        })
        test_invoice.name = "INV/123456789012345678901234567890"
        expected_qrr = "567890123456789012345678901"
        self.assertEqual(test_invoice.get_l10n_ch_qrr_number(), expected_qrr)

    def test_no_bank_account(self):
        self.invoice.partner_bank_id = False
        self.assertFalse(self.invoice.get_l10n_ch_qrr_number())

    def test_wrong_currency(self):
        self.invoice.partner_bank_id = self.bank_acc_qriban
        self.invoice.currency_id = self.env.ref("base.BTN")
        self.assertFalse(self.invoice.get_l10n_ch_qrr_number())
