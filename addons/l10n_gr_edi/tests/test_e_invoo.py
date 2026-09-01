import base64
from unittest.mock import MagicMock, patch

from lxml import etree

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import freeze_time, tagged


@freeze_time('2024-01-01')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEInvoo(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gr')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.write({
            'name': 'Greek Company',
            'vat': '047747270',
            'l10n_gr_edi_test_env': True,
            'l10n_gr_edi_aade_id': 'test_user',
            'l10n_gr_edi_aade_key': 'test_key',
        })
        cls.partner_a.write({
            'country_id': cls.env.ref('base.gr').id,
            'vat': '047747210',
        })
        cls.tax_24 = cls.env.ref(f'account.{cls.env.company.id}_l10n_gr_tax_s24_G')

    def _create_invoice(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-01-01',
            'date': '2024-01-01',
            'l10n_gr_edi_inv_type': '1.1',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100,
                'tax_ids': [Command.set(self.tax_24.ids)],
                'l10n_gr_edi_cls_category': 'category1_1',
                'l10n_gr_edi_cls_type': 'E3_561_001',
            })],
        })
        invoice.action_post()
        return invoice

    @staticmethod
    def _success_result():
        return {
            'upstream_status': 200,
            'response': {
                'success': True,
                'b1_auth_string': 'AUTHENTICATION-CODE',
                'provider_uid': 'PROVIDER-UID',
                'mark': '400001900000001',
                'uid': 'MYDATA-UID',
                'qrUrl': 'https://mydata.example/verify',
                'inv_identifier': 'INVOICE-IDENTIFIER',
                'provider_qrUrl': 'https://e-invoo.com/veriry/INVOICE-IDENTIFIER/PARENT-TOKEN',
            },
        }

    def _patch_proxy_user(self, *results):
        proxy_user = MagicMock()
        proxy_user._l10n_gr_edi_proxy_request.side_effect = results
        patcher = patch.object(
            self.env.registry['res.company'],
            '_l10n_gr_edi_get_proxy_user',
            return_value=proxy_user,
        )
        return patcher, proxy_user

    def test_invoice_issuance_and_final_pdf_upload(self):
        invoice = self._create_invoice()
        pdf_content = b'%PDF-1.4 final invoice'

        patcher, proxy_user = self._patch_proxy_user(
            self._success_result(),
            {
                'upstream_status': 204,
                'response': None,
            },
        )
        with patcher:
            invoice.l10n_gr_edi_try_send_invoices()

            document = invoice.l10n_gr_edi_document_ids.filtered(
                lambda document: document.state == 'invoice_sent'
            )
            self.assertEqual(len(document), 1)
            self.assertRecordValues(document, [{
                'mydata_mark': '400001900000001',
                'mydata_uid': 'MYDATA-UID',
                'mydata_authentication_code': 'AUTHENTICATION-CODE',
                'provider_uid': 'PROVIDER-UID',
                'provider_invoice_identifier': 'INVOICE-IDENTIFIER',
                'provider_pdf_state': 'pending',
            }])

            route, request_values = proxy_user._l10n_gr_edi_proxy_request.call_args_list[0].args
            self.assertEqual(route, 'send_invoice')
            self.assertEqual(
                request_values['invoice_id'],
                invoice._l10n_gr_edi_get_provider_invoice_id(),
            )
            self.assertEqual(request_values['issue_date'], '2024-01-01')
            self.assertTrue(
                request_values['xml'].startswith("<?xml version='1.0' encoding='UTF-8'")
            )

            root = etree.fromstring(request_values['xml'].encode())
            self.assertEqual(etree.QName(root).localname, 'InvoicesDoc')
            self.assertEqual(len(root.xpath('./*[local-name() = "invoice"]')), 1)

            invoice_data = {
                'pdf_attachment_values': {
                    'raw': pdf_content,
                },
            }
            self.env['account.move.send']._l10n_gr_edi_try_upload_final_pdf(invoice, invoice_data)

        route, pdf_values = proxy_user._l10n_gr_edi_proxy_request.call_args_list[1].args
        self.assertEqual(route, 'save_final_pdf')
        self.assertEqual(
            pdf_values['invoice_id'],
            invoice._l10n_gr_edi_get_provider_invoice_id(),
        )
        self.assertEqual(pdf_values['parent_token'], 'PARENT-TOKEN')
        self.assertEqual(base64.b64decode(pdf_values['pdf_b64']), pdf_content)
        self.assertEqual(document.provider_pdf_state, 'sent')
        self.assertFalse(document.provider_pdf_error)
        self.assertNotIn('error', invoice_data)

    def test_unknown_result_reuses_pending_submission(self):
        invoice = self._create_invoice()

        patcher, proxy_user = self._patch_proxy_user(None, self._success_result())
        with patcher:
            with freeze_time('2024-01-01 12:00:00'):
                invoice.l10n_gr_edi_try_send_invoices()

            pending_document = invoice.l10n_gr_edi_document_ids.filtered(
                lambda document: document.state == 'invoice_pending'
            )
            self.assertEqual(len(pending_document), 1)

            original_datetime = pending_document.datetime
            original_xml = pending_document.attachment_id.raw

            with freeze_time('2024-01-01 13:00:00'):
                invoice.l10n_gr_edi_try_send_invoices()

        sent_document = invoice.l10n_gr_edi_document_ids.filtered(
            lambda document: document.state == 'invoice_sent'
        )
        self.assertEqual(sent_document, pending_document)
        self.assertEqual(sent_document.datetime, original_datetime)
        self.assertEqual(sent_document.attachment_id.raw, original_xml)
        self.assertEqual(len(invoice.l10n_gr_edi_document_ids), 1)

        first_request = proxy_user._l10n_gr_edi_proxy_request.call_args_list[0].args[1]
        retry_request = proxy_user._l10n_gr_edi_proxy_request.call_args_list[1].args[1]
        self.assertEqual(retry_request['invoice_id'], first_request['invoice_id'])
        self.assertEqual(retry_request['invoice_datetime'], first_request['invoice_datetime'])
        self.assertEqual(retry_request['xml'], first_request['xml'])

    def test_tf_errors_start_a_fresh_submission(self):
        for error_code in ('tf1', 'tf2'):
            with self.subTest(error_code=error_code):
                invoice = self._create_invoice()

                patcher, proxy_user = self._patch_proxy_user(
                    {
                        'upstream_status': 200,
                        'response': {
                            'success': False,
                            'error': error_code,
                        },
                    },
                    self._success_result(),
                )
                with patcher:
                    invoice.l10n_gr_edi_try_send_invoices()

                    error_document = invoice.l10n_gr_edi_document_ids.filtered(
                        lambda document: document.state == 'invoice_error'
                    )
                    self.assertEqual(len(error_document), 1)
                    self.assertIn(error_code.upper(), error_document.message)

                    invoice.l10n_gr_edi_try_send_invoices()

                sent_document = invoice.l10n_gr_edi_document_ids.filtered(
                    lambda document: document.state == 'invoice_sent'
                )
                self.assertEqual(len(sent_document), 1)
                self.assertFalse(error_document.exists())
                self.assertEqual(proxy_user._l10n_gr_edi_proxy_request.call_count, 2)

    def test_issue_date_uses_current_date_in_greece(self):
        invoice = self._create_invoice()

        # 21:59 UTC is still January 1 in Athens.
        with freeze_time('2024-01-01 21:59:00'):
            errors = invoice._l10n_gr_edi_get_pre_error_dict()
            self.assertNotIn('l10n_gr_edi_invalid_issue_date', errors)

        # 22:01 UTC is January 2 in Athens.
        with freeze_time('2024-01-01 22:01:00'):
            errors = invoice._l10n_gr_edi_get_pre_error_dict()
            self.assertIn('l10n_gr_edi_invalid_issue_date', errors)
