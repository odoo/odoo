from unittest.mock import patch

from odoo import tools
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_pl_edi.models.account_move import AccountMove
from odoo.addons.l10n_pl_edi.tests.test_l10n_pl_edi import TestL10nPlEdiCommon
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlFetchPdf(TestL10nPlEdiCommon):

    ksef_number = '7492091229-20260210-0700A043714A-5E'

    def _fetch_bill(self):
        def get_invoice_by_ksef_number(_ksef_number):
            with tools.file_open('l10n_pl_edi/tests/export_xmls/fa3_bill.xml', mode='rb') as file:
                return {'xml_content': file.read()}

        with (
            patch.object(KsefApiService, 'query_invoice_metadata', return_value={
                'hasMore': False,
                'invoices': [{'ksefNumber': self.ksef_number}],
            }),
            patch.object(KsefApiService, 'get_invoice_by_ksef_number', side_effect=get_invoice_by_ksef_number),
        ):
            self.env['account.move'].with_company(self.company)._l10n_pl_edi_download_bills_from_ksef()

        return self.env['account.move'].search([
            ('l10n_pl_edi_number', '=', self.ksef_number),
        ])

    def test_fetched_bill_has_xml_message_pdf_and_supplier_qr(self):
        bill = self._fetch_bill()

        self.assertTrue(bill.invoice_pdf_report_id)
        self.assertTrue(bill._l10n_pl_edi_generate_qr_link())
        self.assertTrue(bill.message_ids.attachment_ids.filtered(lambda attachment: attachment.mimetype == 'application/xml'))

        report_html = self.env['ir.actions.report']._render_qweb_html(
            'account.account_invoices', bill.ids,
        )[0]
        self.assertIn(self.ksef_number.encode(), report_html)

    def test_supplier_qr_uses_the_stored_xml(self):
        bill = self._fetch_bill()
        qr_link = bill._l10n_pl_edi_generate_qr_link()
        self.assertIn('/invoice/7492091229/10-02-2026/', qr_link)

        bill.commercial_partner_id.vat = False
        bill.invoice_date = '2026-02-11'

        self.assertEqual(bill._l10n_pl_edi_generate_qr_link(), qr_link)

    def test_bill_import_survives_pdf_rendering_failure(self):
        with (
            patch.object(
                AccountMove,
                '_l10n_pl_edi_store_pdf',
                side_effect=UserError('PDF rendering failed'),
            ),
            mute_logger('odoo.addons.l10n_pl_edi.models.account_move'),
        ):
            bill = self._fetch_bill()

        self.assertEqual(bill.l10n_pl_edi_status, 'fetched')
        self.assertFalse(bill.invoice_pdf_report_id)
        self.assertTrue(bill.message_ids.filtered(
            lambda message: 'PDF visualization could not be generated' in message.body
        ))

    def test_fetched_bill_with_unreadable_xml_has_no_qr_link(self):
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_pl.id,
            'l10n_pl_edi_status': 'fetched',
            'l10n_pl_edi_number': self.ksef_number,
        })
        self.env['ir.attachment'].create({
            'name': 'unreadable.xml',
            'raw': b'not an XML',
            'mimetype': 'application/xml',
            'res_model': bill._name,
            'res_id': bill.id,
            'res_field': 'l10n_pl_edi_attachment_file',
        })
        bill.invalidate_recordset(fnames=['l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file'])

        self.assertEqual(bill._l10n_pl_edi_generate_qr_link(), '')

    def _accept_invoice(self, invoice):
        """ Run the KSeF status check of a sent invoice, KSeF answering that it is accepted. """
        response = {
            'status': {'code': 200, 'description': 'Accepted'},
            'ksefNumber': self.ksef_number,
        }
        with patch.object(KsefApiService, 'get_invoice_status', return_value=response):
            invoice.action_l10n_pl_edi_update_invoice_status()

    def _sent_invoice(self):
        invoice = self.standard_invoice
        invoice.action_post()
        invoice.write({
            'l10n_pl_edi_status': 'sent',
            'l10n_pl_edi_ref': 'INVOICE-REF',
            'l10n_pl_edi_session_id': 'SESSION-REF',
        })
        return invoice

    def _invoice_pdfs(self, invoice):
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', invoice.id),
            ('res_field', '=', 'invoice_pdf_report_file'),
        ])

    def test_accepted_invoice_without_pdf_stores_none(self):
        invoice = self._sent_invoice()

        with patch.object(self.env.registry['ir.actions.report'], '_render_qweb_pdf') as render_pdf:
            self._accept_invoice(invoice)

        self.assertEqual(invoice.l10n_pl_edi_status, 'accepted')
        render_pdf.assert_not_called()
        self.assertFalse(invoice.invoice_pdf_report_id)

    def test_accepted_invoice_replaces_its_existing_pdf(self):
        invoice = self._sent_invoice()
        old_pdf = self.env['ir.attachment'].create({
            'name': 'old.pdf',
            'raw': b'old PDF',
            'mimetype': 'application/pdf',
            'res_model': invoice._name,
            'res_id': invoice.id,
            'res_field': 'invoice_pdf_report_file',
        })
        ksef_xml = self.env['ir.attachment'].create({
            'name': 'ksef.xml',
            'raw': b'<Faktura/>',
            'mimetype': 'application/xml',
            'res_model': invoice._name,
            'res_id': invoice.id,
            'res_field': 'l10n_pl_edi_attachment_file',
        })
        invoice.invalidate_recordset(fnames=[
            'invoice_pdf_report_id',
            'invoice_pdf_report_file',
            'l10n_pl_edi_attachment_id',
            'l10n_pl_edi_attachment_file',
        ])
        invoice.message_main_attachment_id = old_pdf

        with patch.object(
            self.env.registry['ir.actions.report'], '_render_qweb_pdf', return_value=(b'new PDF', 'pdf'),
        ) as render_pdf:
            self._accept_invoice(invoice)
            new_pdf = invoice.invoice_pdf_report_id
            self._accept_invoice(invoice)

        render_pdf.assert_called_once()
        self.assertEqual(new_pdf.raw, b'new PDF')
        self.assertEqual(invoice.invoice_pdf_report_id, new_pdf)
        self.assertEqual(self._invoice_pdfs(invoice), new_pdf)
        self.assertEqual(invoice.message_main_attachment_id, new_pdf)
        # The old PDF is detached from the invoice, not deleted.
        self.assertTrue(old_pdf.exists())
        self.assertRecordValues(old_pdf, [{
            'res_model': invoice._name,
            'res_id': invoice.id,
            'res_field': False,
        }])
        self.assertIn('detached', old_pdf.name)
        self.assertEqual(invoice.l10n_pl_edi_attachment_id, ksef_xml)

    def test_send_and_print_flags_the_invoice_accepted_during_sending_as_sent(self):
        invoice = self.standard_invoice
        invoice.action_post()

        with (
            patch.object(KsefApiService, 'open_ksef_session'),
            patch.object(KsefApiService, 'send_invoice', return_value={'referenceNumber': 'INVOICE-REF'}),
            patch.object(KsefApiService, 'get_invoice_status', return_value={
                'ksefNumber': self.ksef_number,
                'status': {'code': 200},
            }),
            # The QR code image is not what is tested, only that the report shows it.
            patch.object(self.env.registry['ir.actions.report'], 'barcode', return_value=b'QR'),
        ):
            self.env['account.move.send.wizard'].with_company(self.company).create({
                'move_id': invoice.id,
                'extra_edi_checkboxes': {'pl_ksef': {'checked': True}},
            }).action_send_and_print()

        self.assertEqual(invoice.l10n_pl_edi_status, 'accepted')
        self.assertTrue(invoice.is_move_sent)
        pdf_attachments = self._invoice_pdfs(invoice)
        self.assertEqual(len(pdf_attachments), 1)
        self.assertEqual(pdf_attachments, invoice.invoice_pdf_report_id)
        self.assertEqual(invoice.message_main_attachment_id, pdf_attachments)
        self.assertIn(b'id="ksef_verification_code"', pdf_attachments.raw)
