from lxml import etree

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

    def test_standalone_refund_is_262(self):
        refund = self._create_262_credit_note(post=False)
        self.assertTrue(refund._l10n_fr_pdp_is_document_type_262())
        self.assertTrue(refund.l10n_fr_pdp_is_commercial_credit_note)

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
        xml_bytes, errors = self.env['account.edi.xml.ubl_21_fr']._export_invoice(refund)
        self.assertTrue(errors)
        error_text = ' '.join(map(str, errors.values() if isinstance(errors, dict) else errors))
        self.assertIn('262', error_text)

    def test_262_period_uses_invoice_dates(self):
        refund = self._create_262_credit_note(post=False)
        start, end = refund._l10n_fr_pdp_get_invoicing_period()
        self.assertEqual(start, refund.invoice_date)
        self.assertEqual(end, refund.invoice_date_due or refund.invoice_date)

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
