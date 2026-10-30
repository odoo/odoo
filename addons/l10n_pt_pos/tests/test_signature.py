from datetime import datetime

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import freeze_time, tagged

from odoo.addons.l10n_pt_pos.tests.common import TestL10nPtPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtPosSignature(TestL10nPtPosCommon):
    """
    The invoice of a PoS order is signed when the order is synced, over its date, SystemEntryDate,
    number and gross total, chained to the signature of the previous document of its series (Despacho
    8632/2014 2.1; Portaria 302/2016 4.3.4.3.5). The PoS issues in the series of its invoice journal,
    so its documents share their chains with the back office's. Once signed, nothing the invoice was
    signed over can change (Despacho 8632/2014 1.11), which the integrity check verifies.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.session = cls.open_session()

    # -------------------------------------------------------------------------
    # Signature and integrity
    # -------------------------------------------------------------------------

    def test_signed_payload(self):
        """
        The document date signed is the order's; SystemEntryDate is the time of the sync in UTC (D-9);
        the first document of a series chains to nothing.
        """
        data = self.order_data(date_order='2026-06-15 08:00:00')
        with freeze_time('2026-06-15 10:30:00'):
            order = self.sync(data)
        invoice = order.account_move
        self.assertEqual(self.signing.calls['sign_records'], 1)
        self.assertEqual(self.signing.payloads, [{
            'model': 'account.move',
            'id': invoice.id,
            'sorting_key': 1,
            'date': '2026-06-15',
            'system_entry_date': '2026-06-15T10:30:00',
            'name': 'FS 2026/00001',
            'gross_total': '12.30',
            'previous_signature': '',
        }])
        self.assertSignatureValid(invoice)
        self.assertQrFields(invoice, {'D': 'FS', 'F': '20260615', 'O': '12.30'})

    def test_documents_chained_by_series(self):
        """
        FS, FR and NC are numbered and chained in their own series; an FS of the PoS follows the FS
        the back office issued in the same series.
        """
        back_office = self.issue(self.post(self.make_invoice('out_receipt', partner=False)))
        simplified = self.sell()
        invoice_receipt = self.sell(partner=self.partner_pt)
        refund = self.refund(simplified)
        invoices = back_office + (simplified + invoice_receipt + refund).account_move
        self.assertEqual(
            invoices.mapped('name'),
            ['FS 2026/00001', 'FS 2026/00002', 'FR 2026/00001', 'NC 2026/00001'],
        )
        self.assertEqual(self._previous_signed(simplified.account_move), back_office)
        for invoice in invoices:
            self.assertSignatureValid(invoice)
        self.assertChainVerified(invoices)

    def test_issued_invoice_locked(self):
        """The values the invoice of an order is signed over cannot change once it is issued."""
        invoice = self.sell(partner=self.partner_pt).account_move
        for field_name, value in (
            ('invoice_date', fields.Date.from_string('2026-06-01')),
            ('l10n_pt_document_number', 'FR 2026/00009'),
        ):
            with self.subTest(field=field_name), self.assertRaisesRegex(UserError, "protected by a hash"):
                invoice.write({field_name: value})

    def test_integrity(self):
        """
        The integrity check verifies the chain of the PoS's invoices and reports the first one whose
        signed values were changed behind the ORM's back.
        """
        orders = self.env['pos.order']
        for day in (10, 11, 12):
            with freeze_time(datetime(2026, 6, day, 10, 0)):
                orders |= self.sell()
        invoices = orders.account_move
        self.assertChainVerified(invoices)
        self.tamper(invoices[1], 'invoice_date', '2026-06-13')
        result = self.integrity_results(invoices)[self.series_fs]
        self.assertEqual(result['status'], 'corrupted')
        self.assertEqual(result['msg_cover'], f"Corrupted data on journal entry with id {invoices[1].id} ({invoices[1].name}).")

    def test_order_synced_late(self):
        """
        An order paid while its till was offline is issued when it reaches the server: on its own date,
        at the time of the sync, numbered and chained after the documents issued meanwhile.
        """
        offline = self.order_data(date_order='2026-06-15 09:00:00')
        with freeze_time('2026-06-15 10:00:00'):
            online = self.sell()
        with freeze_time('2026-06-15 11:00:00'):
            order = self.sync(offline)
        invoice = order.account_move
        self.assertEqual(invoice.name, 'FS 2026/00002')
        self.assertEqual(self.signing.payloads[-1]['system_entry_date'], '2026-06-15T11:00:00')
        self.assertEqual(self._previous_signed(invoice), online.account_move)
        self.assertChainVerified(invoice)
