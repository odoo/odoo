# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form


class TestGenISRReference(common.SavepointCase):
    """Check condition of generation of and content of the structured ref

    Add tests for ISR-B

    """
    # FIXME To merge with l10n_ch/tests/test_gen_isr_reference.py

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

    def test_isr_b(self):
        self.bank_acc.l10n_ch_isrb_id_number = "123456"
        inv_form = self.new_form()
        inv_form.invoice_partner_bank_id = self.bank_acc
        invoice = inv_form.save()

        invoice.name = "INV/01234567890"

        expected_isr = "123456000000000012345678908"
        expected_optical_line = (
            "0100000494004>123456000000000012345678908+ 010001628>"
        )
        self.assertEqual(invoice.l10n_ch_isr_number, expected_isr)
        self.assertEqual(invoice.l10n_ch_isr_optical_line, expected_optical_line)

    def test_isr_b_small_customer_id(self):
        self.bank_acc.l10n_ch_isrb_id_number = "123"
        inv_form = self.new_form()
        inv_form.invoice_partner_bank_id = self.bank_acc
        invoice = inv_form.save()

        invoice.name = "INV/01234567890"

        expected_isr = "000123000000000012345678905"
        expected_optical_line = (
            "0100000494004>000123000000000012345678905+ 010001628>"
        )
        self.assertEqual(invoice.l10n_ch_isr_number, expected_isr)
        self.assertEqual(invoice.l10n_ch_isr_optical_line, expected_optical_line)

    def test_isr_b_long_reference(self):
        self.bank_acc.l10n_ch_isrb_id_number = "666666"
        inv_form = self.new_form()
        inv_form.invoice_partner_bank_id = self.bank_acc
        invoice = inv_form.save()

        invoice.name = "INV/123456789012345678901234567890"

        expected_isr = "666666123456789012345678900"
        expected_optical_line = (
            "0100000494004>666666123456789012345678900+ 010001628>"
        )
        self.assertEqual(invoice.l10n_ch_isr_number, expected_isr)
        self.assertEqual(invoice.l10n_ch_isr_optical_line, expected_optical_line)
