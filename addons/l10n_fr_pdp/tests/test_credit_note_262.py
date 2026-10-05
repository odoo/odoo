from lxml import etree

from odoo.fields import Command
from odoo.tests import tagged

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install', 'credit_note_262')
class TestCommercialCreditNote262Export(TestL10nFrPdpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # CII/Factur-X BR-DE-7 requires a seller email.
        cls.env.company.email = 'billing@example.com'

    def _create_262_credit_note(self, post=True, **kwargs):
        vals = {
            'move_type': 'out_refund',
            'ref': 'CTR-2026-01',
        }
        vals.update(kwargs)
        refund = self._create_french_invoice(**vals)
        if post:
            refund.action_post()
        return refund

    def _assert_no_preceding_invoice(self, tree):
        self.assertIsNone(tree.find('.//{*}BillingReference/{*}InvoiceDocumentReference/{*}ID'))
        self.assertIsNone(tree.find('.//{*}InvoiceReferencedDocument/{*}IssuerAssignedID'))

    def _assert_period(self, refund, tree, cii=False):
        start, end = refund._l10n_fr_pdp_get_invoicing_period()
        if cii:
            self.assertEqual(
                tree.findtext(
                    './/{*}ApplicableHeaderTradeSettlement/{*}BillingSpecifiedPeriod/{*}StartDateTime/{*}DateTimeString',
                ),
                start.strftime('%Y%m%d'),
            )
            self.assertEqual(
                tree.findtext(
                    './/{*}ApplicableHeaderTradeSettlement/{*}BillingSpecifiedPeriod/{*}EndDateTime/{*}DateTimeString',
                ),
                end.strftime('%Y%m%d'),
            )
            return
        self.assertEqual(tree.findtext('.//{*}InvoicePeriod/{*}StartDate'), str(start))
        self.assertEqual(tree.findtext('.//{*}InvoicePeriod/{*}EndDate'), str(end))

    def test_cdar_stays_381(self):
        refund = self._create_262_credit_note(post=False)
        # Flux 10 G1.01 does not allow UNTDID 262; CDAR stays 381.
        self.assertEqual(
            self.env['pdp.flow.10.xml.builder']._get_move_typecode(refund),
            '381',
        )

    def test_flow10_maps_contract_and_period(self):
        refund = self._create_262_credit_note(post=False)
        refund.invoice_date_due = '2017-03-31'
        builder = self.env['pdp.flow.10.xml.builder']
        node = {}
        builder._invoice_add_referenced_documents(node, refund)
        self.assertEqual(node['ReferencedDocument'][0]['ID']['_text'], 'CTR-2026-01')
        self.assertEqual(node['ReferencedDocument'][0]['IssueDate']['_text'], '20170101')
        builder._invoice_add_invoice_period(node, refund, False)
        self.assertEqual(node['InvoicePeriod']['StartDate']['_text'], '20170101')
        self.assertEqual(node['InvoicePeriod']['EndDate']['_text'], '20170331')

    def test_flow10_same_day_period_skips_invoice_period(self):
        refund = self._create_262_credit_note(post=False)
        refund.invoice_date_due = refund.invoice_date
        node = {}
        builder = self.env['pdp.flow.10.xml.builder']
        builder._invoice_add_referenced_documents(node, refund)
        builder._invoice_add_invoice_period(node, refund, False)
        self.assertEqual(node['ReferencedDocument'][0]['IssueDate']['_text'], '20170101')
        self.assertNotIn('InvoicePeriod', node)

    def test_flow10_regular_credit_note_keeps_invoice_reference(self):
        invoice = self._create_french_invoice()
        invoice.action_post()
        refund = self._create_french_invoice(
            move_type='out_refund',
            reversed_entry_id=invoice.id,
            ref='CTR-2026-01',
        )
        node = {}
        self.env['pdp.flow.10.xml.builder']._invoice_add_referenced_documents(node, refund)
        self.assertEqual(node['ReferencedDocument'][0]['ID']['_text'], invoice.name)

    def test_standalone_refund_is_262(self):
        refund = self._create_262_credit_note(post=False)
        self.assertTrue(refund._l10n_fr_pdp_is_document_type_262())

    def test_ubl_21_fr_export_type_262(self):
        refund = self._create_262_credit_note()
        xml_bytes, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(refund)
        self.assertFalse(errors, errors)
        tree = etree.fromstring(xml_bytes)
        self.assertEqual(tree.findtext('.//{*}CreditNoteTypeCode'), '262')
        self.assertEqual(tree.findtext('.//{*}ContractDocumentReference/{*}ID'), 'CTR-2026-01')
        self._assert_period(refund, tree)
        self._assert_no_preceding_invoice(tree)

    def test_ubl_bis3_export_type_262(self):
        refund = self._create_262_credit_note()
        xml_bytes, errors = self.env['account.edi.xml.ubl_bis3']._export_invoice(refund)
        self.assertFalse(errors, errors)
        tree = etree.fromstring(xml_bytes)
        self.assertEqual(tree.findtext('.//{*}CreditNoteTypeCode'), '262')
        self.assertEqual(tree.findtext('.//{*}ContractDocumentReference/{*}ID'), 'CTR-2026-01')
        self._assert_period(refund, tree)
        self._assert_no_preceding_invoice(tree)

    def test_facturx_cii_export_type_262(self):
        refund = self._create_262_credit_note()
        xml_bytes, errors = self.env['account.edi.xml.cii']._export_invoice(refund)
        self.assertFalse(errors, errors)
        tree = etree.fromstring(xml_bytes)
        self.assertEqual(tree.findtext('.//{*}ExchangedDocument/{*}TypeCode'), '262')
        self.assertEqual(
            tree.findtext('.//{*}ContractReferencedDocument/{*}IssuerAssignedID'),
            'CTR-2026-01',
        )
        self._assert_period(refund, tree, cii=True)
        self.assertIsNone(tree.find('.//{*}InvoiceReferencedDocument/{*}IssuerAssignedID'))

    def test_262_requires_contract_on_export(self):
        refund = self._create_262_credit_note(post=True, ref=False)
        _, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(refund)
        self.assertTrue(errors)
        error_text = ' '.join(map(str, errors.values() if isinstance(errors, dict) else errors))
        self.assertIn('262', error_text)

    def test_262_period_uses_invoice_dates(self):
        refund = self._create_262_credit_note(post=False)
        start, end = refund._l10n_fr_pdp_get_invoicing_period()
        self.assertEqual(start, refund.invoice_date)
        self.assertEqual(end, refund.invoice_date_due or refund.invoice_date)

    def test_non_fr_fiscal_country_skips_262(self):
        refund = self._create_262_credit_note(post=False)
        refund.company_id.account_fiscal_country_id = self.env.ref('base.be')
        self.assertFalse(refund._l10n_fr_pdp_is_document_type_262())

    def test_sale_origin_invoice_blocks_262(self):
        """A refund that shares sale lines with a posted invoice is not UNTDID 262.

        ``l10n_fr_pdp`` does not depend on ``sale``. Without ``sale_line_ids`` the
        helper returns an empty recordset and a standalone refund stays 262.
        """
        refund = self._create_262_credit_note(post=False)
        self.assertFalse(refund.reversed_entry_id)
        self.assertTrue(refund._l10n_fr_pdp_is_document_type_262())

        move_line_fields = self.env['account.move.line']._fields
        sale_field = move_line_fields.pop('sale_line_ids', None)
        try:
            self.assertFalse(refund._l10n_fr_pdp_get_sale_origin_invoices())
        finally:
            if sale_field is not None:
                move_line_fields['sale_line_ids'] = sale_field
        self.assertTrue(refund._l10n_fr_pdp_is_document_type_262())

        if 'sale_line_ids' not in self.env['account.move.line']._fields:
            # Full sales-order linkage needs sale, which is not a hard dependency.
            return

        invoice = self._create_french_invoice()
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 1.0,
            })],
        })
        sale_line = order.order_line
        (invoice.invoice_line_ids[:1] | refund.invoice_line_ids[:1]).sale_line_ids = sale_line
        self.assertFalse(refund._l10n_fr_pdp_get_sale_origin_invoices())
        self.assertTrue(refund._l10n_fr_pdp_is_document_type_262())
        invoice.action_post()
        self.assertEqual(refund._l10n_fr_pdp_get_sale_origin_invoices(), invoice)
        self.assertFalse(refund._l10n_fr_pdp_is_document_type_262())

    def test_reversed_credit_note_stays_381(self):
        invoice = self._create_french_invoice()
        invoice.action_post()
        refund = self._create_french_invoice(
            move_type='out_refund',
            reversed_entry_id=invoice.id,
            ref='CTR-2026-01',
        )
        refund.action_post()
        self.assertFalse(refund._l10n_fr_pdp_is_document_type_262())
        xml_bytes, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(refund)
        self.assertFalse(errors, errors)
        tree = etree.fromstring(xml_bytes)
        self.assertEqual(tree.findtext('.//{*}CreditNoteTypeCode'), '381')
        self.assertEqual(
            tree.findtext('.//{*}BillingReference/{*}InvoiceDocumentReference/{*}ID'),
            invoice.name,
        )
