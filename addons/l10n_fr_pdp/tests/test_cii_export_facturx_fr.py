from odoo.tests import tagged

from .common import TestL10nFrPdpCommon

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPdpXmlCii(TestL10nFrPdpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.startClassPatcher(freeze_time('2026-01-01 10:00:00'))
        cls.partner_a.invoice_edi_format = 'facturx'
        cls.company_data['company'].email = 'my_company@test.com'
        cls.recipient_bank = cls.env['res.partner.bank'].create({
            'account_number': 'FR7630004028379876543210943',
            'partner_id': cls.partner_fr.id,
            'allow_out_payment': True,
        })

    @classmethod
    def subfolders(cls):
        return 'facturx', 'invoice', 'fr'

    def test_invoice_narration(self):
        tax_20 = self.percent_tax(20.0)

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_a,
            product_id=self.product,
            tax_ids=tax_20,
            partner_bank_id=self.recipient_bank,
            narration="Test narration",
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_narration')

        early_payment_term = self._create_early_payment_term()
        invoice = self._create_invoice_one_line(
            partner_id=self.partner_a,
            invoice_payment_term_id=early_payment_term.id,
            product_id=self.product,
            tax_ids=tax_20,
            partner_bank_id=self.recipient_bank,
            narration="Test narration",
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_narration_early_payment_discount')

    def test_invoice_profile_id(self):
        tax_goods = self.percent_tax(20.0, tax_scope='consu')
        tax_services = self.percent_tax(20.0, tax_scope='service')

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_a,
            product_id=self.product,
            tax_ids=tax_goods,
            partner_bank_id=self.recipient_bank,
            narration="Test narration",
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_profile_id_goods')

        invoice = self._create_invoice_one_line(
            partner_id=self.partner_a,
            product_id=self.product,
            tax_ids=tax_services,
            partner_bank_id=self.recipient_bank,
            narration="Test narration",
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_profile_id_services')

        invoice = self._create_invoice(
            partner_id=self.partner_a,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=100.0,
                    tax_ids=tax_goods,
                ),
                self._prepare_invoice_line(
                    price_unit=100.0,
                    tax_ids=tax_services,
                ),
            ],
            partner_bank_id=self.recipient_bank,
            narration="Test narration",
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_invoice_profile_id_mixed')
