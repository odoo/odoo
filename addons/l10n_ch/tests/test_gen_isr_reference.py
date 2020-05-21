# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form


class TestGenISRReference(common.SavepointCase):
    """Check condition of generation of and content of the structured ref"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.partner = cls.env.ref("base.res_partner_12")
        cls.bank = cls.env["res.bank"].create(
            {
                "name": "Alternative Bank Schweiz AG",
                "bic": "ALSWCH21XXX",
            }
        )
        cls.bank_acc = cls.env["res.partner.bank"].create(
            {
                "acc_number": "ISR",
                "l10n_ch_isr_subscription_chf": "01-162-8",
                "bank_id": cls.bank.id,
                "partner_id": cls.partner.id,
            }
        )

    def new_form(self):
        inv = Form(self.env["account.move"].with_context(
            default_type="out_invoice")
        )
        inv.partner_id = self.partner
        inv.currency_id = self.env.ref("base.CHF")
        with inv.invoice_line_ids.new() as line:
            line.name = "Fondue Party"
            line.price_unit = 494.
        return inv

    def test_isr(self):
        inv_form = self.new_form()
        inv_form.invoice_partner_bank_id = self.bank_acc
        invoice = inv_form.save()

        invoice.name = "INV/01234567890"

        expected_isr = "000000000000000012345678903"
        expected_optical_line = (
            "0100000494004>000000000000000012345678903+ 010001628>"
        )
        self.assertEqual(invoice.l10n_ch_isr_number, expected_isr)
        self.assertEqual(invoice.l10n_ch_isr_optical_line, expected_optical_line)

    def test_isr_long_reference(self):
        inv_form = self.new_form()
        inv_form.invoice_partner_bank_id = self.bank_acc
        invoice = inv_form.save()

        invoice.name = "INV/123456789012345678901234567890"

        expected_isr = "567890123456789012345678901"
        expected_optical_line = (
            "0100000494004>567890123456789012345678901+ 010001628>"
        )
        self.assertEqual(invoice.l10n_ch_isr_number, expected_isr)
        self.assertEqual(invoice.l10n_ch_isr_optical_line, expected_optical_line)

    def test_missing_isr_subscription_num(self):
        self.bank_acc.l10n_ch_isr_subscription_chf = False

        inv_form = self.new_form()
        inv_form.invoice_partner_bank_id = self.bank_acc
        invoice = inv_form.save()
        self.assertFalse(invoice.l10n_ch_isr_number)
        self.assertFalse(invoice.l10n_ch_isr_optical_line)

    def test_no_bank_account(self):
        inv_form = self.new_form()
        inv_form.invoice_partner_bank_id = self.env["res.partner.bank"]
        invoice = inv_form.save()

        self.assertFalse(invoice.l10n_ch_isr_number)
        self.assertFalse(invoice.l10n_ch_isr_optical_line)

    def test_wrong_currency(self):
        inv_form = self.new_form()
        inv_form.invoice_partner_bank_id = self.bank_acc
        inv_form.currency_id = self.env.ref("base.BTN")
        invoice = inv_form.save()

        self.assertFalse(invoice.l10n_ch_isr_number)
        self.assertFalse(invoice.l10n_ch_isr_optical_line)
