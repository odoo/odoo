from datetime import date
from unittest.mock import patch

from odoo.exceptions import ConcurrencyError, UserError
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_pt_certification.controllers.portal import L10nPtPortalAccount
from odoo.addons.l10n_pt_certification.tests.common import TestL10nPtCommon

ORIGINAL = '<span id="l10n_pt_print_version">Original</span>'
REPRINT = '<span id="l10n_pt_print_version">2ª Via</span>'
CANCELLED = 'Documento Cancelado'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtPrinting(TestL10nPtCommon):
    """
    What the customer receives: the printed document and its QR code.

    A document's first print is its Original; every later print is a "2ª Via" that keeps the content
    of the original, marked once the document is cancelled, and asks for a reason (Despacho
    8632/2014 2.2.15, 2.2.16; FAQ 2764). Only a print counts: an HTML preview does not.

    Every PT document prints a QR code built from its fields, as the AT specifies them (Portaria
    195/2020; QR code specification v1.1). Signatures being deterministic, values are literal.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template']
        cls.tax_sale_13 = ChartTemplate.ref('iva_pt_sale_intermedia')
        cls.tax_sale_6 = ChartTemplate.ref('iva_pt_sale_reduzida')
        cls.tax_sale_azores_16 = ChartTemplate.ref('iva_pt_ac_sale_normal')
        cls.tax_sale_not_subject = cls.env['account.tax'].create({
            'name': 'Não sujeito', 'amount': 0.0, 'type_tax_use': 'sale',
            'tax_group_id': cls.tax_sale_exempt.tax_group_id.id, 'l10n_pt_tax_exemption_reason': 'M99',
        })

    # -------------------------------------------------------------------------
    # Printing
    # -------------------------------------------------------------------------

    def _attachments(self, records):
        return self.env['l10n.pt.attachment'].sudo().search([('res_model', '=', records._name), ('res_id', 'in', records.ids)])

    def test_original_then_reprint(self):
        """The first print, of any invoice report, is the Original; the next, of any report, the 2ª Via."""
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        first = self.print_pdf(invoice)
        self.assertIn(ORIGINAL, first)
        self.assertEqual(invoice.l10n_pt_print_version, 'original')
        second = self.print_pdf(invoice, 'account.account_invoices_without_payment')
        self.assertIn(REPRINT, second)
        self.assertNotIn(ORIGINAL, second)
        self.assertEqual(invoice.l10n_pt_print_version, 'reprint')
        self.assertIn(REPRINT, self.print_pdf(invoice))
        self.assertEqual(len(self._attachments(invoice)), 2)

    def test_preview_stores_nothing(self):
        """An HTML preview issues the invoice but is not a print: nothing stored, the next print is the Original."""
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        self.assertIn(ORIGINAL, self.preview(invoice))
        self.assertIssued(invoice)
        self.assertFalse(invoice.l10n_pt_print_version)
        self.assertFalse(self._attachments(invoice))
        self.assertIn(ORIGINAL, self.print_pdf(invoice))

    def test_print_menu_renders_nothing(self):
        """Opening the Print menu of a never-printed invoice renders, prints and issues nothing (PT-104)."""
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        items = invoice.get_extra_print_items()
        self.assertTrue(items)
        self.assertFalse(invoice.l10n_pt_print_version)
        self.assertFalse(self._attachments(invoice))
        self.assertNotIssued(invoice)

    def test_reprint_keeps_original_content(self):
        """A reprint serves the content of the original print, even after the customer changed."""
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        self.assertIn('Cliente PT', self.print_pdf(invoice))
        self.partner_pt.name = 'Novo Nome Lda'
        reprint = self.print_pdf(invoice)
        self.assertIn('Cliente PT', reprint)
        self.assertNotIn('Novo Nome Lda', reprint)

    def test_cancelled_documents(self):
        """A cancelled document reprints as a 2ª Via marked "Documento Cancelado", receipts included."""
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        self.assertNotIn(CANCELLED, self.print_pdf(invoice))
        receipt = self.make_receipt(self.issue(self.post(self.make_invoice())).with_user(self.billing_user))
        self.assertNotIn(CANCELLED, self.print_pdf(receipt))
        invoice.button_cancel()
        receipt.action_cancel()
        for document in (invoice, receipt):
            with self.subTest(document=document.display_name):
                html = self.print_pdf(document)
                self.assertIn(REPRINT, html)
                self.assertIn(CANCELLED, html)

    def test_stored_prints_by_company(self):
        """
        A user of another company cannot read a company's stored prints; printing with another company
        active still serves the original (PT-116).
        """
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        self.print_pdf(invoice)
        attachments = self._attachments(invoice)
        self.assertEqual(attachments.company_id, self.company_pt)
        self.assertFalse(self.env['l10n.pt.attachment'].with_user(self.other_company_user).search([('id', 'in', attachments.ids)]))
        both = self.env.user.with_context(allowed_company_ids=(self.company_pt_2 + self.company_pt).ids)
        self.assertIn(REPRINT, self.print_pdf(invoice.with_env(both.env)))
        self.assertEqual(self._attachments(invoice), attachments)

    def test_reprint_reason(self):
        """
        Printing again asks for a reason, logged in the chatter; the wizard then resumes the print it
        was opened for, and only a known print action (PT-115).
        """
        invoice = self.post(self.make_invoice()).with_user(self.billing_user)
        self.assertEqual(invoice.action_print_pdf()['type'], 'ir.actions.report')
        self.print_pdf(invoice)
        action = invoice.action_print_pdf()
        self.assertEqual((action['res_model'], action['context']['action_to_return']), ('l10n_pt.reprint.reason', 'action_print_pdf'))

        def run_wizard(model, records, action_to_return, reason='Cliente perdeu o original'):
            return self.env['l10n_pt.reprint.reason'].with_user(self.billing_user).with_context(
                active_model=model, active_ids=records.ids, action_to_return=action_to_return,
            ).create({'reason': reason}).action_log_and_print()

        result = run_wizard('account.move', invoice, 'action_print_pdf')
        self.assertTrue(result['close_on_report_download'])
        self.assertIn('Cliente perdeu o original', invoice.message_ids[:1].body)
        with self.assertRaisesRegex(UserError, "cannot be printed from here"):
            run_wizard('account.move', invoice, 'button_cancel')
        with self.assertRaisesRegex(UserError, "cannot be printed from here"):
            run_wizard('account.move', invoice, 'action_send_and_print')

        send_wizard = self.env['account.move.send.wizard'].with_user(self.billing_user).create({'move_id': invoice.id, 'sending_methods': ['email']})
        run_wizard('account.move.send.wizard', send_wizard, 'action_send_and_print', reason='Reenvio')
        self.assertIn('Reenvio', invoice.message_ids.filtered(lambda m: 'Reenvio' in str(m.body))[:1].body)

        receipt = self.make_receipt(invoice)
        self.print_pdf(receipt)
        self.assertEqual(receipt.with_user(self.billing_user).action_open_reprint_wizard()['res_model'], 'l10n_pt.reprint.reason')
        self.assertEqual(run_wizard('account.payment', receipt, None)['report_name'], 'account.report_payment_receipt')

    def test_render_without_ids_or_with_an_int(self):
        """Reports render for a single int id, and for no record at all, as core accepts (PT-109)."""
        invoice = self.issue(self.post(self.make_invoice()))
        Report = self.env['ir.actions.report']
        Report._pre_render_qweb_pdf('account.account_invoices', res_ids=invoice.id)
        Report._pre_render_qweb_pdf('account.action_report_account_hash_integrity', res_ids=None, data={})

    def test_mixed_companies_refused(self):
        """
        Invoices of PT and non-PT companies cannot be printed together in one document; the report
        with payments renders each invoice apart, and is not concerned.
        """
        invoice = self.post(self.make_invoice())
        foreign = self.post(self.make_invoice(company=self.company_foreign, partner=self.partner_foreign, lines=[
            {'tax_ids': self.company_data_foreign['default_tax_sale']},
        ]))
        env = self.env(context={**self.env.context, 'allowed_company_ids': (self.company_pt + self.company_foreign).ids})
        with self.assertRaisesRegex(UserError, "not possible to print documents with the template"):
            self.print_pdf((invoice + foreign).with_env(env), 'account.account_invoices_without_payment')

    def test_partner_language_date_format_alert(self):
        """Sending warns when the customer's language prints dates in a format the AT does not accept."""
        invoice = self.issue(self.post(self.make_invoice()))
        self.env['res.lang']._activate_lang('en_US')
        self.partner_pt.lang = 'en_US'
        wizard = self.env['account.move.send.wizard'].create({'move_id': invoice.id})
        self.assertIn('l10n_pt_configure_partner_language', wizard.alerts)
        self.partner_pt.lang = False
        wizard = self.env['account.move.send.wizard'].create({'move_id': invoice.id})
        self.assertNotIn('l10n_pt_configure_partner_language', wizard.alerts or {})

    # -------------------------------------------------------------------------
    # QR code
    # -------------------------------------------------------------------------

    def test_mainland_invoice(self):
        """A mainland FT: every field, in order (spec v1.1 section 4)."""
        invoice = self.issue(self.post(self.make_invoice()))
        self.assertEqual(
            invoice.l10n_pt_qr_code_str,
            f"A:123456789*B:501964843*C:PT*D:FT*E:N*F:20260615*G:FT 2026/00001*H:{self.series_ft.at_code}-1*"
            "I1:PT*I7:100.00*I8:23.00*N:23.00*O:123.00*Q:EEGz*R:9999",
        )

    def test_rates_and_regions(self):
        """
        Bases and VAT per rate (reduced I3/I4, intermediate I5/I6, normal I7/I8, exempt I2) per region;
        another region's taxes go to the J block, and N/O sum every block (PT-71).
        """
        invoice = self.issue(self.post(self.make_invoice(lines=[
            {'tax_ids': self.tax_sale_6, 'price_unit': 10.0},
            {'tax_ids': self.tax_sale_13, 'price_unit': 20.0},
            {'tax_ids': self.tax_sale_23, 'price_unit': 30.0},
            {'tax_ids': self.tax_sale_exempt, 'price_unit': 40.0},
            {'tax_ids': self.tax_sale_azores_16, 'price_unit': 50.0},
        ])))
        self.assertQrFields(invoice, {
            'I1': 'PT', 'I2': '40.00', 'I3': '10.00', 'I4': '0.60', 'I5': '20.00', 'I6': '2.60', 'I7': '30.00', 'I8': '6.90',
            'J1': 'PT-AC', 'J2': None, 'J7': '50.00', 'J8': '8.00',
            'K1': None, 'L': None, 'N': '18.10', 'O': '168.10',
        })

    def test_azores_company(self):
        """A company in the Azores leads with its region; a 0 % tax, valid in all regions, is the company's (PT-71)."""
        self.company_pt.state_id = self.env.ref('base.state_pt_pt-20')
        self.assertEqual(self.company_pt.l10n_pt_region_code, 'PT-AC')
        invoice = self.issue(self.post(self.make_invoice(lines=[
            {'tax_ids': self.tax_sale_azores_16},
            {'tax_ids': self.tax_sale_exempt},
            {'tax_ids': self.tax_sale_23},
        ])))
        self.assertQrFields(invoice, {'I1': 'PT-AC', 'I2': '100.00', 'I7': '100.00', 'I8': '16.00', 'J1': 'PT', 'J7': '100.00', 'J8': '23.00'})

    def test_not_subject(self):
        """
        Bases not subject to VAT (M99, M12-M15) are in L, apart from the exempt ones in I2 (PT-72).
        Withholding (P) comes with `l10n_pt_saft_withholding`, and is tested there.
        """
        invoice = self.issue(self.post(self.make_invoice(lines=[
            {'tax_ids': self.tax_sale_not_subject},
            {'tax_ids': self.tax_sale_exempt},
            {'tax_ids': self.tax_sale_23},
        ])))
        self.assertQrFields(invoice, {'I1': 'PT', 'I2': '100.00', 'I7': '100.00', 'I8': '23.00', 'L': '100.00', 'P': None})
        only_not_subject = self.issue(self.post(self.make_invoice(lines=[{'tax_ids': self.tax_sale_not_subject}])))
        self.assertQrFields(only_not_subject, {'I1': 'PT', 'I2': None, 'L': '100.00', 'N': '0.00', 'O': '100.00'})

    def test_customer_fields(self):
        """
        A foreign tax number is printed as collected, without its country prefix (PT-74); no customer
        is 999999990 in an unknown country.
        """
        dutch = self.env['res.partner'].create({'name': 'Klant NL', 'vat': 'NL000099998B57', 'country_id': self.env.ref('base.nl').id})
        no_country = self.env['res.partner'].create({'name': 'Cliente sem país', 'vat': 'PT501964843'})
        invoices = self.issue(self.post(
            self.make_invoice(partner=dutch, lines=[{'tax_ids': self.tax_sale_exempt}])
            + self.make_invoice(partner=no_country)
        ))
        anonymous = self.issue(self.post(self.make_invoice('out_receipt', partner=False)))
        self.assertQrFields(invoices[0], {'B': '000099998B57', 'C': 'NL'})
        self.assertQrFields(invoices[1], {'B': '501964843', 'C': 'Desconhecido'})
        self.assertQrFields(anonymous, {'B': '999999990', 'C': 'Desconhecido', 'D': 'FS'})

    def test_document_types_and_status(self):
        """D carries the SAF-T type of the document; E says whether it is annulled."""
        invoice = self.issue(self.post(self.make_invoice()))
        credit_note = self.issue(self.post(self.reverse(invoice)))
        cancelled = self.post(self.make_invoice())
        cancelled.button_cancel()
        self.assertQrFields(credit_note, {'D': 'NC', 'E': 'N', 'G': 'NC 2026/00001'})
        self.assertQrFields(cancelled, {'D': 'FT', 'E': 'A'})

    def test_foreign_currency_in_eur(self):
        """Amounts of a foreign-currency document are in EUR: O equals the gross total signed (PT-101)."""
        usd = self.setup_other_currency('USD', rates=[('2026-01-01', 2.0)])
        invoice = self.issue(self.post(self.make_invoice(currency=usd)))
        self.assertQrFields(invoice, {'I7': '50.00', 'I8': '11.50', 'N': '11.50', 'O': '61.50'})
        self.assertEqual(self.signing.payloads[0]['gross_total'], '61.50')

    def test_foreign_currency_dates_differ(self):
        """
        With an accounting date apart from the invoice date and a rate change between, the QR converts at
        the invoice date, as core converts the signed total: O still equals what was signed (PT-123).
        """
        usd = self.setup_other_currency('USD', rates=[('2026-01-01', 2.0), ('2026-06-12', 4.0)])
        invoice = self.issue(self.post(self.make_invoice(currency=usd, invoice_date=date(2026, 6, 10), date=date(2026, 6, 15))))
        self.assertEqual(self.signing.payloads[0]['gross_total'], '61.50')
        self.assertQrFields(invoice, {'I7': '50.00', 'I8': '11.50', 'N': '11.50', 'O': '61.50'})

    def test_prerequisites(self):
        """The QR code is only built for a signed document with an ATCUD: what is missing is named."""
        invoice = self.post(self.make_invoice())
        with self.assertRaisesRegex(UserError, "(?s)`ATCUD` is not defined.*`hash` is not defined"):
            invoice._l10n_pt_verify_prerequisites_qr_code()
        self.assertFalse(invoice.l10n_pt_qr_code_str)

    def test_stored_once_signed(self):
        """The QR code is stored as soon as the invoice is signed, without anything reading it (PT-10)."""
        invoice = self.issue(self.post(self.make_invoice()))
        self.env.flush_all()
        self.env.cr.execute("SELECT l10n_pt_qr_code_str FROM account_move WHERE id = %s", [invoice.id])
        self.assertTrue(self.env.cr.fetchone()[0].startswith('A:123456789*'))

    # -------------------------------------------------------------------------
    # Concurrency
    # -------------------------------------------------------------------------
    # Two first prints of one document at once (PT-17). The race is reproduced deterministically: the
    # second transaction's snapshot predates the first's commit, so it does not see the stored original.
    # Two real connections would need committed PT companies and charts; the shell script in PT-17's
    # log did that once.

    @mute_logger('odoo.sql_db')
    def test_concurrent_first_prints(self):
        """
        The second of two concurrent first prints fails with a concurrency error, which the request
        retries (`odoo.service.model.retrying`); retried, it is a reprint, and one original is stored.
        """
        invoice = self.issue(self.post(self.make_invoice())).with_user(self.billing_user)
        self.print_pdf(invoice)
        Attachment = self.registry['l10n.pt.attachment']
        search = Attachment.search

        def stale_search(records, domain, *args, **kwargs):
            # The concurrent transaction's view: the original was committed after its snapshot.
            return records.browse() if ('res_id', '=', invoice.id) in domain else search(records, domain, *args, **kwargs)

        with (
            patch.object(Attachment, 'search', stale_search),
            self.assertRaisesRegex(ConcurrencyError, "Concurrent first print"),
            self.env.cr.savepoint(),
        ):
            # Nor has it seen the print version the first print set.
            invoice.l10n_pt_print_version = False
            self.print_pdf(invoice)
        invoice.invalidate_recordset()
        self.assertIn('2ª Via', self.print_pdf(invoice))
        self.assertEqual(self.env['l10n.pt.attachment'].sudo().search_count([
            ('res_model', '=', 'account.move'), ('res_id', '=', invoice.id),
        ]), 1)

    # -------------------------------------------------------------------------
    # Performance
    # -------------------------------------------------------------------------
    # Measured as independence from the number of lines rather than as an exact budget.

    def _count_queries(self, function):
        """The queries ``function`` runs from a cold record cache, the registry's caches (access rules) warm."""
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.env.cr.sql_log_count
        function()
        self.env.flush_all()
        return self.env.cr.sql_log_count - before

    def test_qr_tax_details_independent_of_lines(self):
        """The QR tax details read the tax groups together, however many lines and groups (PT-119)."""
        def qr_queries(line_count):
            invoice = self.issue(self.post(self.make_invoice(lines=[{'price_unit': 10.0 + i} for i in range(line_count)])))
            return self._count_queries(invoice._l10n_pt_get_tax_details_by_region)

        qr_queries(1)  # warm-up
        self.assertEqual(qr_queries(1), qr_queries(6))


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nPtPortal(TestL10nPtCommon, HttpCase):
    """
    A PT invoice reaches its customer once it is issued, never before (FAQ R23): the portal does not
    list, count, show or pay an invoice posted but not issued, and browsing it issues nothing.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_user = new_test_user(cls.env, login='pt_portal', groups='base.group_portal', partner_id=cls.partner_pt.id, name=cls.partner_pt.name)
        # Both overdue.
        cls.issued = cls.issue(cls.post(cls.make_invoice(invoice_date=date(2026, 5, 1), invoice_date_due=date(2026, 5, 31))))
        cls.unissued = cls.post(cls.make_invoice(invoice_date=date(2026, 5, 2), invoice_date_due=date(2026, 5, 31)))

    def test_invoice_list_and_overdue_count(self):
        """The invoice list and the overdue invoices (counted on /my, paid at once) leave out unissued invoices."""
        self.authenticate('pt_portal', 'pt_portal')
        page = self.url_open('/my/invoices').text
        self.assertIn(self.issued.name, page)
        self.assertNotIn(self.unissued.name, page)
        overdue = self.env['account.move'].search(L10nPtPortalAccount()._get_overdue_invoices_domain(partner_id=self.partner_pt.id))
        self.assertIn(self.issued, overdue)
        self.assertNotIn(self.unissued, overdue)
        self.assertNotIssued(self.unissued)

    def test_invoice_page(self):
        """The customer is sent back from an unissued invoice's page; an internal user still sees it."""
        self.authenticate('pt_portal', 'pt_portal')
        response = self.url_open(f'/my/invoices/{self.unissued.id}')
        self.assertTrue(response.url.endswith('/my'), response.url)
        response = self.url_open(f'/my/invoices/{self.issued.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.issued.name, response.text)

        self.authenticate(self.env.user.login, self.env.user.login)
        response = self.url_open(f'/my/invoices/{self.unissued.id}')
        self.assertFalse(response.url.endswith('/my'), response.url)
        self.assertNotIssued(self.unissued)
