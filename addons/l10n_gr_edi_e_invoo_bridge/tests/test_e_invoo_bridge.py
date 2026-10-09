import base64
from lxml import etree
from unittest.mock import patch

from odoo import Command
from odoo.tests import freeze_time, tagged
from odoo.addons.l10n_gr_edi import utils
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move import E_INVOO_TOKEN_NOT_SET


@freeze_time('2024-01-01')
@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyDATAInvoiceEInvooDirect(AccountTestInvoicingCommon):

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
            'l10n_gr_edi_methodoos_api_token': 'token',
        })
        cls.partner_a.write({
            'country_id': cls.env.ref('base.gr').id,
            'vat': '047747210',
        })
        cls.env['res.company'].create({
            'name': 'Greece Partner A',
            'partner_id': cls.partner_a.id,
            'l10n_gr_edi_test_env': True,
        })
        cls.tax_24 = cls.env.ref("account.%s_l10n_gr_tax_s24_G" % cls.env.company.id)
        cls.tax_0 = cls.env.ref("account.%s_l10n_gr_tax_s0_exempt" % cls.env.company.id)

    def _create_mydata_invoice(
            self,
            inv_type='1.1',
            tax_ids=False,
            cls_category='category1_1',
            cls_type='E3_561_001',
            post=True,
            paid=True,
            **kwargs,
    ):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-01-01',
            'date': '2024-01-01',
            'l10n_gr_edi_inv_type': inv_type,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'tax_ids': tax_ids or [Command.set(self.tax_24.ids)],
                'l10n_gr_edi_cls_category': cls_category,
                'l10n_gr_edi_cls_type': cls_type,
            })],
            **kwargs,
        })
        if post:
            invoice.action_post()
        if paid:
            self.env['account.payment.register'] \
                .with_context(active_ids=invoice.ids, active_model='account.move') \
                .create({'payment_date': invoice.date}) \
                ._create_payments()

        return invoice

    def assert_mydata_error(self, invoice, expected_error_message):
        """
        :param account.move invoice:
        :param str expected_error_message:
        """
        document = invoice.l10n_gr_edi_document_ids.sorted()[0]
        self.assertRecordValues(document, [{
            'state': 'invoice_error' if invoice.is_sale_document(include_receipts=True) else 'bill_error',
            'message': expected_error_message,
        }])

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

    def test_l10n_gr_edi_try_send_invoices_no_credentials_and_vat(self):
        self.company_data['company'].write({
            'l10n_gr_edi_aade_id': False,
            'l10n_gr_edi_aade_key': False,
        })
        invoice = self._create_mydata_invoice()
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, "You need to set AADE ID and Key in the company settings.")

    def test_l10n_gr_edi_try_send_invoices_no_token(self):
        self.company_data['company'].l10n_gr_edi_methodoos_api_token = False
        invoice = self._create_mydata_invoice()
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, str(E_INVOO_TOKEN_NOT_SET))

    def test_l10n_gr_edi_try_send_invoices_no_classification(self):
        # No invoice type
        invoice = self._create_mydata_invoice()
        invoice.l10n_gr_edi_inv_type = False
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing myDATA Invoice Type.')

        # No classification category
        invoice = self._create_mydata_invoice(cls_category=False)
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing myDATA classification category on line 1.')

        # No classification type, and inv_type + cls_category combination doesn't allow empty cls_type
        invoice = self._create_mydata_invoice(cls_type=False)
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing myDATA classification type on line 1.')

    def test_l10n_gr_edi_try_send_invoices_allowed_no_cls_type(self):
        """Allow no cls_type on some combinations with available cls_type"""
        allowed_inv_type_category = (('1.1', 'category1_95'), ('3.2', 'category1_95'), ('5.1', 'category1_95'))
        for inv_type, category in allowed_inv_type_category:
            invoice = self._create_mydata_invoice(inv_type=inv_type, cls_category=category, cls_type=False)
            self.assertFalse(utils.get_pre_error_string(invoice._l10n_gr_edi_get_pre_error_dict()))

    def test_l10n_gr_edi_try_send_invoices_invalid_tax_amount(self):
        """ Invalid tax amount should raises error. """
        invalid_tax = self.env['account.tax'].create([{
            'name': 'Bad 12%',
            'type_tax_use': 'sale',
            'amount': 12.0,
            'company_id': self.env.company.id,
        }])
        invoice = self._create_mydata_invoice(tax_ids=[Command.set(invalid_tax.ids)])
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Invalid tax amount for line 1. The valid values are 24, 13, 6, 17, 9, 4, 3, 0.')

    def test_l10n_gr_edi_try_send_invoices_invalid_tax_multi(self):
        """ Multiple tax should raises error. """
        invoice = self._create_mydata_invoice(tax_ids=[Command.set((self.tax_24 + self.tax_0).ids)])
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'myDATA does not support multiple taxes on line 1.')

    def test_l10n_gr_edi_try_send_invoices_invalid_tax_nonexistent(self):
        """ No tax should raises error. """
        invoice = self._create_mydata_invoice(post=False)
        invoice.invoice_line_ids.tax_ids = False
        invoice.action_post()
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing tax on line 1.')

    def test_l10n_gr_edi_try_send_invoices_invalid_tax_exempt_no_category(self):
        """ Tax 0% and no tax exemption category should raises error. """
        invoice = self._create_mydata_invoice(tax_ids=[Command.set(self.tax_0.ids)])
        invoice.with_context(skip_readonly_check=True).invoice_line_ids.l10n_gr_edi_tax_exemption_category = False
        invoice.l10n_gr_edi_try_send_invoices()
        self.assert_mydata_error(invoice, 'Missing myDATA Tax Exemption Category for line 1.')

    @patch('odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move.AccountMove._l10n_gr_edi_issue_invoice')
    @patch('odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move.AccountMove._l10n_gr_edi_post_e_invoo')
    def test_invoice_issuance_and_final_pdf_upload(self, mock_post_e_invoo, mock_issue_invoice):
        mock_issue_invoice.return_value = self._success_result()
        mock_post_e_invoo.return_value = {
            'upstream_status': 204,
            'response': None,
        }

        invoice = self._create_mydata_invoice()
        pdf_content = b'%PDF-1.4 final invoice'

        invoice._l10n_gr_edi_send_invoices()

        document = invoice.l10n_gr_edi_document_ids.filtered(lambda document: document.state == 'invoice_sent')
        self.assertEqual(len(document), 1)
        self.assertRecordValues(document, [{
            'mydata_mark': '400001900000001',
            'mydata_uid': 'MYDATA-UID',
            'mydata_authentication_code': 'AUTHENTICATION-CODE',
            'provider_uid': 'PROVIDER-UID',
            'provider_invoice_identifier': 'INVOICE-IDENTIFIER',
            'provider_pdf_state': 'pending',
        }])

        mock_issue_invoice.assert_called_once()
        request_values = mock_issue_invoice.call_args.kwargs['request_values']
        self.assertEqual(request_values['invoice_id'], invoice._l10n_gr_edi_get_provider_invoice_id())
        self.assertEqual(request_values['issue_date'], '2024-01-01')
        self.assertTrue(request_values['xml'].startswith("<?xml version='1.0' encoding='UTF-8'"))

        root = etree.fromstring(request_values['xml'].encode())
        self.assertEqual(etree.QName(root).localname, 'InvoicesDoc')
        self.assertEqual(len(root.xpath('./*[local-name() = "invoice"]')), 1)

        invoice_data = {
            'pdf_attachment_values': {
                'raw': pdf_content,
            },
        }
        self.env['account.move.send']._l10n_gr_edi_try_upload_final_pdf(invoice, invoice_data)

        mock_post_e_invoo.assert_called_once()
        pdf_values = mock_post_e_invoo.call_args.kwargs['json']
        self.assertEqual(pdf_values['invoice_id'], invoice._l10n_gr_edi_get_provider_invoice_id())
        self.assertEqual(pdf_values['parent_token'], 'PARENT-TOKEN')
        self.assertEqual(base64.b64decode(pdf_values['pdf_b64']), pdf_content)
        self.assertEqual(document.provider_pdf_state, 'sent')
        self.assertFalse(document.provider_pdf_error)
        self.assertNotIn('error', invoice_data)

    @patch('odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move.AccountMove._l10n_gr_edi_issue_invoice')
    def test_unknown_result_reuses_pending_submission(self, mock_issue_invoice):
        mock_issue_invoice.side_effect = (None, self._success_result())
        invoice = self._create_mydata_invoice()

        with freeze_time('2024-01-01 12:00:00'):
            invoice._l10n_gr_edi_send_invoices()

        pending_document = invoice.l10n_gr_edi_document_ids.filtered(lambda document: document.state == 'invoice_pending')
        self.assertEqual(len(pending_document), 1)

        original_datetime = pending_document.datetime
        original_xml = pending_document.attachment_id.raw

        with freeze_time('2024-01-01 13:00:00'):
            invoice._l10n_gr_edi_send_invoices()

        sent_document = invoice.l10n_gr_edi_document_ids.filtered(lambda document: document.state == 'invoice_sent')
        self.assertEqual(sent_document, pending_document)
        self.assertEqual(sent_document.datetime, original_datetime)
        self.assertEqual(sent_document.attachment_id.raw, original_xml)
        self.assertEqual(len(invoice.l10n_gr_edi_document_ids), 1)

        self.assertEqual(mock_issue_invoice.call_count, 2)
        first_request = mock_issue_invoice.call_args_list[0].kwargs['request_values']
        retry_request = mock_issue_invoice.call_args_list[1].kwargs['request_values']

        self.assertEqual(retry_request['invoice_id'], first_request['invoice_id'])
        self.assertEqual(retry_request['invoice_datetime'], first_request['invoice_datetime'])
        self.assertEqual(retry_request['xml'], first_request['xml'])

    @patch('odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move.AccountMove._l10n_gr_edi_issue_invoice')
    def test_tf_errors_start_a_fresh_submission(self, mock_issue_invoice):
        for error_code in ('tf1', 'tf2'):
            with self.subTest(error_code=error_code):
                mock_issue_invoice.reset_mock()
                mock_issue_invoice.side_effect = (
                    {
                        'upstream_status': 200,
                        'response': {
                            'success': False,
                            'error': error_code,
                        },
                    },
                    self._success_result(),
                )
                invoice = self._create_mydata_invoice()

                invoice._l10n_gr_edi_send_invoices()

                error_document = invoice.l10n_gr_edi_document_ids.filtered(lambda document: document.state == 'invoice_error')
                self.assertEqual(len(error_document), 1)
                self.assertIn(error_code.upper(), error_document.message)

                invoice._l10n_gr_edi_send_invoices()

                sent_document = invoice.l10n_gr_edi_document_ids.filtered(lambda document: document.state == 'invoice_sent')
                self.assertEqual(len(sent_document), 1)
                self.assertFalse(error_document.exists())
                self.assertEqual(mock_issue_invoice.call_count, 2)

    @patch('odoo.addons.l10n_gr_edi_e_invoo_bridge.models.account_move.AccountMove._l10n_gr_edi_issue_invoice')
    def test_send_invoices_missing_methodoos_api_token(self, mock_issue_invoice):
        invoice = self._create_mydata_invoice()
        invoice.company_id.l10n_gr_edi_methodoos_api_token = False

        invoice._l10n_gr_edi_send_invoices()

        mock_issue_invoice.assert_not_called()
        document = invoice.l10n_gr_edi_document_ids.filtered(lambda document: document.state == 'invoice_error')
        self.assertEqual(len(document), 1)
        self.assertIn(str(E_INVOO_TOKEN_NOT_SET), document.message)
