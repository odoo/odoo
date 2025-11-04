# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from lxml import etree

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.l10n_my_edi.tests.test_file_generation_common import (
    NS_MAP,
    L10nMyEDITestFileGenerationCommon,
)


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMyEDITestConsolidatedFileGeneration(L10nMyEDITestFileGenerationCommon):

    @classmethod
    @L10nMyEDITestFileGenerationCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()
        # Purposedly do not set the identification number, so that this partner is picked up for consolidated invoices
        cls.partner_a.write({
            'l10n_my_identification_type': False,
            'l10n_my_identification_number': False,
            'vat': False,
        })

    @freeze_time('2025-07-15')
    def test_consolidating_invoices(self):
        """
        Create three invoices for the period and consolidate them; then validate the xml file of a consolidated invoice.
        """
        for _ in range(3):
            self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_id = myinvois_document_action['res_id']
        myinvois_document = self.env['myinvois.document'].browse(myinvois_document_id)
        self.assertEqual(len(myinvois_document.invoice_ids), 3)  # We should get a single document, linked to the three invoices

        myinvois_document.myinvois_issuance_date = fields.Date.context_today(myinvois_document)
        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)
        root = etree.fromstring(file)

        # Make sure that the correct sequence is in use
        self._assert_node_values(
            root,
            'cbc:ID',
            'CINV/2025/00001',
        )
        # Check the user; it should be using the General Public information
        customer_root = root.xpath('cac:AccountingCustomerParty/cac:Party', namespaces=NS_MAP)[0]
        self._assert_node_values(
            customer_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="TIN"]',
            'EI00000000010',
        )
        self._assert_node_values(
            customer_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="BRN"]',
            'NA',
        )
        # Check the line; there should be only one for all three invoices.
        invoice_root = root.xpath('cac:InvoiceLine', namespaces=NS_MAP)
        self.assertEqual(len(invoice_root), 1)
        self._assert_node_values(
            invoice_root[0],
            'cac:Item/cbc:Name',
            'INV/2025/00001-INV/2025/00003',
        )
        self._assert_node_values(
            invoice_root[0],
            'cac:Item/cac:CommodityClassification/cbc:ItemClassificationCode',
            '004',
        )
        # Ensure that the document type is, as expected, invoice
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '01',
        )

    @freeze_time('2025-07-15')
    def test_consolidating_multi_currency_invoices(self):
        """
        Create two invoices of different currencies for the period, then ensure that these are correctly separated in two
        different consolidated invoices.
        """
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today(), currency=self.other_currency)

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_ids = myinvois_document_action['domain'][0][2]
        myinvois_documents = self.env['myinvois.document'].browse(myinvois_document_ids)
        self.assertEqual(len(myinvois_documents), 2)

    @freeze_time('2025-07-15')
    def test_consolidating_multi_journal_invoices(self):
        """
        Very similar purpose as the previous test, but with separate journals.
        We will expect three consolidated invoice; two for a journal having two invoices of different currencies and
        one for the other journal.
        """
        journal2 = self.company_data['default_journal_sale'].copy()
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today(), currency=self.other_currency)
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today(), journal=journal2)

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_ids = myinvois_document_action['domain'][0][2]
        myinvois_documents = self.env['myinvois.document'].browse(myinvois_document_ids)
        self.assertEqual(len(myinvois_documents), 3)

    @freeze_time('2025-07-15')
    def test_consolidating_credit_notes(self):
        """
        Create both an invoice and a credit note for that invoice in the period; then consolidate them.
        We expect two separate consolidated invoices, one per document types.
        """
        invoices = self.env['account.move']
        for _ in range(3):
            invoices |= self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())

        for invoice in invoices[:2]:
            action = invoice.action_reverse()
            reversal_wizard = self.env[action['res_model']].with_context(
                active_ids=invoice.ids,
                active_model='account.move',
                default_journal_id=invoice.journal_id.id,
                date=fields.Date.today(),
            ).create({})
            action = reversal_wizard.reverse_moves()
            credit_note = self.env['account.move'].browse(action['res_id'])
            credit_note.action_post()

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_ids = myinvois_document_action['domain'][0][2]
        myinvois_documents = self.env['myinvois.document'].browse(myinvois_document_ids)
        self.assertEqual(len(myinvois_documents), 2)
        # Get the credit note document and ensure it has the correct type set on it
        credit_note_document = myinvois_documents.filtered(lambda m: m.invoice_ids[0].move_type == 'out_refund')[0]
        credit_note_document.myinvois_issuance_date = fields.Date.context_today(credit_note_document)
        file, errors = credit_note_document._myinvois_generate_xml_file()
        self.assertFalse(errors)
        root = etree.fromstring(file)
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '02',
        )
        # Make sure that the correct sequence is in use
        self._assert_node_values(
            root,
            'cbc:ID',
            'CRINV/2025/00001',
        )
        invoice_root = root.xpath('cac:InvoiceLine', namespaces=NS_MAP)
        self._assert_node_values(
            invoice_root[0],
            'cac:Item/cbc:Name',
            'RINV/2025/00001-RINV/2025/00002',
        )
        # Ensure that the amounts are positive
        self._assert_node_values(
            invoice_root[0],
            'cbc:LineExtensionAmount',
            '2000.00',
        )
        self._assert_node_values(
            invoice_root[0],
            'cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount',
            '200.00',
        )

    @freeze_time('2025-07-15')
    def test_consolidating_debit_notes(self):
        """
        Same Idea as the previous test, but for debit notes.
        """
        if self.env.ref('base.module_account_debit_note').state != 'installed':
            self.skipTest("This test requires the Debit Notes module to be installed.")

        invoices = self.env['account.move']
        for _ in range(3):
            invoices |= self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())

        for invoice in invoices[:2]:
            action = invoice.action_debit_note()
            debit_wizard = self.env[action['res_model']].with_context(
                active_ids=invoice.ids,
                active_model='account.move',
                default_journal_id=invoice.journal_id.id,
                date=fields.Date.today(),
            ).create({
                'copy_lines': True,
            })
            action = debit_wizard.create_debit()
            debit_note = self.env['account.move'].browse(action['res_id'])
            debit_note.action_post()

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_ids = myinvois_document_action['domain'][0][2]
        myinvois_documents = self.env['myinvois.document'].browse(myinvois_document_ids)
        self.assertEqual(len(myinvois_documents), 2)
        # Get the credit note document and ensure it has the correct type set on it
        debit_note_document = myinvois_documents.filtered(lambda m: m.invoice_ids[0].debit_origin_id)[0]
        debit_note_document.myinvois_issuance_date = fields.Date.context_today(debit_note_document)
        file, errors = debit_note_document._myinvois_generate_xml_file()
        self.assertFalse(errors)
        root = etree.fromstring(file)
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '03',
        )
        # Make sure that the correct sequence is in use
        self._assert_node_values(
            root,
            'cbc:ID',
            'CDINV/2025/00001',
        )

    @freeze_time('2025-07-15')
    def test_consolidating_refunds(self):
        """
        Similar as the previous tests, but this time for a refund document (credit note that has been paid).
        """
        invoices = self.env['account.move']
        for _ in range(3):
            invoices |= self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoices.ids
        ).create({})._create_payments()

        for invoice in invoices[:2]:
            action = invoice.action_reverse()
            reversal_wizard = self.env[action['res_model']].with_context(
                active_ids=invoice.ids,
                active_model='account.move',
                default_journal_id=invoice.journal_id.id,
                date=fields.Date.today(),
            ).create({})
            action = reversal_wizard.reverse_moves()
            credit_note = self.env['account.move'].browse(action['res_id'])
            credit_note.action_post()
            self.env['account.payment.register'].with_context(active_model='account.move', active_ids=credit_note.ids).create({})._create_payments()

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_ids = myinvois_document_action['domain'][0][2]
        myinvois_documents = self.env['myinvois.document'].browse(myinvois_document_ids)
        self.assertEqual(len(myinvois_documents), 2)
        # Get the credit note document and ensure it has the correct type set on it
        credit_note_document = myinvois_documents.filtered(lambda m: m.invoice_ids[0].move_type == 'out_refund')[0]
        credit_note_document.myinvois_issuance_date = fields.Date.context_today(credit_note_document)
        file, errors = credit_note_document._myinvois_generate_xml_file()
        self.assertFalse(errors)
        root = etree.fromstring(file)
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '04',
        )
        # Make sure that the correct sequence is in use
        self._assert_node_values(
            root,
            'cbc:ID',
            'CRINV/2025/00001',
        )

    @freeze_time('2025-07-15')
    def test_consolidating_everything(self):
        """
        Same as previous tests, but we create a mix of invoices, credit notes, debit notes, refunds, in multiple currencies/journals.
        We will just assert that the correct amount of documents is created, and the moves are correctly spread.

        Note: We don't use init_invoice here because the amount of invoices to create would be very slow if done one at a time.
        """
        if self.env.ref('base.module_account_debit_note').state != 'installed':
            self.skipTest("This test requires the Debit Notes module to be installed.")

        def is_refund(cn):
            return self.env['account.edi.xml.ubl_myinvois_my']._l10n_my_edi_get_refund_details(cn)[0]

        base_invoice_data = {
            'partner_id': self.partner_a.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'tax_ids': [Command.set(self.company_data['default_tax_sale'].ids)],
                }),
            ],
        }

        journal2 = self.company_data['default_journal_sale'].copy()
        invoices_data = [
            # Regular Invoices
            base_invoice_data,
            {
                **base_invoice_data,
                'currency_id': self.other_currency.id,
            },
            {
                **base_invoice_data,
                'journal_id': journal2.id,
            },
            {
                **base_invoice_data,
                'currency_id': self.other_currency.id,
                'journal_id': journal2.id,
            },
            # Invoices to credit
            base_invoice_data,
            base_invoice_data,
            {
                **base_invoice_data,
                'currency_id': self.other_currency.id,
            },
            # Invoices to refund
            base_invoice_data,
            base_invoice_data,
            # Invoices to debit
            base_invoice_data,
            base_invoice_data,
        ]
        all_invoices = self.env['account.move'].create(invoices_data)
        all_invoices.action_post()

        invoices_to_credit = all_invoices[4:7]
        invoices_to_refund = all_invoices[7:9]
        invoices_to_debit = all_invoices[9:11]

        # Pay the invoices to refund
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoices_to_refund.ids
        ).create({})._create_payments()

        # Credit the invoices to credit.
        reversal_wizard = self.env['account.move.reversal'].with_context(
            active_ids=invoices_to_credit.ids,
            active_model='account.move',
            default_journal_id=self.company_data['default_journal_sale'].id,
            date=fields.Date.today(),
        ).create({})
        action = reversal_wizard.reverse_moves()
        credit_notes = self.env['account.move'].browse(action['domain'][0][2])

        reversal_wizard = self.env['account.move.reversal'].with_context(
            active_ids=invoices_to_refund.ids,
            active_model='account.move',
            default_journal_id=self.company_data['default_journal_sale'].id,
            date=fields.Date.today(),
        ).create({})
        action = reversal_wizard.reverse_moves()
        refunds = self.env['account.move'].browse(action['domain'][0][2])

        debit_wizard = self.env['account.debit.note'].with_context(
            active_ids=invoices_to_debit.ids,
            active_model='account.move',
            default_journal_id=self.company_data['default_journal_sale'].id,
            date=fields.Date.today(),
        ).create({
            'copy_lines': True,
        })
        action = debit_wizard.create_debit()
        debit_notes = self.env['account.move'].browse(action['domain'][0][2])

        (credit_notes | refunds | debit_notes).action_post()
        # Ensure to pay the refunds as well
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=refunds.ids
        ).create({})._create_payments()

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_ids = myinvois_document_action['domain'][0][2]
        myinvois_documents = self.env['myinvois.document'].browse(myinvois_document_ids)
        self.assertEqual(len(myinvois_documents), 8)
        # Make sure that what we have is the expected count of each type.
        invoice_documents = myinvois_documents.filtered(lambda m: m.invoice_ids[0].move_type == 'out_invoice' and not m.invoice_ids[0].debit_origin_id)
        self.assertEqual(len(invoice_documents), 4)
        debit_notes_documents = myinvois_documents.filtered(lambda m: m.invoice_ids[0].move_type == 'out_invoice' and m.invoice_ids[0].debit_origin_id)
        self.assertEqual(len(debit_notes_documents), 1)
        credit_notes_documents = myinvois_documents.filtered(lambda m: m.invoice_ids[0].move_type == 'out_refund' and not is_refund(m.invoice_ids[0]))
        self.assertEqual(len(credit_notes_documents), 2)
        refund_documents = myinvois_documents.filtered(lambda m: m.invoice_ids[0].move_type == 'out_refund' and is_refund(m.invoice_ids[0]))
        self.assertEqual(len(refund_documents), 1)

    @freeze_time('2025-07-15')
    def test_consolidating_invoices_with_regular_partner(self):
        """
        Ensure that when a regular commercial partner is set on an invoice (one that has vat and id information set) we
        do not pick that invoice for consolidation.
        """
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today(), partner=self.partner_b)

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_id = myinvois_document_action['res_id']
        myinvois_document = self.env['myinvois.document'].browse(myinvois_document_id)
        self.assertEqual(len(myinvois_document.invoice_ids), 2)  # We should get a single document, linked to the two valid invoices

    @freeze_time('2025-07-15')
    def test_consolidating_self_billed_invoices(self):
        """
        Create three self billed invoices for the period and consolidate them; then validate the xml file of a consolidated invoice.
        """
        for _ in range(3):
            self.init_invoice('in_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_id = myinvois_document_action['res_id']
        myinvois_document = self.env['myinvois.document'].browse(myinvois_document_id)
        self.assertEqual(len(myinvois_document.invoice_ids), 3)  # We should get a single document, linked to the three invoices

        myinvois_document.myinvois_issuance_date = fields.Date.context_today(myinvois_document)
        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)
        root = etree.fromstring(file)

        # Make sure that the correct sequence is in use
        self._assert_node_values(
            root,
            'cbc:ID',
            'CBILL/2025/00001',
        )
        # Check the user; it should be using the General Public information
        supplier_root = root.xpath('cac:AccountingSupplierParty/cac:Party', namespaces=NS_MAP)[0]
        self._assert_node_values(
            supplier_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="TIN"]',
            'EI00000000010',
        )
        self._assert_node_values(
            supplier_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="BRN"]',
            'NA',
        )
        # Check the line; there should be only one for all three invoices.
        invoice_root = root.xpath('cac:InvoiceLine', namespaces=NS_MAP)
        self.assertEqual(len(invoice_root), 1)
        self._assert_node_values(
            invoice_root[0],
            'cac:Item/cbc:Name',
            'BILL/2025/07/0001-BILL/2025/07/0003',
        )
        self._assert_node_values(
            invoice_root[0],
            'cac:Item/cac:CommodityClassification/cbc:ItemClassificationCode',
            '004',
        )
        # Ensure that the document type is, as expected, invoice
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '11',
        )

    @freeze_time('2025-07-15')
    def test_consolidating_single_invoices(self):
        """
        Ensure that a single invoice linked to a MyInvois Document is considered a consolidated invoice if it makes sense.
        """
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())

        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_id = myinvois_document_action['res_id']
        myinvois_document = self.env['myinvois.document'].browse(myinvois_document_id)
        self.assertEqual(len(myinvois_document.invoice_ids), 1)
        self.assertTrue(myinvois_document._is_consolidated_invoice())

        myinvois_document.myinvois_issuance_date = fields.Date.context_today(myinvois_document)
        file, errors = myinvois_document._myinvois_generate_xml_file()
        self.assertFalse(errors)
        root = etree.fromstring(file)

        # Make sure that the correct sequence is in use
        self._assert_node_values(
            root,
            'cbc:ID',
            'CINV/2025/00001',
        )
        # Check the user; it should be using the General Public information
        customer_root = root.xpath('cac:AccountingCustomerParty/cac:Party', namespaces=NS_MAP)[0]
        self._assert_node_values(
            customer_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="TIN"]',
            'EI00000000010',
        )
        self._assert_node_values(
            customer_root,
            'cac:PartyIdentification/cbc:ID[@schemeID="BRN"]',
            'NA',
        )
        # Check the line; there should be only one for all three invoices.
        invoice_root = root.xpath('cac:InvoiceLine', namespaces=NS_MAP)
        self.assertEqual(len(invoice_root), 1)
        self._assert_node_values(
            invoice_root[0],
            'cac:Item/cbc:Name',
            'INV/2025/00001',
        )
        self._assert_node_values(
            invoice_root[0],
            'cac:Item/cac:CommodityClassification/cbc:ItemClassificationCode',
            '004',
        )
        # Ensure that the document type is, as expected, invoice
        self._assert_node_values(
            root,
            'cbc:InvoiceTypeCode',
            '01',
        )

    @freeze_time('2025-07-15')
    def test_sending_single_invoices_for_consolidated_invoice(self):
        """
        If an invoice is using a consolidated invoice user (general public/...) but is sent individually, it should be following the
        single invoice submission format and not consolidated invoice one.
        """
        proxy_user = self.env['account_edi_proxy_client.user']._register_proxy_user(self.company_data['company'], 'l10n_my_edi', 'demo')
        proxy_user.edi_mode = 'test'

        invoice = self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
        with self.assertRaises(UserError):  # We expect an error that would happen due to missing ID info on the partner, but wouldn't happen in consolidated invoice generation
            invoice.action_l10n_my_edi_send_invoice()

    @freeze_time('2025-07-15')
    def test_consolidating_sequence(self):
        """
        Create a myinvois document from a regular invoice; and then create a consolidated invoice for the same journal.
        The consolidated invoice should have its name properly computed, and shouldn't pick the regular invoice as reference.
        """
        # Create and 'send' an invoice, the document should share the same name.
        invoice = self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today(), partner=self.partner_b)
        invoice._create_myinvois_document()
        self.assertEqual(invoice.l10n_my_edi_document_ids.name, 'INV/2025/00001')

        # When making a consolidated invoice, it should not pick up the INV and should instead start a new sequence.
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_id = myinvois_document_action['res_id']
        myinvois_document = self.env['myinvois.document'].browse(myinvois_document_id)
        self.assertEqual(len(myinvois_document.invoice_ids), 1)
        self.assertTrue(myinvois_document._is_consolidated_invoice())

        myinvois_document.myinvois_issuance_date = fields.Date.context_today(myinvois_document)
        self.assertEqual(myinvois_document.name, 'CINV/2025/00001')

        # And adding another one should continue the sequence
        self.init_invoice('out_invoice', taxes=self.company_data['default_tax_sale'], products=self.product_a, post=True, invoice_date=fields.Date.today())
        myinvois_document_action = self.env['myinvois.consolidate.invoice.wizard'].create({
            'date_from': '2025-07-01',
            'date_to': '2025-07-31',
            'consolidation_type': 'invoice',
        }).button_consolidate()

        myinvois_document_id = myinvois_document_action['res_id']
        myinvois_document = self.env['myinvois.document'].browse(myinvois_document_id)
        self.assertEqual(len(myinvois_document.invoice_ids), 1)
        self.assertTrue(myinvois_document._is_consolidated_invoice())

        myinvois_document.myinvois_issuance_date = fields.Date.context_today(myinvois_document)
        self.assertEqual(myinvois_document.name, 'CINV/2025/00002')
