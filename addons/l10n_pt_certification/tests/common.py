import base64
import hashlib
import itertools
from collections import Counter
from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command, fields
from odoo.models import BaseModel
from odoo.tests import freeze_time, new_test_user
from odoo.tools import SQL

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils

FAKE_PUBLIC_KEY = 'test'

# The real entry points of the signing service, bound before any test class replaces them with the fake.
REAL_SIGNING = {name: getattr(pt_hash_utils, name) for name in ('sign_records', 'get_public_keys', 'verify_integrity')}

# The AT's demo key pair signs the sample documents of its demo SAF-T, saft_idemo599999999.xml
# (https://info.portaldasfinancas.gov.pt/pt/apoio_contribuinte/Faturacao/Paginas/certificacao-de-software.aspx).
# The IAP's test signer holds the private key; the public key is enough to verify.
AT_DEMO_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDWDX9wVqj6ZqNZU1ojwBpyKKku
zHTCmfK39xx/T9vWkqpcV7h3sx++ZOv2KhhNkIe/1I4OCWDPCXRE4g0uIQr0NS29
vMlP3aHHayy76+lbBCNVcHFxM0ggjre1acnD0qUpZ6Vza7F+PpCyuypD2V/pkL1n
X9Z6z5uYyqc0XaSFdwIDAQAB
-----END PUBLIC KEY-----
"""
# Two series of that SAF-T, each its own chain: (document number, date, SystemEntryDate, gross total, signature).
AT_SAMPLE_SERIES = [
    [
        ('1T 1/1', '2017-03-10', '2017-03-10 15:58:01', 28.07, "vfinNfF+rToGp3dWF1LV6mEctQ76hAeZm+PlhBnV4wokN//N79L7fTNvi71ONnMHzfIzVR/Iz2zOOo9MUrYfYYZhqtpcEgFNHMdET6ZqbVVke7HbfqSACzaKXNdgWZt7lm7AFOfhcizQgC4a66SNvJvPJUqF7bCTUMIJFR9Zfro="),
        ('1T 1/2', '2017-09-16', '2017-09-16 15:58:10', 235.15, "jABYv0ThJHWoocmbzuLPOJXknl2WHBpLRBPqhIBSYP6GRzo3WiMxh6ryFiaa8rQD2BM9tdLxjhPHOZo1XPeGR5hFGK5BI/NzTXBu9+ponV4wvASOhjy2iomBlOxISN3MYGBcG1XWLfi+aDBw0TLrVwpbsENk0MtypYGU78OPPjg="),
        ('1T 1/3', '2017-09-16', '2017-09-16 15:58:45', 679.61, "MqvfiYZOh1L1fgfrAXBemPED1xy27MUs79vWxk/0P99Bq+jxvxwjJa3HQdElGfogj5bslcxX3ia9Tps2Oxfw1kH3GnsmfzqHbVagqnNxiI/KMZGfR4XXXNSOf7l7K7iMELz29b/c8u8eRmUwm13sgk9E9yAyk9zLuQ/s5TByG9k="),
    ],
    [
        ('2T A/1', '2017-09-16', '2017-09-16 16:02:16', 235.15, "CM1pPaqk/pTE5DajJZ3H9VejD00FL455GvHx0FjuNj3UKj1V9EkP5dPsOpB6/KXlttY1WsHGG4dcunSOKULW0FMEWAMQYxBo/HqLcIojedKxrzh6m9+P61VM4BnYxbtEBQRFdVs0MGP8X85uSc4ikPrY4OeO1UOixGR9xLIAtr4="),
        ('2T A/2', '2017-09-16', '2017-09-16 16:03:11', 2261.34, "Y7kXSvGiS1eCSU9DY1GlWHw+HMmpI/gdZKEv17EXFC7OFdOdSCwcRNPzBUB6QjB1aQ60T8+4jvQb+tSWAQJdsCoiNUMcZl+oQJKJjJTfPJTmDBlrnh0JGXaOrg4sPe1eVvjjtCKxyJ3xoQnwU/bVBjMde2Kx0zXBsBwIWoT0ukg="),
        ('2T A/3', '2017-09-16', '2017-09-16 16:04:45', 47.03, "W3Z1jj4rNG5CREwXq0ZCjaRHDqrB1U9U6NmyKZZ7VpruDsw+NxcbwUubuMgejYBCVr6OIRrUNlm1UvNuYx/EXFZpzhdoWRc7O1HPBSQFhAfhByE6QxvumsVtxSome95/cG2VmAU1MJUJTVQN4Y//snz8YaCy1/81bB7aGfUs0C0="),
    ],
]

# The AT internal code of each document type, used as the prefix of its series.
SERIES_PREFIXES = {
    'out_invoice': 'FT',
    'out_receipt': 'FS',
    'out_invoice_receipt': 'FR',
    'out_refund': 'NC',
    'debit_note': 'ND',
    'payment_receipt': 'RG',
}

# The report each document is printed with, by model.
DEFAULT_REPORTS = {
    'account.move': 'account.account_invoices',
    'account.payment': 'account.action_report_payment_receipt',
}

# AT validation codes are unique across the database: every series gets the next one.
_at_codes = (f'ATTEST{n:04d}' for n in itertools.count(1))


def fake_signature(message):
    """The signature the fake signing service gives ``message``: deterministic, 44 characters like the real one."""
    return base64.b64encode(hashlib.sha256(message.encode()).digest()).decode()


class L10nPtSigningFake:
    """
    In-process stand-in for the IAP signing service, replacing ``sign_records``, ``get_public_keys``
    and ``verify_integrity`` of ``utils.hashing``.

    The service does the RSA work; the module builds the payload, chains, stores and verifies, which
    is what the tests are about. The fake's "signature" is ``base64(sha256(message))``, the message
    built from the payload as the service builds it, so signatures and ``Q:`` are deterministic and
    ``verify_integrity`` still detects any tampering. Like the service, it chains a batch by
    ``sorting_key``: only the first document carries ``previous_signature``.

    Every payload sent to sign is recorded in ``payloads`` (with its ``model``) and every call
    counted in ``calls``. Keys can be rotated: ``public_keys`` by version, and documents are signed
    under ``signing_version``, which ``verify_integrity`` checks the key against. ``available = False``
    makes the service unreachable, as a connection error does. All of it is reset before each test.
    """

    def __init__(self):
        self.payloads = []
        self.calls = Counter()
        self.public_keys = {1: FAKE_PUBLIC_KEY}
        self.signing_version = 1
        self.available = True

    def reset(self):
        self.payloads.clear()
        self.calls.clear()
        self.public_keys = {1: FAKE_PUBLIC_KEY}
        self.signing_version = 1
        self.available = True

    def _check_available(self, env):
        if not self.available:
            raise pt_hash_utils.L10nPtSigningUnavailable(env._(pt_hash_utils.ERROR_MESSAGES['error_connecting_iap']))  # pylint: disable=gettext-variable

    def sign_records(self, env, docs_to_sign, model):
        self.calls['sign_records'] += 1
        self._check_available(env)
        self.payloads.extend({'model': model, **doc} for doc in docs_to_sign)
        res, previous = {}, None
        for doc in sorted(docs_to_sign, key=lambda d: d['sorting_key']):
            previous_signature = doc['previous_signature'] if previous is None else previous
            message = f"{doc['date']};{doc['system_entry_date']};{doc['name']};{doc['gross_total']};{previous_signature or ''}"
            previous = fake_signature(message)
            res[env[model].browse(int(doc['id']))] = f"${self.signing_version}${previous}"
        return res

    def get_public_keys(self, env):
        self.calls['get_public_keys'] += 1
        self._check_available(env)
        return dict(self.public_keys)

    def verify_integrity(self, message, inalterable_hash, public_key_string):
        self.calls['verify_integrity'] += 1
        try:
            version, signature = inalterable_hash.split('$')[1:3]
            key = self.public_keys.get(int(version))
        except (AttributeError, ValueError):
            return False
        return public_key_string == key and signature == fake_signature(message)


class L10nPtSigningFakeMixin:
    """
    Signs through ``L10nPtSigningFake`` (``cls.signing``) for the whole class. Mixed into the test
    classes of every PT module that signs documents (certification, sale, stock, PoS).
    """

    @classmethod
    def setUpClass(cls):
        # Patched after the base classes' setup, whose cleanups check that no patcher outlives the
        # class: cleanups run last first, so these must be registered after that check.
        super().setUpClass()
        cls.signing = L10nPtSigningFake()
        for name in REAL_SIGNING:
            cls.startClassPatcher(patch.object(pt_hash_utils, name, getattr(cls.signing, name)))

    def setUp(self):
        super().setUp()
        self.signing.reset()


@freeze_time('2026-06-15 10:00:00')
class TestL10nPtCommon(L10nPtSigningFakeMixin, AccountTestInvoicingCommon):
    """
    Base of the ``l10n_pt_certification`` suite, and of the PT sale, stock and PoS suites.

    Time is frozen on 2026-06-15 10:00 UTC, inside the series' year; move it with ``freeze_time``
    within a test, never backwards past a document already issued (the system clock check).

    Posting and issuing are distinct steps, as in the module: ``post()`` gives an invoice its number,
    ``issue()`` its document number, ATCUD and signature.
    """

    @classmethod
    @AccountTestInvoicingCommon.setup_country('pt')
    def setUpClass(cls):
        super().setUpClass()

        # ==== Companies ====
        cls.company_pt = cls.company_data['company']
        cls.company_pt.write({
            'street': '25 Avenida da Liberdade',
            'city': 'Lisboa',
            'zip': '1250-001',
            'company_registry': '123456',
            'phone': '+351 211 111 111',
            'vat': 'PT123456789',
        })
        # A branch issues its documents under the NIF of its root company.
        cls.branch_pt = cls._create_company(
            name='company_pt_branch',
            parent_id=cls.company_pt.id,
            street='50 Rua de Santa Catarina',
            city='Porto',
            zip='4000-447',
            vat='PT123456789',
        )
        cls.company_data_pt_2 = cls.setup_other_company(
            name='company_pt_2',
            street='1 Rua Augusta',
            city='Lisboa',
            zip='1100-053',
            vat='PT500000000',
        )
        cls.company_pt_2 = cls.company_data_pt_2['company']
        cls.company_data_foreign = cls._setup_foreign_company()
        cls.company_foreign = cls.company_data_foreign['company']

        # ==== Users ====
        cls.billing_user = new_test_user(
            cls.env,
            login='pt_billing_user',
            groups='base.group_user,account.group_account_invoice',
            company_id=cls.company_pt.id,
            company_ids=[Command.set((cls.company_pt + cls.branch_pt).ids)],
        )
        cls.readonly_user = new_test_user(
            cls.env,
            login='pt_readonly_user',
            groups='base.group_user,account.group_account_readonly',
            company_id=cls.company_pt.id,
            company_ids=[Command.set((cls.company_pt + cls.branch_pt).ids)],
        )
        cls.other_company_user = new_test_user(
            cls.env,
            login='pt_other_company_user',
            groups='base.group_user,account.group_account_invoice',
            company_id=cls.company_pt_2.id,
            company_ids=[Command.set(cls.company_pt_2.ids)],
        )

        # ==== Partners ====
        cls.partner_pt = cls.env['res.partner'].create({
            'name': 'Cliente PT',
            'street': '10 Rua do Ouro',
            'city': 'Lisboa',
            'zip': '1100-060',
            'country_id': cls.env.ref('base.pt').id,
            'vat': 'PT501964843',
            'email': 'cliente.pt@example.com',
        })
        cls.partner_foreign = cls.env['res.partner'].create({
            'name': 'Client BE',
            'street': '1 Rue de la Loi',
            'city': 'Bruxelles',
            'zip': '1000',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })

        # ==== Taxes and products ====
        cls.tax_sale_23 = cls.env['account.chart.template'].ref('iva_pt_sale_normal')
        cls.tax_sale_exempt = cls.env['account.chart.template'].ref('iva_pt_sale_eu_isenta')
        cls.product_service = cls._create_product(name='service', type='service', lst_price=50.0)

        # ==== AT series: one per document type, for 2026, communicated to the AT ====
        cls.series_ft = cls.series_factory(document_type='out_invoice')
        cls.series_fs = cls.series_factory(document_type='out_receipt')
        cls.series_fr = cls.series_factory(document_type='out_invoice_receipt')
        cls.series_nc = cls.series_factory(document_type='out_refund')
        cls.series_nd = cls.series_factory(document_type='debit_note')
        cls.series_rg = cls.series_factory(document_type='payment_receipt')

    @classmethod
    def _setup_foreign_company(cls):
        """A US company, on the generic chart, so that no other localization is needed."""
        company = cls.env['res.company'].create({
            'name': 'company_us',
            'country_id': cls.env.ref('base.us').id,
            'currency_id': cls.env.ref('base.USD').id,
        })
        cls.env.user.company_ids = [Command.link(company.id)]
        cls._use_chart_template(company, 'generic_coa')
        return cls.collect_company_accounting_data(company)

    # -------------------------------------------------------------------------
    # Factories
    # -------------------------------------------------------------------------

    @classmethod
    def series_factory(cls, **overrides):
        """
        An AT series of ``company_pt`` for 2026, shared with its branches, with an AT validation code.
        Its prefix is the AT code of its document type, its journal the company's sales journal, or
        bank journal for receipts. ``overrides`` are any field values.
        """
        vals = {
            'name': '2026',
            'document_type': 'out_invoice',
            'company_id': cls.company_pt.id,
            'date_start': '2026-01-01',
            'date_end': '2026-12-31',
            'at_code': next(_at_codes),
            **overrides,
        }
        if 'prefix' not in vals:
            vals['prefix'] = SERIES_PREFIXES[vals['document_type']]
        if 'journal_id' not in vals:
            company = cls.env['res.company'].browse(vals['company_id'])
            vals['journal_id'] = cls.env['account.journal'].search([
                *cls.env['account.journal']._check_company_domain(company),
                ('type', '=', 'bank' if vals['document_type'] == 'payment_receipt' else 'sale'),
            ], order='sequence, id', limit=1).id
        return cls.env['l10n_pt.at.series'].create(vals)

    @classmethod
    def make_invoice(cls, move_type='out_invoice', invoice_date=None, lines=None, partner=None, currency=None, company=None, **vals):
        """
        A draft invoice of ``company_pt``, dated today, to ``partner_pt``, with one 100.00 line of
        ``product_a`` at the company's 23 % (its default sales tax outside PT). ``lines`` are the
        values of each line over those defaults, records
        allowed (``{'tax_ids': cls.tax_sale_exempt}``); ``partner=False`` leaves it without a customer.
        Its AT series is left to the module to pick.
        """
        company = company or cls.company_pt
        partner = cls.partner_pt if partner is None else partner
        line_model = cls.env['account.move.line']
        default_tax = (
            cls.env['account.chart.template'].with_company(company.root_id).ref('iva_pt_sale_normal', raise_if_not_found=False)
            or company.root_id.account_sale_tax_id
        )

        def line_vals(line):
            vals = {
                'product_id': cls.product_a.id,
                'quantity': 1,
                'price_unit': 100.0,
                'tax_ids': [Command.set(default_tax.ids)],
            }
            for field_name, value in line.items():
                if isinstance(value, BaseModel):
                    value = [Command.set(value.ids)] if line_model._fields[field_name].type == 'many2many' else value.id
                vals[field_name] = value
            return vals

        return cls.env['account.move'].with_company(company).create({
            'move_type': move_type,
            'company_id': company.id,
            'partner_id': partner.id if partner else False,
            'invoice_date': invoice_date or fields.Date.today(),
            'currency_id': (currency or company.currency_id).id,
            'invoice_line_ids': [Command.create(line_vals(line)) for line in (lines or [{}])],
            **vals,
        })

    @classmethod
    def post(cls, records):
        """Post ``records``: an invoice takes its number in its series, as its name; a receipt is issued."""
        records.action_post()
        return records

    @classmethod
    def issue(cls, records):
        """Issue the posted ``records``: document number, ATCUD and signature, as their first print would."""
        if records._name == 'account.move':
            records._l10n_pt_issue()
        else:
            records._l10n_pt_compute_missing_hashes()
        return records

    @classmethod
    def make_receipt(cls, invoices, amount=None, date=None, journal=None):
        """One receipt (RG) paying ``invoices``, through Register Payment, in the environment of ``invoices``."""
        wizard = invoices.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoices.ids,
        ).create({
            'payment_date': date or fields.Date.today(),
            'journal_id': (journal or cls.company_data['default_journal_bank']).id,
            'group_payment': True,
            **({'amount': amount} if amount is not None else {}),
        })
        return wizard._create_payments()

    @classmethod
    def reverse(cls, move, reason='Devolução de mercadoria', date=None):
        """The draft credit note of ``move`` made by the reversal wizard, in the environment of ``move``."""
        wizard = move.env['account.move.reversal'].with_context(
            active_model='account.move',
            active_ids=move.ids,
        ).create({
            'reason': reason,
            'journal_id': move.journal_id.id,
            'date': date or fields.Date.today(),
        })
        wizard.reverse_moves()
        return wizard.new_move_ids

    @classmethod
    def print_pdf(cls, records, report=None):
        """
        Print ``records`` as a PDF is printed, which counts as their print (Original, then 2ª Via).
        Without wkhtmltopdf in tests, core hands back the HTML the PDF would be made of.
        """
        content, _report_type = records.env['ir.actions.report']._render_qweb_pdf(
            report or DEFAULT_REPORTS[records._name], records.ids,
        )
        return content.decode()

    @classmethod
    def preview(cls, records, report=None):
        """Render ``records`` as an HTML preview, which is not a print."""
        content, _report_type = records.env['ir.actions.report']._render_qweb_html(
            report or DEFAULT_REPORTS[records._name], records.ids,
        )
        return content.decode()

    @classmethod
    def tamper(cls, record, field_name, value):
        """Change a stored value behind the ORM's back, as direct database access would."""
        record.flush_recordset()
        record.env.execute_query(SQL(
            "UPDATE %s SET %s = %s WHERE id = %s",
            SQL.identifier(record._table), SQL.identifier(field_name), value, record.id,
        ))
        record.invalidate_recordset()

    @contextmanager
    def at_sample_documents(self):
        """
        The documents of the AT's demo SAF-T (``AT_SAMPLE_SERIES``), as invoices of two 2017 FT series,
        each issued at its SystemEntryDate and exempt of VAT, so that its gross total is its price.
        Yields ``{invoice: signature}``, the signature the AT published for each. The AT numbers them
        ``1T 1/1``, the module ``FT 2017/00001``: within the context, what is signed and verified
        carries the AT's number; every other value is the module's.
        """
        AccountMove = self.registry['account.move']
        get_document_number = AccountMove._l10n_pt_get_document_number
        at_numbers, signatures = {}, {}

        def document_number(move):
            return at_numbers.get(move.id) or get_document_number(move)

        with patch.object(AccountMove, '_l10n_pt_get_document_number', document_number):
            for name, documents in zip(('2017', '2017A'), AT_SAMPLE_SERIES):
                series = self.series_factory(name=name, date_start='2017-01-01', date_end='2017-12-31')
                for number, document_date, system_entry_date, gross_total, signature in documents:
                    with freeze_time(system_entry_date):
                        invoice = self.post(self.make_invoice(
                            invoice_date=document_date,
                            lines=[{'price_unit': gross_total, 'tax_ids': self.tax_sale_exempt}],
                            l10n_pt_at_series_id=series.id,
                        ))
                        at_numbers[invoice.id] = number
                        self.issue(invoice)
                    signatures[invoice] = signature
            yield signatures

    # -------------------------------------------------------------------------
    # Assertions
    # -------------------------------------------------------------------------

    def assertIssued(self, records):
        """Each of ``records`` holds its document number, ATCUD, issuer and, if signed, its signature."""
        for record in records:
            msg = f"{record._name}({record.id}) {record.display_name} is not issued"
            self.assertTrue(record.l10n_pt_document_number, msg)
            self.assertEqual(
                record.l10n_pt_atcud,
                f"{record.l10n_pt_at_series_id.at_code}-{record._l10n_pt_get_sequence_number()}",
                msg,
            )
            self.assertTrue(record.l10n_pt_issue_user_id, msg)
            self.assertTrue(record.l10n_pt_issued_on, msg)
            if record._name == 'account.move':
                self.assertEqual(record.l10n_pt_document_number, record.name, msg)
            if hash_field := getattr(record, '_l10n_pt_hash_field', None):
                self.assertTrue(record[hash_field], msg)
                self.assertTrue(record.l10n_pt_hashed_on, msg)

    def assertNotIssued(self, records):
        """None of ``records`` holds a document number, ATCUD or signature."""
        for record in records:
            msg = f"{record._name}({record.id}) {record.display_name} is issued"
            self.assertFalse(record.l10n_pt_document_number, msg)
            self.assertFalse(record.l10n_pt_atcud, msg)
            if hash_field := getattr(record, '_l10n_pt_hash_field', None):
                self.assertFalse(record[hash_field], msg)

    def _previous_signed(self, record):
        """The document signed just before ``record`` in its series' chain."""
        sequence_field = 'sequence_number' if record._name == 'account.move' else 'l10n_pt_sequence_number'
        # sudo: a series shared across branches chains documents of companies the user may not see.
        return record.env[record._name].sudo().search([
            ('l10n_pt_at_series_id', '=', record.l10n_pt_at_series_id.id),
            (sequence_field, '<', record[sequence_field]),
            (record._l10n_pt_hash_field, '!=', False),
        ], order=f'{sequence_field} desc', limit=1)

    def assertSignatureValid(self, record):
        """
        ``record``'s signature is the one its current values, rebuilt through
        ``_l10n_pt_get_hash_values``, and the previous document's signature are signed into.
        """
        hash_field = record._l10n_pt_hash_field
        previous = self._previous_signed(record)
        previous_signature = previous[hash_field].split('$')[2] if previous else ''
        message = pt_hash_utils.get_message_to_hash(record._l10n_pt_get_hash_values(), previous_signature)
        self.assertEqual(record[hash_field].split('$')[2], fake_signature(message), f"Invalid signature of {record.display_name}")

    @classmethod
    def qr_fields(cls, record):
        """The fields of ``record``'s QR code string, e.g. ``{'A': '123456789', 'I7': '100.00', ...}``."""
        return dict(field.split(':', 1) for field in record.l10n_pt_qr_code_str.split('*'))

    def assertQrFields(self, record, expected):
        """``record``'s QR code holds the ``expected`` fields, ``{'A': '123456789', ...}``; ``None`` for an absent field."""
        self.assertTrue(record.l10n_pt_qr_code_str, f"{record.display_name} has no QR code")
        qr_fields = self.qr_fields(record)
        self.assertEqual({key: qr_fields.get(key) for key in expected}, expected)

    def integrity_results(self, records):
        """
        The integrity report's result of each AT series of ``records``, as ``{series: result}``. Run as
        the class's accountant: the report is an accountant's tool, whoever made the documents.
        """
        records = records.with_env(self.env)
        company = records.company_id.root_id[:1]
        if records._name == 'account.move':
            # Core reports per journal and sequence prefix, e.g. "Customer Invoices (FT 2026/...)".
            results = company._check_hash_integrity()['results']
            return {
                series: next((r for r in results if f"({series.document_identifier}/...)" in r['journal_name']), None)
                for series in records.l10n_pt_at_series_id
            }
        results = records.env[records._name]._l10n_pt_check_hash_integrity(company)['results']
        return {
            series: next((r for r in results if r.get('series_document_identifier') == series.document_identifier), None)
            for series in records.l10n_pt_at_series_id
        }

    def assertChainVerified(self, records):
        """The integrity report verifies the whole chain of each AT series of ``records``."""
        for series, result in self.integrity_results(records).items():
            self.assertTrue(result, f"The integrity report does not cover {series.document_identifier}")
            self.assertEqual(result['status'], 'verified', result['msg_cover'])
