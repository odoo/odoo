# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import time

from odoo import tools
from odoo.exceptions import ValidationError
from odoo.modules.module import get_resource_path
from odoo.tests import Form, common


CH_ISR_SUBSCRIPTION = "01-162-8"  # partner ISR subsr num we register under postal
CH_POSTAL = "10-8060-7"
CH_IBAN = "CH15 3881 5158 3845 3843 7"


class TestPartnerBankISR(common.SavepointCase):
    """Test creation of partner bank account with l10n_ch fields"""

    def setUpClass(cls):
        super().setUpClass()
        cls.abs_bank = cls.env["res.bank"].create(
            {"name": "Alternative Bank Schweiz", "bic": "ABSOCH22XXX"}
        )
        cls.supplier1 = cls.env["res.partner"].create({"name": "Supplier ISR 1"})
        cls.supplier2 = cls.env["res.partner"].create({"name": "Supplier ISR 2"})

    def test_create_supplier_bank_isr_issuer(self):
        """Create ISR issuer account with `01-xxxx-x` number

        Create 2 to check for ISR-B that there is no unique constraint
        """
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING1"  # required but not used
        form.partner_id = self.supplier1
        form.bank_id = self.abs_bank

        form.l10n_ch_postal = CH_ISR_SUBSCRIPTION
        bank_acc = form.save()

        self.assertTrue(bank_acc)

        # the same ISR Subscription number can be used by an other
        # supplier
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING2"  # required but not used
        form.partner_id = self.supplier2
        form.bank_id = self.abs_bank

        form.l10n_ch_postal = CH_ISR_SUBSCRIPTION
        bank_acc = form.save()

        self.assertTrue(bank_acc)

    def test_create_supplier_bank_postal(self):
        """Create standard postal account with `10-xxxx-x` number"""
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING"  # required but not used
        form.partner_id = self.supplier1

        form.l10n_ch_postal = CH_POSTAL
        bank_acc = form.save()

        self.assertFalse(bank_acc.is_isr_issuer())

    def test_create_supplier_bank_wrong_checksum(self):
        """Postal account number is checked with checksum"""
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING"  # required but not used
        form.partner_id = self.supplier1

        with self.assertRaises(ValidationError):
            form.l10n_ch_postal = CH_POSTAL[:-1] + "1"
            form.save()

    def test_create_supplier_bank_wrong_format(self):
        """Postal account number is checked with checksum"""
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING"  # required but not used
        form.partner_id = self.supplier1

        with self.assertRaises(ValidationError):
            form.l10n_ch_postal = "12345"
            form.save()

    def test_create_my_company_isr_issuer(self):
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING"  # required
        form.partner_id = self.env.user.company_id.partner_id
        form.bank_id = self.abs_bank

        form.l10n_ch_isr_subscription_chf = CH_ISR_SUBSCRIPTION
        bank_acc = form.save()

        self.assertFalse(bank_acc.is_isr_issuer())

    def test_create_my_company_isr_issuer_wrong_postal(self):
        """A standard postal account is not valid
        as an ISR issuer"""
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING"  # required
        form.partner_id = self.env.user.company_id.partner_id

        with self.assertRaises(ValidationError):
            # postal != ISR subscription number
            form.l10n_ch_isr_subscription_chf = CH_POSTAL
            form.save()

    def test_create_my_company_isr_issuer_wrong_checksum(self):
        """A standard postal account is not valid
        as an ISR issuer"""
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING"  # required
        form.partner_id = self.env.user.company_id.partner_id

        with self.assertRaises(ValidationError):
            # postal != ISR subscription number
            form.l10n_ch_isr_subscription_chf = CH_ISR_SUBSCRIPTION[:-1] + '0'
            form.save()

    def test_create_my_company_isr_issuer_wrong_format(self):
        """Not 01-xxxx-y format"""
        form = Form(self.env['res.partner.bank'])
        form.acc_number = "FILLING"  # required
        form.partner_id = self.env.user.company_id.partner_id
        with self.assertRaises(ValidationError):
            form.l10n_ch_isr_subscription_chf = "01234"
            form.save()
