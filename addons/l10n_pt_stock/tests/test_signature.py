from datetime import datetime
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import freeze_time, tagged

from odoo.addons.l10n_pt_certification.tests.common import AT_DEMO_PUBLIC_KEY, REAL_SIGNING
from odoo.addons.l10n_pt_stock.tests.common import TestL10nPtStockCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtStockSignature(TestL10nPtStockCommon):
    """
    A transport document is signed when it is issued, at validation, over its date, SystemEntryDate,
    number and a gross total of 0.00, chained to the signature of the previous document of its series
    in number order (Despacho 8632/2014 2.1; Portaria 302/2016 4.2.3.12). Once signed, nothing it was
    signed over can change (Despacho 8632/2014 1.11), which the integrity check verifies.
    """

    # -------------------------------------------------------------------------
    # Signature and integrity
    # -------------------------------------------------------------------------

    def test_signed_payload(self):
        """
        The date signed is the validation's, SystemEntryDate its time in UTC (D-9), the total 0.00; the
        first document of a series chains to nothing. The QR code reads the same date.
        """
        picking = self.make_transfer()
        with freeze_time('2026-06-15 10:30:00'):
            self.validate(picking)
        self.assertEqual(self.signing.payloads, [{
            'model': 'stock.picking',
            'id': picking.id,
            'sorting_key': 1,
            'date': '2026-06-15',
            'system_entry_date': '2026-06-15T10:30:00',
            'name': 'GT 2026/00001',
            'gross_total': '0.00',
            'previous_signature': '',
        }])
        self.assertSignatureValid(picking)
        self.assertQrFields(picking, {'F': '20260615', 'G': 'GT 2026/00001'})

    def test_chains_by_series(self):
        """
        Deliveries and moves between warehouses chain in their GT series, return notes in their GD series,
        each verified on its own.
        """
        delivery = self.deliver()
        between_warehouses = self.deliver(self.int_type, partner=False, location_dest=self.warehouse_2.lot_stock_id)
        receipt = self.deliver(self.in_type, partner=self.partner_supplier)
        supplier_return = self.validate(self.make_return(receipt))
        self.assertEqual(self._previous_signed(between_warehouses), delivery)
        self.assertFalse(self._previous_signed(supplier_return))
        self.assertEqual(self.signing.payloads[-1]['previous_signature'], '')
        for picking in delivery + between_warehouses + supplier_return:
            self.assertSignatureValid(picking)
        self.assertChainVerified(delivery + between_warehouses + supplier_return)

    def test_signed_fields_locked(self):
        """What a transfer is signed over, its series and its signature cannot change once signed; its note can."""
        picking = self.deliver()
        for field_name, value in (
            ('date_done', datetime(2026, 6, 1, 10, 0)),
            ('name', 'WH/OUT/99999'),
            ('l10n_pt_document_number', 'GT 2026/00009'),
            ('l10n_pt_hashed_on', datetime(2026, 6, 1, 10, 0)),
            ('l10n_pt_inalterable_hash', '$1$fake'),
            ('l10n_pt_at_series_id', self.series_factory(document_type='outgoing', name='2026B').id),
        ):
            with self.subTest(field=field_name), self.assertRaisesRegex(UserError, "protected by a hash"):
                picking.write({field_name: value})
        picking.note = 'Frágil'
        self.assertSignatureValid(picking)

    def test_integrity(self):
        """
        The integrity check verifies the chain from its first to its last transfer, and reports the first
        one whose signed values or signature were changed behind the ORM's back.
        """
        pickings = self.env['stock.picking']
        for day in (10, 11, 12):
            with freeze_time(datetime(2026, 6, day, 10, 0)):
                pickings |= self.deliver()
        result = self.integrity_results(pickings)[self.series_gt]
        self.assertEqual(result['status'], 'verified')
        self.assertEqual(result['msg_cover'], "Delivery orders are correctly hashed")
        self.assertEqual(result['first_document_number'], 'GT 2026/00001')
        self.assertEqual(result['last_document_number'], 'GT 2026/00003')
        self.assertEqual(result['first_date'], datetime(2026, 6, 10, 10, 0))
        self.assertEqual(result['last_date'], datetime(2026, 6, 12, 10, 0))

        def corrupted():
            result = self.integrity_results(pickings)[self.series_gt]
            self.assertEqual(result['status'], 'corrupted')
            return result['msg_cover']

        self.tamper(pickings[2], 'l10n_pt_inalterable_hash', '$1$fake')
        self.assertEqual(corrupted(), f"Corrupted data on delivery order with id {pickings[2].id} (GT 2026/00003).")
        # The walk stops at the first corrupted transfer.
        self.tamper(pickings[1], 'date_done', datetime(2026, 6, 13, 10, 0))
        self.assertEqual(corrupted(), f"Corrupted data on delivery order with id {pickings[1].id} (GT 2026/00002).")

    def test_integrity_report(self):
        """
        The stock integrity check runs from the company, for PT companies only, and its report signs what
        is missing and prints the result of each series.
        """
        picking = self.deliver()
        results = self.company_pt._l10n_pt_stock_check_hash_integrity()['results']
        self.assertEqual([r['series_document_identifier'] for r in results], ['GT 2026'])
        with self.assertRaisesRegex(UserError, "only available for Portuguese companies"):
            self.company_foreign._l10n_pt_stock_check_hash_integrity()
        action = self.company_pt._l10n_pt_stock_action_check_hash_integrity()
        self.assertEqual(action['report_name'], 'l10n_pt_stock.report_hash_integrity')
        html = self.preview(self.company_pt, action['report_name'])
        self.assertIn(picking.l10n_pt_inalterable_hash, html)
        self.assertIn("Delivery orders are correctly hashed", html)

    def test_hundred_thousandth_transfer(self):
        """A series crossing GT 2026/99999 → GT 2026/100000 chains in number order, not in string order (PT-35)."""
        self.series_gt._l10n_pt_get_document_number_sequence().number_next = 99999
        last_five_digits = self.deliver()
        with freeze_time('2026-06-15 11:00:00'):
            first_six_digits = self.deliver()
        self.assertEqual(last_five_digits.l10n_pt_document_number, 'GT 2026/99999')
        self.assertEqual(first_six_digits.l10n_pt_document_number, 'GT 2026/100000')
        self.assertEqual([p['sorting_key'] for p in self.signing.payloads], [99999, 100000])
        self.assertEqual(self._previous_signed(first_six_digits), last_five_digits)
        self.assertChainVerified(last_five_digits + first_six_digits)

    def test_at_sample_transfers_verify(self):
        """
        The transport guides of the AT's demo SAF-T (saft_idemo599999999.xml), rebuilt as deliveries,
        verify under the AT's demo public key against the signatures the AT published for them: the
        module signs and verifies the values the AT signs, chained as the AT chains them (Despacho
        8632/2014 2.1). Offline: the published signatures are stored, not asked of the signing service.
        """
        with (
            self.at_sample_transfers() as signatures,
            patch('odoo.addons.l10n_pt_certification.utils.hashing.verify_integrity', REAL_SIGNING['verify_integrity']),
        ):
            pickings = self.env['stock.picking'].concat(*signatures)
            self.assertEqual(
                [(p['date'], p['name'], p['gross_total']) for p in self.signing.payloads],
                [('2017-09-15', '1G 5A/1', '679.61'), ('2017-11-30', '1G 5A/2', '679.61'), ('2017-12-17', '1G 5A/3', '1487.67')],
            )
            for picking, signature in signatures.items():
                self.tamper(picking, 'l10n_pt_inalterable_hash', f'$1${signature}')
            self.signing.public_keys = {1: AT_DEMO_PUBLIC_KEY}
            self.assertChainVerified(pickings)

            self.tamper(pickings[1], 'date_done', datetime(2017, 12, 1, 23, 10, 23))
            result = self.integrity_results(pickings)[pickings.l10n_pt_at_series_id]
            self.assertEqual(result['status'], 'corrupted')
            self.assertIn(f"delivery order with id {pickings[1].id}", result['msg_cover'])

    # -------------------------------------------------------------------------
    # Signing service
    # -------------------------------------------------------------------------

    def test_signing_unavailable_at_validation(self):
        """
        With the signing service unreachable, a delivery is still validated and numbered, the failure
        logged in its chatter (PT-44, parked); the daily job signs it once the service answers, at the
        time it is signed.
        """
        self.signing.available = False
        picking = self.deliver()
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.l10n_pt_document_number, 'GT 2026/00001')
        self.assertFalse(picking.l10n_pt_inalterable_hash)
        self.assertFalse(picking.l10n_pt_qr_code_str)
        self.assertIn("Unable to connect to the IAP endpoint", picking.message_ids[0].body)

        self.signing.available = True
        with freeze_time('2026-06-15 12:00:00'):
            self.env['stock.picking']._cron_l10n_pt_stock_compute_missing_hashes()
        self.assertIssued(picking)
        self.assertEqual(picking.l10n_pt_hashed_on, datetime(2026, 6, 15, 12, 0))
        self.assertEqual(self.signing.payloads[-1]['system_entry_date'], '2026-06-15T12:00:00')
        self.assertTrue(picking.l10n_pt_qr_code_str)
        self.assertChainVerified(picking)

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------
    # Service calls per series, not per document.

    def test_validation_signs_a_series_in_one_call(self):
        """
        Transfers validated together are numbered in order and signed in one call per series, chained by
        their number; the integrity check fetches the public keys once.
        """
        deliveries = self.make_transfer() + self.make_transfer() + self.make_transfer()
        self.validate(deliveries)
        self.assertEqual(deliveries.mapped('l10n_pt_document_number'), ['GT 2026/00001', 'GT 2026/00002', 'GT 2026/00003'])
        self.assertEqual(self.signing.calls['sign_records'], 1)
        self.assertEqual([p['sorting_key'] for p in self.signing.payloads], [1, 2, 3])
        self.signing.calls.clear()
        self.assertChainVerified(deliveries)
        self.assertEqual(self.signing.calls['get_public_keys'], 1)
        self.assertEqual(self.signing.calls['verify_integrity'], 3)
