from odoo import Command
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
            'acc_number': 'FR7630004028379876543210943',
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

    def test_export_invoice_partner_fr_tax_unit(self):
        """
        Under French Single Taxpayer Group rules (Assujetti Unique, CGI art. 256 C):
        - BT-29 (Seller identifier): The Single Taxpayer Group's 9-digit SIREN must appear
          under ram:GlobalID with schemeID "0231" (BR-FR-32).
        - BT-21/BT-22: Mandatory note #TXD#MEMBRE_ASSUJETTI_UNIQUE must appear (BR-FR-CO-14).
        - BG-11 (Tax Representative): ram:SellerTaxRepresentativeTradeParty must be present and contain
          the Single Taxpayer Group's VAT under BT-63 (BR-FR-CO-15), along with name (BT-62)
          and postal address (BG-12).
        - BT-31: The member company's own VAT remains under ram:SellerTradeParty.
        """
        self.ensure_installed('account_reports')
        other_company = self.env['res.company'].create({
            'name': 'Company 2',
            'country_id': self.env.ref('base.fr').id,
            'currency_id': self.env.company.currency_id.id,
        })
        self.env['account.tax.unit'].create({  # noqa: OLS03001
            'name': 'company_1_data',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR05677404089',
            'company_ids': [Command.set((self.env.company + other_company).ids)],
            'main_company_id': self.env.company.id,
        })

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
        self._assert_invoice_ubl_file(invoice, 'facturx_fr_out_invoice_tax_unit')

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

    def test_export_downpayments_partner_fr(self):
        self.product_b.taxes_id = self.percent_tax(20.0).ids
        order = self._create_sale_order()
        order.order_line[1].product_uom_qty = 2
        downpayment_pct = 20
        payment_ctx = {
            "active_model": "sale.order",
            "active_ids": [order.id],
            "active_id": order.id,
        }
        wizard = (
            self.env["sale.advance.payment.inv"]
                .with_context(**payment_ctx)
                .create({
                    'advance_payment_method': 'percentage',
                    'amount': downpayment_pct,
                })
        )
        wizard.sudo().create_invoices()
        downpayment_invoice = order.invoice_ids
        downpayment_invoice.narration = "Test narration"
        downpayment_invoice.action_post()
        self._send_patched(downpayment_invoice)
        self._assert_invoice_ubl_file(downpayment_invoice, "facturx_fr_out_downpayment_invoice")

        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((downpayment_invoice.id,))],
                'date': self.fakenow.date(),
                'journal_id': downpayment_invoice.journal_id.id,
            }
        ).reverse_moves()
        downpayment_credit_note = downpayment_invoice.reversal_move_ids
        downpayment_credit_note.invoice_line_ids[0].price_unit = 100.0
        downpayment_credit_note.invoice_line_ids[1].price_unit = 40.0
        downpayment_credit_note.narration = "Test narration"
        downpayment_credit_note.action_post()
        self._send_patched(downpayment_credit_note)
        self._assert_invoice_ubl_file(downpayment_credit_note, "facturx_fr_out_downpayment_credit_note")

        wizard = (
            self.env["sale.advance.payment.inv"]
                .with_context(**payment_ctx)
                .create({
                    'advance_payment_method': 'delivered',
                })
        )
        wizard.sudo().create_invoices()
        final_invoice = order.invoice_ids.filtered(
            lambda m: m.id not in downpayment_invoice.ids + downpayment_credit_note.ids
        )
        final_invoice.narration = "Test narration"
        final_invoice.action_post()
        self._send_patched(final_invoice)
        self._assert_invoice_ubl_file(final_invoice, "facturx_fr_out_final_invoice")
