from odoo import Command
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiBECommon

from odoo.tests import tagged

from lxml import etree

NS_MAP = {
    'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
    'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
}


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblExportBis3SelfInvoiceBE(TestUblBis3Common, TestUblCiiBECommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.self_billing_journal = cls.env['account.journal'].create({
            'name': 'Self Billing',
            'code': 'SB',
            'type': 'purchase',
            'is_self_billing': True,
        })

    @classmethod
    def subfolders(cls):
        subfolder_format, _subfolder_document, subfolder_country = super().subfolders()
        return subfolder_format, 'self_invoice', subfolder_country

    def test_export_selfbilling(self):
        self.env['res.partner'].create({
            'name': 'custom delivery address',
            'parent_id': self.company.partner_id.id,
            'type': 'delivery',
            'street': 'Chaussée de Namur 40',
            'city': 'Ramillies',
            'zip': '1367',
            'country_id': self.ref('base.be'),
        })

        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_21)
        invoice = self._create_invoice_one_line(
            move_type='in_invoice',
            journal_id=self.self_billing_journal.id,
            product_id=product,
            price_unit=100.0,
            tax_ids=tax_21,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_selfbilling')

    def test_export_selfbilling_reverse_charge(self):
        # We add a VAT number so that the reverse-charge tax is correctly given TaxCategoryCode K (intra-community supply)
        self.partner_lu_dig.write({
            'peppol_endpoint': 'LU12345613',
            'vat': 'LU12345613',
        })
        tax_21_reverse_charge = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )
        product = self._create_product(lst_price=100.0, taxes_id=tax_21_reverse_charge)

        invoice = self._create_invoice_one_line(
            move_type='in_invoice',
            journal_id=self.self_billing_journal.id,
            product_id=product,
            price_unit=100.0,
            tax_ids=tax_21_reverse_charge,
            partner_id=self.partner_lu_dig,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_selfbilling_reverse_charge')

    def test_export_selfbilling_credit_note(self):
        tax_21 = self.percent_tax(21.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_21)

        invoice = self._create_invoice_one_line(
            move_type='in_refund',
            journal_id=self.self_billing_journal.id,
            product_id=product,
            price_unit=100.0,
            tax_ids=tax_21,
            partner_id=self.partner_be,
            post=True,
        )

        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, 'test_selfbilling_credit_note')

    def test_self_billing_sequence_per_partner(self):
        """Test that self-billing invoices in a self-billing journal get a unique sequence per partner."""

        partner_a = self.partner_a
        partner_b = self.partner_b

        # Create and post invoice for partner_a
        invoice_a = self.env['account.move'].create({
            'partner_id': partner_a.id,
            'move_type': 'in_invoice',
            'journal_id': self.self_billing_journal.id,
            'invoice_date': '2026-04-20',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        invoice_a.action_post()

        # Create and post invoice for partner_b
        invoice_b = self.env['account.move'].create({
            'partner_id': partner_b.id,
            'move_type': 'in_invoice',
            'journal_id': self.self_billing_journal.id,
            'invoice_date': '2026-04-20',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id})],
        })
        invoice_b.action_post()

        partner_a_id = str(partner_a.commercial_partner_id.id).zfill(5)
        partner_b_id = str(partner_b.commercial_partner_id.id).zfill(5)

        # Sequences should contain the partner id
        self.assertTrue((invoice_a.name.split('/')[0] or '').endswith(partner_a_id))
        self.assertTrue((invoice_b.name.split('/')[0] or '').endswith(partner_b_id))

        # Both should be 0001 since sequences are independent per partner
        self.assertTrue(invoice_a.name.endswith('0001'))
        self.assertTrue(invoice_b.name.endswith('0001'))

    def test_nlcius_self_billing_xml(self):
        self.partner_nl.invoice_edi_format = 'nlcius'
        for move_type, type_code in [('in_invoice', '389'), ('in_refund', '261')]:
            with self.subTest(move_type=move_type, type_code=type_code):
                invoice = self._create_invoice_one_line(
                    move_type=move_type,
                    journal_id=self.self_billing_journal.id,
                    product_id=self.product_a,
                    partner_id=self.partner_nl,
                    tax_ids=self.tax_purchase_a,
                    post=True,
                )

                self._generate_invoice_ubl_file(invoice)
                file = invoice.ubl_cii_xml_id.raw
                root = etree.fromstring(file)
                self.assertEqual(
                    root.xpath("cbc:CustomizationID/text()", namespaces=NS_MAP)[0],
                    'urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0',
                )
                self.assertEqual(
                    root.xpath("cbc:ProfileID/text()", namespaces=NS_MAP)[0],
                    'urn:fdc:peppol.eu:2017:poacc:billing:01:1.0',
                )
                move_type_node = 'cbc:InvoiceTypeCode/text()' if move_type == 'in_invoice' else 'cbc:CreditNoteTypeCode/text()'
                self.assertEqual(root.xpath(move_type_node, namespaces=NS_MAP)[0], type_code)
