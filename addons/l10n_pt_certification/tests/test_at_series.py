from datetime import date

from psycopg2.errors import UniqueViolation

from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tests import freeze_time, new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtAtSeries(TestL10nPtCommon):
    """
    An AT series is communicated to the AT, which returns its validation code (Portaria 195/2020); it
    numbers one document type without gaps, and once used it is frozen and kept, closed by its end
    date (Despacho 8632/2014 1.9, 2.5.1; FAQ 4327).

    Branches issue under their root company's NIF, in series they may share with it; independent
    companies keep their own series and chains. Every rule over a series (gaps, dates, use) holds over
    all the documents it holds, whichever companies the user may see.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = 'base.group_user,account.group_account_invoice'
        cls.root_only_user = new_test_user(
            cls.env, login='pt_root_only', groups=groups, company_id=cls.company_pt.id, company_ids=[(6, 0, cls.company_pt.ids)],
        )
        cls.branch_only_user = new_test_user(
            cls.env, login='pt_branch_only', groups=groups, company_id=cls.branch_pt.id, company_ids=[(6, 0, cls.branch_pt.ids)],
        )

    # -------------------------------------------------------------------------
    # Series
    # -------------------------------------------------------------------------

    def test_name_and_prefix_alphanumeric(self):
        """Name and prefix are made of letters and digits: they form the document number."""
        for vals, message in (
            ({'name': '2026 B'}, "name of the series"),
            ({'name': '2026/B'}, "name of the series"),
            ({'name': '2026B', 'prefix': 'F-T'}, "prefix of the series"),
        ):
            with self.subTest(vals=vals), self.assertRaisesRegex(ValidationError, message), self.env.cr.savepoint():
                self.series_factory(**vals)

    @mute_logger('odoo.sql_db')
    def test_uniqueness(self):
        """
        A name is unique per document type and company, whatever its case (PT-111); a prefix per name;
        an AT code everywhere. The same name serves another type, and another company.
        """
        for vals in (
            {'name': '2026', 'prefix': 'FT2'},
            {'name': '2026', 'prefix': 'FTX'},
            {'name': '2026', 'document_type': 'debit_note', 'prefix': 'FT'},
            {'name': '2026B', 'at_code': self.series_ft.at_code},
        ):
            with self.subTest(vals=vals), self.assertRaises(UniqueViolation), self.env.cr.savepoint():
                self.series_factory(**vals)
        self.assertTrue(self.series_factory(name='2026B'))
        with self.assertRaises(UniqueViolation), self.env.cr.savepoint():
            self.series_factory(name='2026b')
        self.assertTrue(self.series_factory(document_type='out_invoice', company_id=self.company_pt_2.id))

    def test_journal_required(self):
        """A receipt series needs a payment journal, an invoice series a sales journal."""
        with self.assertRaisesRegex(ValidationError, "A Payment Journal is required"):
            self.series_factory(name='2026B', document_type='payment_receipt', journal_id=False)
        with self.assertRaisesRegex(ValidationError, "A Sales Journal is required"):
            self.series_factory(name='2026B', journal_id=False)

    def test_active_follows_end_date(self):
        """
        `active` says whether the series is still open today: it follows its end date, also within the
        transaction that changes it (PT-113), and searches agree.
        """
        Series = self.env['l10n_pt.at.series'].with_context(active_test=False)
        ended = self.series_factory(name='2025', date_start='2025-01-01', date_end='2025-12-31')
        open_ended = self.series_factory(name='2026B', date_end=False)
        ends_today = self.series_factory(name='2026C', date_end='2026-06-15')
        self.assertEqual((ended + open_ended + ends_today).mapped('active'), [False, True, True])
        self.assertEqual(Series.search([('active', '=', False), ('id', 'in', (ended + open_ended + ends_today).ids)]), ended)
        self.assertEqual(Series.search([('active', '=', True), ('id', 'in', (ended + open_ended + ends_today).ids)]), open_ended + ends_today)
        ends_today.date_end = date(2026, 6, 14)
        self.assertFalse(ends_today.active)
        with freeze_time('2026-06-16'):
            self.env.invalidate_all()
            self.assertEqual(self.series_ft.active, True)
            self.assertFalse(Series.search([('active', '=', False), ('id', '=', ends_today.id)]) != ends_today)

    def test_validity_window(self):
        """`_l10n_pt_is_valid_on` and `_l10n_pt_validity_domain` agree, bounds included."""
        Series = self.env['l10n_pt.at.series']
        for day, valid in ((date(2025, 12, 31), False), (date(2026, 1, 1), True), (date(2026, 12, 31), True), (date(2027, 1, 1), False)):
            with self.subTest(day=day):
                self.assertEqual(self.series_ft._l10n_pt_is_valid_on(day), valid)
                self.assertEqual(bool(Series.search([('id', '=', self.series_ft.id), *Series._l10n_pt_validity_domain(day)])), valid)

    def test_company_domain(self):
        """A branch uses its parent's shared series and its own exclusive ones, not its parent's exclusive ones."""
        Series = self.env['l10n_pt.at.series']
        exclusive_parent = self.series_factory(name='2026E', company_exclusive_series=True)
        exclusive_branch = self.series_factory(name='2026R', company_id=self.branch_pt.id, company_exclusive_series=True, journal_id=self.company_data['default_journal_sale'].id)
        series = self.series_ft + exclusive_parent + exclusive_branch
        self.assertEqual(Series.search([('id', 'in', series.ids), *Series._l10n_pt_company_domain(self.branch_pt)]), self.series_ft + exclusive_branch)
        self.assertEqual(Series.search([('id', 'in', series.ids), *Series._l10n_pt_company_domain(self.company_pt)]), self.series_ft + exclusive_parent)

    def test_used_series_frozen(self):
        """
        A series in which a document took its number -- a draft invoice back from posting, a receipt
        being processed, a cancelled invoice -- keeps its properties and code and is not deleted; an
        unused one is free.
        """
        origin = self.issue(self.post(self.make_invoice()))
        draft = self.post(self.make_invoice())
        draft.button_draft()
        # Not matched to any invoice yet: the receipt is still being processed.
        receipt = self.post(self.env['account.payment'].create({
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_pt.id,
            'amount': 50.0,
            'journal_id': self.company_data['default_journal_bank'].id,
        }))
        cancelled = self.post(self.reverse(origin))
        cancelled.button_cancel()
        self.assertEqual(receipt.state, 'in_process')
        for series in self.series_ft + self.series_rg + self.series_nc:
            with self.subTest(series=series.document_identifier):
                for field_name, value in (
                    ('prefix', 'XX'), ('name', '2026Z'), ('document_type', 'debit_note'), ('date_start', '2026-02-01'),
                    ('training_series', True), ('journal_id', self.company_data['default_journal_misc'].id),
                    ('company_exclusive_series', True), ('company_id', self.company_pt_2.id),
                ):
                    with self.assertRaisesRegex(UserError, "cannot change the properties of a series"):
                        series.write({field_name: value})
                with self.assertRaisesRegex(UserError, "cannot change the AT Validation Code"):
                    series.at_code = 'ATOTHER'
                with self.assertRaisesRegex(UserError, "cannot delete a series in which documents were already issued"):
                    series.unlink()
        self.series_fr.write({'name': '2026Z', 'at_code': 'ATOTHER'})
        self.series_fr.unlink()

    def test_closing(self):
        """
        A used series is closed by its end date, from its last document's date on (PT-63); it can be
        moved while open, not removed, and not reopened once ended.
        """
        self.post(self.make_invoice(invoice_date=date(2026, 6, 10)))
        with self.assertRaisesRegex(UserError, "cannot end before its last document"):
            self.series_ft.date_end = date(2026, 6, 9)
        self.series_ft.date_end = date(2026, 6, 30)
        with self.assertRaisesRegex(UserError, "cannot be removed"):
            self.series_ft.date_end = False
        self.series_ft.date_end = date(2026, 6, 10)
        self.assertFalse(self.series_ft.active)
        with self.assertRaisesRegex(UserError, "has ended and cannot be reopened"):
            self.series_ft.date_end = date(2026, 12, 31)

    def test_number_sequence(self):
        """One gapless sequence per series, created once, numbering past 99999 (PT-35)."""
        sequence = self.series_ft._l10n_pt_get_document_number_sequence()
        self.assertEqual(sequence, self.series_ft._l10n_pt_get_document_number_sequence())
        self.assertRecordValues(sequence, [{'implementation': 'no_gap', 'prefix': 'FT 2026/', 'padding': 5}])
        sequence.sudo().number_next = 99999
        self.assertEqual([sequence.next_by_id(), sequence.next_by_id()], ['FT 2026/99999', 'FT 2026/100000'])

    def test_missing_code(self):
        """A series without AT code opens its form to register it; one with a code gives it, also once ended (PT-108, per D-22)."""
        series = self.series_factory(name='2026B', at_code=False)
        with self.assertRaisesRegex(RedirectWarning, "has no AT validation code yet") as cm:
            series._get_at_code()
        self.assertEqual((cm.exception.args[1]['res_model'], cm.exception.args[1]['res_id']), ('l10n_pt.at.series', series.id))
        ended = self.series_factory(name='2025', date_start='2025-01-01', date_end='2025-12-31')
        self.assertEqual(ended._get_at_code(), ended.at_code)

    def test_form_defaults(self):
        """The series form asked for by one document type presets it; unticking Exclusive resets the company."""
        Series = self.env['l10n_pt.at.series']
        self.assertEqual(Series.with_context(l10n_pt_series_document_types=['out_refund']).default_get(['document_type']), {'document_type': 'out_refund'})
        self.assertFalse(Series.with_context(l10n_pt_series_document_types=['out_refund', 'debit_note']).default_get(['document_type']).get('document_type'))
        series = Series.new({'company_id': self.branch_pt.id, 'company_exclusive_series': True})
        series._onchange_company_exclusive_series()
        self.assertEqual(series.company_id, self.branch_pt)
        series.company_exclusive_series = False
        series._onchange_company_exclusive_series()
        self.assertEqual(series.company_id, self.env.company)

    def test_prepare_series_vals(self):
        """
        The series a move would need is derived from its sequence: per year, month or year range; a
        name another series of the company holds for the type or prefix gets the journal's code (PT-122).
        """
        journal = self.company_data['default_journal_sale']
        for name, invoice_date, expected in (
            ('FT 2027/00001', date(2027, 6, 15), {'name': '2027', 'prefix': 'FT', 'date_start': '2027-01-01', 'date_end': '2027-12-31'}),
            ('FT 2027A/00001', date(2027, 6, 15), {'name': '2027A', 'prefix': 'FT', 'date_start': '2027-01-01', 'date_end': '2027-12-31'}),
            ('FT 2027/06/0001', date(2027, 6, 15), {'name': '202706', 'prefix': 'FT', 'date_start': '2027-06-01', 'date_end': '2027-06-30'}),
            ('XX 2026/00001', date(2026, 6, 15), {'name': f'{journal.code.upper()}2026', 'prefix': 'XX'}),
            ('FT 2026B/00001', date(2026, 6, 15), {'name': '2026B', 'prefix': 'FT'}),
        ):
            with self.subTest(name=name):
                move = self.env['account.move'].new({
                    'move_type': 'out_invoice', 'journal_id': journal.id, 'invoice_date': invoice_date, 'date': invoice_date, 'name': name,
                })
                vals = move._l10n_pt_prepare_at_series_vals()
                self.assertEqual({key: vals[key] for key in expected}, expected)
                self.assertEqual((vals['document_type'], vals['journal_id'], vals['company_id']), ('out_invoice', journal.id, self.company_pt.id))

    # -------------------------------------------------------------------------
    # Multi-company
    # -------------------------------------------------------------------------

    def test_shared_and_exclusive_series(self):
        """A branch numbers in its parent's shared series, not in its exclusive ones, and in its own."""
        branch_invoice = self.issue(self.post(self.make_invoice(company=self.branch_pt)))
        self.assertEqual(branch_invoice.l10n_pt_at_series_id, self.series_ft)
        self.assertEqual(branch_invoice.name, 'FT 2026/00001')
        self.assertEqual(self.post(self.make_invoice()).name, 'FT 2026/00002')

        self.series_fs.company_exclusive_series = True
        with self.assertRaisesRegex(RedirectWarning, "There is no AT series"):
            self.post(self.make_invoice('out_receipt', company=self.branch_pt))
        branch_fs = self.series_factory(name='2026PORTO', document_type='out_receipt', company_id=self.branch_pt.id, company_exclusive_series=True, journal_id=self.company_data['default_journal_sale'].id)
        self.assertEqual(self.post(self.make_invoice('out_receipt', company=self.branch_pt)).l10n_pt_at_series_id, branch_fs)
        self.assertEqual(self.post(self.make_invoice('out_receipt')).l10n_pt_at_series_id, self.series_fs)

    def test_signed_in_own_company_chain(self):
        """Invoices of two companies issued together are each signed in their own company's chain, whatever company is active."""
        series_pt_2 = self.series_factory(company_id=self.company_pt_2.id)
        invoice_pt = self.post(self.make_invoice())
        invoice_pt_2 = self.post(self.make_invoice(company=self.company_pt_2))
        self.assertEqual(invoice_pt_2.l10n_pt_at_series_id, series_pt_2)
        both = (invoice_pt + invoice_pt_2).with_context(allowed_company_ids=(self.company_pt + self.company_pt_2).ids)
        self.issue(both)
        self.assertIssued(invoice_pt + invoice_pt_2)
        self.assertEqual({p['previous_signature'] for p in self.signing.payloads}, {''})
        self.assertChainVerified(invoice_pt)
        self.assertChainVerified(invoice_pt_2)

    def test_series_rules_see_every_branch(self):
        """
        A user of the root only cannot see the branch's invoices, yet the series' chronology and use
        count them, and issuing the root's invoice issues the branch's before it (PT-128).
        """
        branch_invoice = self.post(self.make_invoice(company=self.branch_pt, invoice_date=date(2026, 6, 20)))
        root_invoice = self.make_invoice().with_user(self.root_only_user)
        with self.assertRaisesRegex(UserError, "dated earlier than the last document issued in this AT series"):
            self.post(root_invoice)
        root_invoice.invoice_date = date(2026, 6, 20)
        self.post(root_invoice)
        self.print_pdf(root_invoice)
        self.assertIssued(root_invoice)
        self.assertIssued(branch_invoice)
        self.assertEqual(branch_invoice.l10n_pt_issue_user_id, self.root_only_user)
        self.assertChainVerified(branch_invoice + root_invoice)
        manager = new_test_user(
            self.env, login='pt_root_manager', groups='base.group_user,account.group_account_manager',
            company_id=self.company_pt.id, company_ids=[(6, 0, self.company_pt.ids)],
        )
        with self.assertRaisesRegex(UserError, "cannot change the properties of a series"):
            self.series_ft.with_user(manager).write({'name': '2026X'})

    def test_integrity_across_branches(self):
        """A shared series chains the invoices of the root and its branches, in one verified chain."""
        invoices = self.issue(self.post(self.make_invoice()))
        invoices += self.issue(self.post(self.make_invoice(company=self.branch_pt)))
        invoices += self.issue(self.post(self.make_invoice()))
        self.assertEqual(invoices.mapped('name'), ['FT 2026/00001', 'FT 2026/00002', 'FT 2026/00003'])
        self.assertEqual(self._previous_signed(invoices[2]), invoices[1])
        self.assertChainVerified(invoices)

    def test_series_visibility(self):
        """A user sees the series of its companies and of their parents, not another company's."""
        series_pt_2 = self.series_factory(company_id=self.company_pt_2.id)
        Series = self.env['l10n_pt.at.series']
        self.assertIn(self.series_ft, Series.with_user(self.branch_only_user).search([]))
        self.assertNotIn(series_pt_2, Series.with_user(self.branch_only_user).search([]))
        self.assertEqual(Series.with_user(self.other_company_user).search([]), series_pt_2)
