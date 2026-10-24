from unittest.mock import patch

from odoo import tools
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.l10n_pl_edi.tests.test_l10n_pl_edi import TestL10nPlEdi
from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService
from odoo.addons.l10n_pl_edi_qr_code.models.account_move import AccountMove


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlFetchPdf(TestL10nPlEdi):

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

    def test_bill_import_survives_pdf_rendering_failure(self):
        with (
            patch.object(
                AccountMove,
                '_l10n_pl_edi_store_pdf',
                side_effect=UserError('PDF rendering failed'),
            ),
            mute_logger('odoo.addons.l10n_pl_edi_qr_code.models.account_move'),
        ):
            bill = self._fetch_bill()

        self.assertEqual(bill.l10n_pl_edi_status, 'fetched')
        self.assertFalse(bill.invoice_pdf_report_id)
        self.assertTrue(bill.message_ids.filtered(
            lambda message: 'PDF visualization could not be generated' in message.body
        ))

    def test_accepted_invoice_gets_one_stored_pdf(self):
        invoice = self.standard_invoice
        invoice.action_post()
        invoice.write({
            'l10n_pl_edi_status': 'sent',
            'l10n_pl_edi_ref': 'INVOICE-REF',
            'l10n_pl_edi_session_id': 'SESSION-REF',
        })
        response = {
            'status': {'code': 200, 'description': 'Accepted'},
            'ksefNumber': self.ksef_number,
        }

        with patch.object(KsefApiService, 'get_invoice_status', return_value=response):
            invoice.action_l10n_pl_edi_update_invoice_status()
            stored_pdf = invoice.invoice_pdf_report_id
            invoice.action_l10n_pl_edi_update_invoice_status()

        self.assertTrue(stored_pdf)
        self.assertEqual(invoice.invoice_pdf_report_id, stored_pdf)
