import json
import unittest
from datetime import date, datetime
from unittest.mock import patch

import requests

from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.tests import freeze_time, new_test_user, tagged

from odoo.addons.l10n_pt_certification.tests.common import AT_DEMO_PUBLIC_KEY, TestL10nPtCommon

# The real functions, bound before the test classes patch the module with the signing fake.
from odoo.addons.l10n_pt_certification.utils.hashing import (
    L10nPtSigningUnavailable,
    get_message_to_hash,
    get_public_keys,
    sign_records,
    verify_integrity,
)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtSignature(TestL10nPtCommon):
    """
    Every invoice is signed when issued, over its date, SystemEntryDate, number and gross total,
    chained to the signature of the previous document of its series (Despacho 8632/2014 2.1; FAQ R23);
    the integrity check rebuilds and verifies that chain. The signing service does the RSA work: the
    tests sign through a fake of it, except the cryptography test and the client of the service.
    """

    # -------------------------------------------------------------------------
    # Signature and integrity
    # -------------------------------------------------------------------------

    def test_signed_payload(self):
        """
        The document date signed is the invoice date, not the accounting date (PT-6); SystemEntryDate
        is the issuing time in UTC (D-9); the first document of a series chains to nothing.
        """
        invoice = self.post(self.make_invoice(invoice_date=date(2026, 6, 10), date=date(2026, 6, 12)))
        self.assertNotEqual(invoice.date, invoice.invoice_date)
        with freeze_time('2026-06-15 23:30:00'):
            self.issue(invoice)
        self.assertEqual(self.signing.calls['sign_records'], 1)
        self.assertEqual(self.signing.payloads, [{
            'model': 'account.move',
            'id': invoice.id,
            'sorting_key': 1,
            'date': '2026-06-10',
            'system_entry_date': '2026-06-15T23:30:00',
            'name': 'FT 2026/00001',
            'gross_total': '123.00',
            'previous_signature': '',
        }])
        self.assertSignatureValid(invoice)
        self.assertQrFields(invoice, {'F': '20260610'})

    def test_signed_gross_total_in_eur(self):
        """A foreign-currency invoice signs its gross total in EUR, as the SAF-T exports it (PT-101)."""
        usd = self.setup_other_currency('USD', rates=[('2026-01-01', 2.0)])
        invoice = self.issue(self.post(self.make_invoice(currency=usd)))
        self.assertEqual(invoice.amount_total, 123.0)
        self.assertEqual(self.signing.payloads[0]['gross_total'], '61.50')
        self.assertSignatureValid(invoice)
        self.assertQrFields(invoice, {'O': '61.50'})

    def test_batch_chained_in_number_order(self):
        """
        Invoices issued together are numbered by date and chained by number: the module sends the
        series' last signature once, the service chains the batch (`sorting_key`).
        """
        invoices = self.post(
            self.make_invoice(invoice_date=date(2026, 6, 12))
            + self.make_invoice(invoice_date=date(2026, 6, 10))
            + self.make_invoice(invoice_date=date(2026, 6, 11))
        )
        self.assertEqual(invoices.mapped('name'), ['FT 2026/00003', 'FT 2026/00001', 'FT 2026/00002'])
        self.issue(invoices)
        self.assertEqual(self.signing.calls['sign_records'], 1)
        self.assertEqual(sorted(p['sorting_key'] for p in self.signing.payloads), [1, 2, 3])
        self.assertEqual({p['previous_signature'] for p in self.signing.payloads}, {''})
        for invoice in invoices:
            self.assertSignatureValid(invoice)

        self.signing.reset()
        last = self.issue(self.post(self.make_invoice()))
        self.assertEqual(self.signing.payloads[0]['previous_signature'], invoices[0].inalterable_hash.split('$')[2])
        self.assertSignatureValid(last)
        self.assertChainVerified(invoices + last)

    def test_chain_crosses_99999(self):
        """The chain follows the number in the series, not its text: …/100000 comes after …/99999 (PT-35)."""
        self.series_ft._l10n_pt_get_document_number_sequence().sudo().number_next = 99999
        invoices = self.post(self.make_invoice() + self.make_invoice())
        self.assertEqual(invoices.mapped('name'), ['FT 2026/99999', 'FT 2026/100000'])
        # Issuing refuses the 99,998 numbers this test skips; the chain is what is under test.
        with patch.object(self.registry['account.move'], '_l10n_pt_check_series_continuity', lambda self: None):
            self.issue(invoices)
        self.assertEqual(sorted(p['sorting_key'] for p in self.signing.payloads), [99999, 100000])
        self.assertSignatureValid(invoices[1])
        self.assertEqual(self._previous_signed(invoices[1]), invoices[0])
        self.assertChainVerified(invoices)

    def test_hash_domain(self):
        """
        Core's chain takes the issued invoices, annulled ones included, and no invoice posted but not
        issued yet (PT-105); it stays a `Domain`, which core combines with others.
        """
        domain = self.env['account.move']._get_move_hash_domain(force_hash=True)
        self.assertIsInstance(domain, Domain)
        issued = self.issue(self.post(self.make_invoice()))
        annulled = self.post(self.make_invoice())
        annulled.button_cancel()
        unissued = self.post(self.make_invoice())
        in_chain = self.env['account.move'].search(domain & Domain('id', 'in', (issued + annulled + unissued).ids))
        self.assertEqual(in_chain, issued + annulled)

    def test_signed_fields_locked(self):
        """The values an invoice is signed over cannot change once it is signed; other fields can."""
        invoice = self.issue(self.post(self.make_invoice()))
        for field_name, value in (
            ('invoice_date', date(2026, 6, 1)),
            ('l10n_pt_hashed_on', datetime(2026, 6, 1, 10, 0)),
            ('amount_total_signed', 1.0),
            ('move_type', 'out_refund'),
            ('l10n_pt_document_number', 'FT 2026/00009'),
            ('inalterable_hash', '$1$forged'),
        ):
            with self.subTest(field=field_name), self.assertRaisesRegex(UserError, "protected by a hash"):
                invoice.write({field_name: value})
        with self.assertRaisesRegex(UserError, "cannot be changed"):
            invoice.name = 'FT 2026/00009'
        invoice.write({'ref': 'PO 42', 'narration': 'Obrigado'})
        self.assertSignatureValid(invoice)

    def test_integrity_verified_and_tampering_detected(self):
        """Changing any signed value, or the signature, of an issued invoice is reported."""
        invoices = self.issue(self.post(self.make_invoice() + self.make_invoice() + self.make_invoice()))
        self.assertChainVerified(invoices)
        for field_name, value in (
            ('amount_total_signed', 1.0),
            ('invoice_date', '2026-06-01'),
            ('l10n_pt_document_number', 'FT 2026/00009'),
            ('inalterable_hash', invoices[0].inalterable_hash.replace('$1$', '$1$A')),
        ):
            with self.subTest(field=field_name), self.env.cr.savepoint() as savepoint:
                self.tamper(invoices[1], field_name, value)
                result = self.integrity_results(invoices)[self.series_ft]
                self.assertEqual(result['status'], 'corrupted')
                self.assertIn(invoices[1].name, result['msg_cover'])
                savepoint.rollback()
                self.env.invalidate_all()
        self.assertChainVerified(invoices)

    def test_integrity_stops_at_first_corruption(self):
        """The report names the first corrupted invoice of a series and stops there."""
        invoices = self.issue(self.post(self.make_invoice() + self.make_invoice() + self.make_invoice()))
        self.tamper(invoices[0], 'amount_total_signed', 1.0)
        self.tamper(invoices[2], 'amount_total_signed', 1.0)
        self.signing.reset()
        result = self.integrity_results(invoices)[self.series_ft]
        self.assertEqual(result['status'], 'corrupted')
        self.assertIn(f"id {invoices[0].id} ({invoices[0].name})", result['msg_cover'])
        self.assertEqual(self.signing.calls['verify_integrity'], 1)

    def test_integrity_report_signs_missing_hashes(self):
        """
        Rendering the integrity report first signs the issued invoices still unsigned, and checks no
        invoice by the company ids it is rendered for (PT-110); an unissued invoice stays unissued.
        """
        issued = self.issue(self.post(self.make_invoice()))
        self.tamper(issued, 'inalterable_hash', None)
        unissued = self.post(self.make_invoice())
        self.env['ir.actions.report']._render_qweb_html('account.action_report_account_hash_integrity', self.company_pt.ids)
        self.assertTrue(issued.inalterable_hash)
        self.assertSignatureValid(issued)
        self.assertNotIssued(unissued)
        self.assertChainVerified(issued)

    def test_integrity_includes_ended_series(self):
        """The invoices of a series that has ended are still verified."""
        series_2025 = self.series_factory(name='2025', date_start='2025-01-01', date_end='2025-12-31')
        with freeze_time('2025-12-30 10:00:00'):
            invoice = self.issue(self.post(self.make_invoice()))
        # `active` is not stored: its value computed in 2025 is still cached.
        self.env.invalidate_all()
        self.assertEqual(invoice.l10n_pt_at_series_id, series_2025)
        self.assertFalse(series_2025.active)
        self.assertChainVerified(invoice)

    def test_integrity_access_error(self):
        """
        A series shared with a branch holds invoices of both: an accountant who may see the branch is
        asked to select it, one who may not gets the access error as is (PT-118).
        """
        # Each posted in its own company: a recordset keeps the companies allowed to its first record.
        invoices = self.issue(self.post(self.make_invoice())) + self.issue(self.post(self.make_invoice(company=self.branch_pt)))
        self.assertEqual(invoices.l10n_pt_at_series_id, self.series_ft)
        groups = 'base.group_user,account.group_account_user'
        accountant = new_test_user(
            self.env, login='pt_accountant', groups=groups, company_id=self.company_pt.id,
            company_ids=[(6, 0, (self.company_pt + self.branch_pt).ids)],
        )
        root_accountant = new_test_user(
            self.env, login='pt_root_accountant', groups=groups, company_id=self.company_pt.id,
            company_ids=[(6, 0, self.company_pt.ids)],
        )
        company = self.company_pt.with_context(allowed_company_ids=self.company_pt.ids)
        # A refused report rolls back its request, which closes the SQL cursor the walk left open.
        with self.assertRaisesRegex(UserError, "please also select company_pt_branch"), self.env.cr.savepoint():
            company.with_user(accountant)._check_hash_integrity()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            company.with_user(root_accountant)._check_hash_integrity()

    @unittest.skip("PT-4 (parked): verification always uses the first public key, whatever the $version$ of the signature")
    def test_older_key_version_still_verifies(self):
        """After a key rotation, invoices signed under either key verify in one chain (PT-4)."""
        first = self.issue(self.post(self.make_invoice()))
        self.signing.public_keys[2] = 'test-v2'
        self.signing.signing_version = 2
        second = self.issue(self.post(self.make_invoice()))
        self.assertTrue(second.inalterable_hash.startswith('$2$'))
        self.assertChainVerified(first + second)

    # -------------------------------------------------------------------------
    # Cryptography
    # -------------------------------------------------------------------------

    def test_verify_integrity(self):
        """
        The one test of the real cryptography: the signed message the module rebuilds, verified against
        a fixed RSA-1024 public key and a signature made by it (RSA-SHA1, PKCS#1 v1.5, Despacho 8632/2014
        2.1). Everything else signs through the fake.
        """
        FIXTURE_PUBLIC_KEY = (
            "-----BEGIN PUBLIC KEY-----\n"
            "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDLkocpHm45WrPN5MQ1ILoQ+qZL\n"
            "InQJzUyn7WqXuJ3VTJa11c/AcySeER3mQPrKRtFCfrA4rYuNaczIaRoHvIM/sLBM\n"
            "JZxaSpmHlraw21k0Snjg6jmV9dLVO0KgZcy0cyAwI2SGJLyRYbaKc8hI1er+nZTm\n"
            "Agvjbnk0eHP+G1+O7QIDAQAB\n"
            "-----END PUBLIC KEY-----\n"
        )
        FIXTURE_MESSAGE = "2026-06-15;2026-06-15T10:00:00;FT 2026/1;123.00;"
        # RSA-1024 / SHA-1 / PKCS#1 v1.5 signature of FIXTURE_MESSAGE, as the signing service makes it.
        FIXTURE_SIGNATURE = (
            "nxdevPDT2etn8WVwxro78ftiwAz5iOkmvhxfPft97u4EkDxdzDoq24QTWrR9OPKRv5x9YVgZQSP2QQEYzR0Whbm0gHpc"
            "gUv17sckd7grMQFA5Pd6eBj8wgQKeuFRHBJRcijSaYrf0xCBDx/B8oFWW2LelyqgU69VNmHmhVbzurw="
        )

        message = get_message_to_hash({
            'date': date(2026, 6, 15),
            'system_entry_date': datetime(2026, 6, 15, 10, 0),
            'document_number': 'FT 2026/1',
            'gross_total': 123.0,
        }, '')
        self.assertEqual(message, FIXTURE_MESSAGE)
        self.assertTrue(verify_integrity(message, f'$1${FIXTURE_SIGNATURE}', FIXTURE_PUBLIC_KEY))
        self.assertFalse(verify_integrity(message.replace('123.00', '124.00'), f'$1${FIXTURE_SIGNATURE}', FIXTURE_PUBLIC_KEY))
        self.assertFalse(verify_integrity(message, f'$1$A{FIXTURE_SIGNATURE[1:]}', FIXTURE_PUBLIC_KEY))
        self.assertFalse(verify_integrity(message, FIXTURE_SIGNATURE, FIXTURE_PUBLIC_KEY))
        self.assertFalse(verify_integrity(message, '$1$not base64!', FIXTURE_PUBLIC_KEY))

    def test_at_sample_documents_verify(self):
        """
        The documents of the AT's demo SAF-T (saft_idemo599999999.xml), rebuilt as invoices, verify
        under the AT's demo public key against the signatures the AT published for them: the module
        signs and verifies the values the AT signs, chained as the AT chains them (Despacho 8632/2014
        2.1). Offline: the published signatures are stored, not asked of the signing service.
        """
        with (
            self.at_sample_documents() as signatures,
            patch('odoo.addons.l10n_pt_certification.utils.hashing.verify_integrity', verify_integrity),
        ):
            invoices = self.env['account.move'].concat(*signatures)
            for invoice, signature in signatures.items():
                self.tamper(invoice, 'inalterable_hash', f'$1${signature}')
            self.signing.public_keys = {1: AT_DEMO_PUBLIC_KEY}
            self.assertChainVerified(invoices)

            self.tamper(invoices[1], 'amount_total_signed', 235.16)
            results = self.integrity_results(invoices)
            self.assertEqual(results[invoices[0].l10n_pt_at_series_id]['status'], 'corrupted')
            self.assertEqual(results[invoices[3].l10n_pt_at_series_id]['status'], 'verified')

    # -------------------------------------------------------------------------
    # Signing service client
    # -------------------------------------------------------------------------
    # How the module talks to the signing service: its answers and failures, with the HTTP layer mocked.

    def _iap_answer(self, result=None, side_effect=None):
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({'result': result or {}}).encode()
        return patch.object(requests, 'post', return_value=response, side_effect=side_effect)

    def test_sign_records(self):
        """The service's signatures are stored with their key version, keyed by record."""
        invoice = self.post(self.make_invoice())
        with self._iap_answer({str(invoice.id): {'signature': 'c2lnbmF0dXJl', 'signature_version': 2}}) as post:
            result = sign_records(self.env, [{'id': invoice.id}], 'account.move')
        self.assertEqual(result, {invoice: '$2$c2lnbmF0dXJl'})
        self.assertTrue(post.call_args.args[0].endswith('/sign_documents'))
        self.assertEqual(post.call_args.kwargs['json']['params']['model'], 'account.move')
        with self._iap_answer({'1': 'KEY1', '2': 'KEY2'}):
            self.assertEqual(get_public_keys(self.env), {1: 'KEY1', 2: 'KEY2'})

    def test_error_codes(self):
        """Each error the service returns is explained; an unknown one is named."""
        for error, message in (
            ('error_db_unknown', "This database is not known by Odoo"),
            ('error_db_no_subscription', "does not have a valid subscription"),
            ('error_db_not_production', "is not a production database"),
            ('error_db_not_activated', "is not activated"),
            ('error_documents_not_provided', "No documents were provided to sign"),
            ('error_documents_wrong_format', "not in the correct format"),
            ('error_brand_new', "Unknown error error_brand_new"),
        ):
            with self.subTest(error=error), self._iap_answer({'error': error}), self.assertRaisesRegex(UserError, message):
                get_public_keys(self.env)

    def test_service_unreachable(self):
        """A connection failure, a timeout or an HTTP error raise `L10nPtSigningUnavailable`: issuing may succeed later."""
        for error in (requests.exceptions.ConnectionError(), requests.exceptions.Timeout()):
            with self.subTest(error=type(error).__name__), self._iap_answer(side_effect=error), \
                    self.assertRaisesRegex(L10nPtSigningUnavailable, "Unable to connect"):
                get_public_keys(self.env)
        response = requests.Response()
        response.status_code = 502
        with patch.object(requests, 'post', return_value=response), self.assertRaises(L10nPtSigningUnavailable):
            get_public_keys(self.env)

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------
    # Service calls per series or check, not per document.

    def test_public_keys_fetched_once_per_check(self):
        """An integrity check fetches the signing service's public keys once, whatever the number of documents and series."""
        invoices = self.issue(self.post(self.make_invoice() + self.make_invoice() + self.make_invoice('out_receipt')))
        self.signing.reset()
        self.assertChainVerified(invoices)
        self.assertEqual(self.signing.calls['get_public_keys'], 1)
        self.assertEqual(self.signing.calls['verify_integrity'], 3)

    def test_issuing_signs_a_series_in_one_call(self):
        """Issuing a batch signs each series in one call to the signing service."""
        invoices = self.post(self.env['account.move'].concat(*(self.make_invoice() for _i in range(5))))
        self.issue(invoices)
        self.assertEqual(self.signing.calls['sign_records'], 1)
        self.assertEqual(len(self.signing.payloads), 5)
