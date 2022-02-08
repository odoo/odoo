# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import Form, common, tagged
from odoo.exceptions import ValidationError


CH_ISR_SUBSCRIPTION = "01-162-8"
CH_POSTAL = "10-8060-7"
CH_IBAN = "CH15 3881 5158 3845 3843 7"
ISR_REFERENCE_GOOD = "16 00011 23456 78901 23456 78901"
ISR_REFERENCE_ZEROS = "00 00000 00000 00001 23456 78903"
ISR_REFERENCE_NO_ZEROS = "1 23456 78903"
ISR_REFERENCE_BAD = "11 11111 11111 11111 11111 11111"


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestVendorBillISR(common.TransactionCase):
    """Check we can encode Vendor bills with ISR references

    The ISR is a structured reference with a checksum.
    User are guided to ensure they don't encode wrong ISR references.
    Only vendors with ISR issuer accounts send ISR references.

    ISR references can be received at least till 2022.

    """

    @classmethod
    def setUpClass(cls):
        super(TestVendorBillISR, cls).setUpClass()
        cls.abs_bank = cls.env["res.bank"].create(
            {"name": "Alternative Bank Schweiz", "bic": "ABSOCH22XXX"}
        )
        cls.supplier1 = cls.env["res.partner"].create({"name": "Supplier ISR"})
        cls.supplier2 = cls.env["res.partner"].create({"name": "Supplier postal"})
        cls.supplier3 = cls.env["res.partner"].create({"name": "Supplier IBAN"})

        cls.bank_acc_isr = cls.env['res.partner.bank'].create({
            "acc_number": "ISR 01-162-8 Supplier ISR",
            "partner_id": cls.supplier1.id,
            "l10n_ch_postal": CH_ISR_SUBSCRIPTION,
        })
        cls.bank_acc_postal = cls.env['res.partner.bank'].create({
            "acc_number": CH_POSTAL,
            "partner_id": cls.supplier2.id,
            "l10n_ch_postal": CH_POSTAL,
        })
        cls.bank_acc_iban = cls.env['res.partner.bank'].create({
            "acc_number": CH_IBAN,
            "partner_id": cls.supplier2.id,
            "l10n_ch_postal": False,
        })

    def test_isr_ref(self):
        """Enter ISR reference with ISR subscription account number

        The vendor bill can be saved.
        """
        self.env.company.country_id = self.env.ref('base.ch')
        form = Form(self.env["account.move"].with_context(
            default_move_type="in_invoice"), view="l10n_ch.isr_invoice_form")
        form.partner_id = self.supplier1
        form.partner_bank_id = self.bank_acc_isr

        form.payment_reference = ISR_REFERENCE_GOOD
        invoice = form.save()

        self.assertFalse(invoice.l10n_ch_isr_needs_fixing)

    def test_isr_ref_with_zeros(self):
        """Enter ISR reference with ISR subscription account number

        An ISR Reference can have lots of zeros on the left.

        The vendor bill can be saved.
        """
        self.env.company.country_id = self.env.ref('base.ch')
        form = Form(self.env["account.move"].with_context(
            default_move_type="in_invoice"), view="l10n_ch.isr_invoice_form")
        form.partner_id = self.supplier1
        form.partner_bank_id = self.bank_acc_isr

        form.payment_reference = ISR_REFERENCE_ZEROS
        invoice = form.save()

        self.assertFalse(invoice.l10n_ch_isr_needs_fixing)

    def test_isr_ref_no_zeros(self):
        """Enter ISR reference with ISR subscription account number

        An ISR Reference full of zeros can be entered starting by the
        first non zero digit.

        The vendor bill can be saved.
        """
        self.env.company.country_id = self.env.ref('base.ch')
        form = Form(self.env["account.move"].with_context(
            default_move_type="in_invoice"), view="l10n_ch.isr_invoice_form")
        form.partner_id = self.supplier1
        form.partner_bank_id = self.bank_acc_isr

        form.payment_reference = ISR_REFERENCE_NO_ZEROS
        invoice = form.save()

        self.assertFalse(invoice.l10n_ch_isr_needs_fixing)

    def test_isr_wrong_ref(self):
        """Mistype ISR reference with ISR subscription account number
        Check it will show the warning
        """
        self.env.company.country_id = self.env.ref('base.ch')
        form = Form(self.env["account.move"].with_context(
            default_move_type="in_invoice"), view="l10n_ch.isr_invoice_form")
        form.partner_id = self.supplier1
        form.partner_bank_id = self.bank_acc_isr

        form.payment_reference = ISR_REFERENCE_BAD
        invoice = form.save()

        self.assertTrue(invoice.l10n_ch_isr_needs_fixing)
