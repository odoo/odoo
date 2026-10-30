import unittest
from datetime import datetime
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import freeze_time, tagged

from odoo.addons.l10n_pt_certification.tests.common import AT_DEMO_PUBLIC_KEY, REAL_SIGNING
from odoo.addons.l10n_pt_sale.tests.common import TestL10nPtSaleCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtSaleSignature(TestL10nPtSaleCommon):
    """
    Every quotation and sales order is signed when issued, over its date, SystemEntryDate, number and
    gross total, chained to the signature of the previous document of its series (Despacho 8632/2014
    2.1; Portaria 302/2016 4.3.4.3.5). Quotations and sales orders are two families, each with its own
    series and chain. Once signed, an order is locked: nothing it was signed over can change (Despacho
    8632/2014 1.11). The integrity check rebuilds and verifies each chain.
    """

    # -------------------------------------------------------------------------
    # Signature and integrity
    # -------------------------------------------------------------------------

    def test_signed_payload(self):
        """
        The document date signed is the order date; SystemEntryDate is the issuing time in UTC (D-9);
        the first document of a series chains to nothing.
        """
        quotation = self.make_order(date_order=datetime(2026, 6, 10, 9, 0))
        with freeze_time('2026-06-15 23:30:00'):
            self.issue(quotation)
        self.assertEqual(self.signing.calls['sign_records'], 1)
        self.assertEqual(self.signing.payloads, [{
            'model': 'sale.order',
            'id': quotation.id,
            'sorting_key': 1,
            'date': '2026-06-10',
            'system_entry_date': '2026-06-15T23:30:00',
            'name': 'OR 2026/00001',
            'gross_total': '123.00',
            'previous_signature': '',
        }])
        self.assertSignatureValid(quotation)
        self.assertQrFields(quotation, {'D': 'OR', 'F': '20260610', 'O': '123.00'})

    def test_signed_gross_total_in_eur(self):
        """An order in another currency signs its gross total in EUR, as its QR code shows it (PT-59)."""
        usd = self.setup_other_currency('USD', rates=[('2026-01-01', 2.0)])
        pricelist = self.env['product.pricelist'].create({'name': 'USD', 'currency_id': usd.id})
        quotation = self.issue(self.make_order(pricelist=pricelist))
        self.assertEqual(quotation.amount_total, 123.0)
        self.assertEqual(self.signing.payloads[0]['gross_total'], '61.50')
        self.assertSignatureValid(quotation)
        self.assertQrFields(quotation, {'O': '61.50'})

    def test_quotations_and_orders_chained_apart(self):
        """Quotations and sales orders are numbered and chained in their own series."""
        quotation_1 = self.make_order()
        sales_order_1 = self.issue(self.confirm(quotation_1))
        quotation_2 = self.issue(self.make_order())
        sales_order_2 = self.issue(self.confirm(quotation_2))
        self.assertEqual(
            (quotation_1 + quotation_2 + sales_order_1 + sales_order_2).mapped('l10n_pt_document_number'),
            ['OR 2026/00001', 'OR 2026/00002', 'NE 2026/00001', 'NE 2026/00002'],
        )
        self.assertEqual((quotation_1 + quotation_2).l10n_pt_at_series_id, self.series_or)
        self.assertEqual((sales_order_1 + sales_order_2).l10n_pt_at_series_id, self.series_ne)
        self.assertEqual(self._previous_signed(quotation_2), quotation_1)
        self.assertEqual(self._previous_signed(sales_order_2), sales_order_1)
        for order in quotation_1 + quotation_2 + sales_order_1 + sales_order_2:
            self.assertSignatureValid(order)
        self.assertChainVerified(quotation_1 + quotation_2 + sales_order_1 + sales_order_2)

    def test_batch_chained_in_number_order(self):
        """
        Orders issued together are numbered by date and chained by number: the module sends the
        series' last signature once, the service chains the batch (`sorting_key`).
        """
        quotations = (
            self.make_order(date_order=datetime(2026, 6, 12, 9, 0))
            + self.make_order(date_order=datetime(2026, 6, 10, 9, 0))
            + self.make_order(date_order=datetime(2026, 6, 11, 9, 0))
        )
        self.issue(quotations)
        self.assertEqual(quotations.mapped('l10n_pt_document_number'), ['OR 2026/00003', 'OR 2026/00001', 'OR 2026/00002'])
        self.assertEqual(self.signing.calls['sign_records'], 1)
        self.assertEqual(sorted(p['sorting_key'] for p in self.signing.payloads), [1, 2, 3])
        self.assertEqual({p['previous_signature'] for p in self.signing.payloads}, {''})
        next_quotation = self.issue(self.make_order())
        self.assertEqual(self._previous_signed(next_quotation), quotations[0])
        self.assertEqual(self.signing.payloads[-1]['previous_signature'], quotations[0].l10n_pt_inalterable_hash.split('$')[2])
        self.assertChainVerified(quotations + next_quotation)

    def test_chain_crosses_99999(self):
        """The chain follows the number in the series, not its text: …/100000 comes after …/99999 (PT-35)."""
        self.series_or._l10n_pt_get_document_number_sequence().sudo().number_next = 99999
        quotations = self.issue(self.make_order() + self.make_order())
        self.assertEqual(quotations.mapped('l10n_pt_document_number'), ['OR 2026/99999', 'OR 2026/100000'])
        self.assertEqual(quotations.mapped('l10n_pt_sequence_number'), [99999, 100000])
        next_quotation = self.issue(self.make_order())
        self.assertEqual(self._previous_signed(next_quotation), quotations[1])
        self.assertSignatureValid(next_quotation)
        self.assertChainVerified(quotations + next_quotation)

    def test_signed_fields_locked(self):
        """
        The values an order is signed over, and its series, cannot change once it is signed; its
        lines and global discount neither, the order being locked. Other fields can.
        """
        quotation = self.issue(self.make_order())
        self.assertTrue(quotation.locked)
        for field_name, value in (
            ('date_order', datetime(2026, 6, 1, 10, 0)),
            ('l10n_pt_hashed_on', datetime(2026, 6, 1, 10, 0)),
            ('name', 'S99999'),
            ('l10n_pt_document_number', 'OR 2026/00009'),
            ('amount_total', 1.0),
            ('partner_id', self.partner_foreign.id),
            ('company_id', self.company_pt_2.id),
            ('l10n_pt_at_series_id', self.series_factory(name='2026B', document_type='quotation').id),
            ('l10n_pt_inalterable_hash', '$1$forged'),
        ):
            with self.subTest(field=field_name), self.assertRaisesRegex(UserError, "protected by a hash"):
                quotation.write({field_name: value})
        with self.assertRaisesRegex(UserError, "locked order"):
            quotation.order_line.product_uom_qty = 2
        with self.assertRaisesRegex(UserError, "locked order"):
            quotation.l10n_pt_global_discount = 10.0
        quotation.write({'validity_date': '2026-07-15', 'note': 'Obrigado'})
        self.assertSignatureValid(quotation)

    @unittest.skip("PT-129 (todo): over RPC, Unlock reopens the lines of an issued order, whose total then changes")
    def test_unlocking_does_not_open_signed_values(self):
        """
        An issued order cannot be unlocked to change its lines (Despacho 8632/2014 1.11): the form
        hides Unlock for PT orders, and over RPC either the unlock or the change is refused.
        """
        quotation = self.issue(self.make_order())
        with self.assertRaises(UserError), self.env.cr.savepoint():
            quotation.action_unlock()
            quotation.order_line.product_uom_qty = 2
        self.assertEqual(quotation.amount_total, 123.0)
        self.assertChainVerified(quotation)

    def test_integrity_verified_and_tampering_detected(self):
        """Changing any signed value, or the signature, of an issued order is reported."""
        quotations = self.issue(self.make_order() + self.make_order() + self.make_order())
        self.assertChainVerified(quotations)
        for field_name, value in (
            ('amount_total', 1.0),
            ('date_order', '2026-06-01 10:00:00'),
            ('l10n_pt_document_number', 'OR 2026/00009'),
            ('l10n_pt_inalterable_hash', quotations[1].l10n_pt_inalterable_hash.replace('$1$', '$1$A')),
        ):
            with self.subTest(field=field_name), self.env.cr.savepoint() as savepoint:
                self.tamper(quotations[1], field_name, value)
                result = self.integrity_results(quotations)[self.series_or]
                self.assertEqual(result['status'], 'corrupted')
                self.assertIn(f"quotation with id {quotations[1].id}", result['msg_cover'])
                savepoint.rollback()
                self.env.invalidate_all()
        self.assertChainVerified(quotations)

    def test_integrity_report_per_document_family(self):
        """The report covers the quotation and sales order series apart, each with its first and last document."""
        quotations = self.make_order(date_order=datetime(2026, 6, 3, 9, 0)) + self.make_order(date_order=datetime(2026, 6, 5, 9, 0))
        sales_orders = self.confirm(quotations[0]) + self.confirm(quotations[1])
        self.issue(sales_orders)
        results = self.integrity_results(quotations + sales_orders)
        self.assertEqual(results[self.series_or]['msg_cover'], "Quotations are correctly hashed")
        self.assertEqual(results[self.series_ne]['msg_cover'], "Sales Orders are correctly hashed")
        for series, orders in ((self.series_or, quotations), (self.series_ne, sales_orders)):
            self.assertEqual(results[series]['first_document_number'], orders[0].l10n_pt_document_number)
            self.assertEqual(results[series]['last_document_number'], orders[1].l10n_pt_document_number)

    def test_integrity_signs_numbered_orders_only(self):
        """
        The integrity check first signs the orders numbered but not signed yet; a quotation nobody
        issued stays out of the chain, unnumbered and editable (PT-55).
        """
        issued = self.issue(self.make_order())
        numbered = self.make_order()
        numbered._set_l10n_pt_document_number()
        draft = self.make_order()
        self.assertFalse(numbered.l10n_pt_inalterable_hash)
        self.assertChainVerified(issued + numbered)
        self.assertSignatureValid(numbered)
        self.assertNotIssued(draft)
        draft.order_line.product_uom_qty = 2

    def test_integrity_report_entry_points(self):
        """The report is reached from the company, and only for a Portuguese one."""
        self.issue(self.make_order())
        action = self.company_pt.with_context(discard_logo_check=True)._l10n_pt_sale_action_check_hash_integrity()
        self.assertEqual(action['report_name'], 'l10n_pt_sale.report_hash_integrity')
        values = self.env['report.l10n_pt_sale.report_hash_integrity'].with_company(self.company_pt)._get_report_values(self.company_pt.ids)
        self.assertEqual([r['status'] for r in values['data']['results']], ['verified'])
        with self.assertRaisesRegex(UserError, "only available for Portuguese companies"):
            self.company_foreign._l10n_pt_sale_check_hash_integrity()

    # -------------------------------------------------------------------------
    # Multi-company
    # -------------------------------------------------------------------------

    def test_signed_in_own_company_chain(self):
        """An order printed while another company is active is issued in its own company's series (PT-56)."""
        self.issue(self.make_order())
        quotation = self.make_order()
        self.print_pdf(quotation.with_company(self.company_foreign))
        self.assertIssued(quotation)
        self.assertEqual(quotation.l10n_pt_at_series_id, self.series_or)
        self.assertEqual(quotation.l10n_pt_document_number, 'OR 2026/00002')
        self.assertSignatureValid(quotation)

    def test_branch_shares_root_chain(self):
        """A shared series chains the orders of the root and its branches, in one verified chain."""
        quotations = self.issue(self.make_order())
        quotations += self.issue(self.make_order(company=self.branch_pt))
        quotations += self.issue(self.make_order())
        self.assertEqual(quotations.l10n_pt_at_series_id, self.series_or)
        self.assertEqual(quotations.mapped('l10n_pt_document_number'), ['OR 2026/00001', 'OR 2026/00002', 'OR 2026/00003'])
        self.assertEqual(self._previous_signed(quotations[2]), quotations[1])
        self.assertChainVerified(quotations)

    # -------------------------------------------------------------------------
    # AT vectors
    # -------------------------------------------------------------------------

    def test_at_sample_orders_verify(self):
        """
        The working documents of the AT's demo SAF-T (saft_idemo599999999.xml), rebuilt as quotations,
        verify under the AT's demo public key against the signatures the AT published for them: the
        module signs and verifies the values the AT signs, chained as the AT chains them (Despacho
        8632/2014 2.1). Offline: the published signatures are stored, not asked of the signing service.
        """
        with (
            self.at_sample_orders() as signatures,
            patch('odoo.addons.l10n_pt_certification.utils.hashing.verify_integrity', REAL_SIGNING['verify_integrity']),
        ):
            quotations = self.env['sale.order'].concat(*signatures)
            self.assertEqual([p['gross_total'] for p in self.signing.payloads], ['56.54', '548.10'])
            for quotation, signature in signatures.items():
                self.tamper(quotation, 'l10n_pt_inalterable_hash', f'$1${signature}')
            self.signing.public_keys = {1: AT_DEMO_PUBLIC_KEY}
            self.assertChainVerified(quotations)

            self.tamper(quotations[0], 'amount_total', 56.55)
            result = self.integrity_results(quotations)[quotations.l10n_pt_at_series_id]
            self.assertEqual(result['status'], 'corrupted')
            self.assertIn(f"quotation with id {quotations[0].id}", result['msg_cover'])

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------
    # Service calls per series, not per document.

    def test_issuing_signs_a_series_in_one_call(self):
        """Issuing several orders signs each series in one call to the signing service."""
        quotations = self.make_order() + self.make_order() + self.make_order()
        self.issue(quotations)
        self.assertEqual(self.signing.calls['sign_records'], 1)
        sales_orders = self.confirm(quotations[0]) + self.confirm(quotations[1])
        self.signing.reset()
        self.issue(sales_orders + self.make_order())
        self.assertEqual(self.signing.calls['sign_records'], 2)
