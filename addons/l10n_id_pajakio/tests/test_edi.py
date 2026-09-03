import json
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from .test_registration import IAP_PROXY_METHOD


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nIDTestPajakioEdi(TestAccountMoveSendCommon):
    """Tests in this class are to guarantee the actual invoice creation/sending/status update/cancellation flow with Pajak.io"""

    @classmethod
    @TestAccountMoveSendCommon.setup_country('id')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].sudo().update({
            "name": "Indonesian Company",
            'country_id': cls.env.ref('base.id').id,
            'city': 'Jakarta',
            'vat': '1234567890123456',
            # assumes that account has been successfully registered and activated
            'l10n_id_pajakio_mode': 'test',
            'l10n_id_pajakio_active': True,
            'l10n_id_pajakio_key_identifier': 'key_identifier',
            'l10n_id_pajakio_company_registered': True,
            'l10n_id_pajakio_email': 'test@email.com',
        })
        cls.partner_a.write({
            'l10n_id_kode_transaksi': '04',
            'vat': '1234567890123456',
            'country_id': cls.env.ref('base.id').id,
            'l10n_id_pkp': True,
        })

    def _create_pajakio_document(self, invoice):
        """ Create the Pajak.io e-Faktur document backing an invoice, mirroring what the real
        send flow creates on-demand, so tests can set Pajak.io fields directly. """
        invoice.l10n_id_coretax_document = self.env['l10n_id_efaktur_coretax.document'].create({
            'invoice_ids': invoice.ids,
            'company_id': invoice.company_id.id,
            'document_type': 'pajakio',
        })
        return invoice.l10n_id_coretax_document

    # Pajak.io showing in the account.move.send wizard

    def test_pajakio_edi_shows(self):
        """ Test when the Pajak.io EDI option is shown in the invoice send wizard"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True)
        wizard = self.create_send_and_print(invoice)
        self.assertIn('id_pajakio', wizard.extra_edis)

    def test_pajakio_edi_not_shown(self):
        """ Test the conditions where even if module is installed, edi might not be shown yet"""
        # pajak.io not activated yet
        self.company_data['company'].l10n_id_pajakio_active = False

        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True)
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

        # The pajak.io status of invoice is already set which means it has been sent
        self.company_data['company'].l10n_id_pajakio_active = True

        document = self._create_pajakio_document(invoice)
        document.l10n_id_pajakio_status = 'draft'
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

        document.l10n_id_pajakio_status = 'waiting'
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

        document.l10n_id_pajakio_status = 'approved'
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

    def test_pajakio_edi_not_applicable_for_non_invoice(self):
        """Test that pajak.io EDI is not applicable for refunds."""
        invoice = self.init_invoice("out_refund", partner=self.partner_a, amounts=[1000], post=True)
        wizard = self.create_send_and_print(invoice)
        self.assertFalse(wizard.extra_edis)

    def test_pajakio_generate_json_attachment_data(self):
        """ Test that _l10n_id_pajakio_generate_json generates the expected attachment data"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        invoice.l10n_id_kode_transaksi = "04"

        invoice_data = {
            'extra_edis': {'id_pajakio'},
        }
        expected_payload = invoice._l10n_id_pajakio_prepare_invoice_payload()

        self.env['account.move.send']._l10n_id_pajakio_generate_json(invoice, invoice_data)

        self.assertIn('pajakio_attachments', invoice_data)
        attachment_data = invoice_data['pajakio_attachments']
        self.assertEqual(attachment_data['name'], f'{invoice.name}_pajakio_request.json')
        self.assertEqual(attachment_data['res_model'], 'l10n_id_efaktur_coretax.document')
        self.assertEqual(attachment_data['res_field'], 'l10n_id_pajakio_file')
        self.assertEqual(json.loads(attachment_data['raw']), expected_payload)

    # Creating a single invoice

    def test_create_invoice_success(self):
        """Flow of creating a single invoice from via send&print wizard"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        send_and_print = self.create_send_and_print(invoice)

        mock_responses = [
            # when sending an invoice
            {
                'data': {'transactionId': 'TRX-12345'},
            },
            # when updating the status after sending
            {
                'data': {
                    'TRX-12345': {
                        'status': 'APPROVAL_SUKSES',
                        'data': {
                            'nofa': 'INV-001-DJP',
                            'urlPdf': 'testurlpdf.com',
                            'jenisFaktur': 'NORMAL',
                        },
                    },
                },
            },
        ]
        with patch(IAP_PROXY_METHOD, side_effect=mock_responses) as mock_iap:
            send_and_print.action_send_and_print()
            self.assertEqual(mock_iap.call_count, 2)

            # invoice should contain coretax document with type pajakio
            self.assertTrue(invoice.l10n_id_coretax_document and invoice.l10n_id_coretax_document.document_type == 'pajakio')
            self.assertEqual(invoice.l10n_id_coretax_document.l10n_id_pajakio_transaction_id, 'TRX-12345')
            self.assertEqual(invoice.l10n_id_coretax_document.l10n_id_pajakio_status, 'approved')
            self.assertEqual(invoice.l10n_id_coretax_document.l10n_id_pajakio_invoice_number, 'INV-001-DJP')

    def test_create_invoice_fail(self):
        """ Create invoice but Pajak.io responds with an erorr """

        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        send_and_print = self.create_send_and_print(invoice)

        mock_response = {
            'error': 'Failed to create invoice in Pajak.io. Input contains invalid NITKU format',
            'code': 'create_invoice_failed',
        }

        with patch(IAP_PROXY_METHOD, return_value=mock_response) as mock_iap:

            with self.assertRaises(UserError) as e:
                send_and_print.action_send_and_print()
            self.assertIn('Failed to create invoice in Pajak.io', str(e.exception))
            self.assertEqual(mock_iap.call_count, 1)  # once the first one fails, second one should not be called

    def test_create_invoices_all_success(self):
        """ Creating multiple invoices in 1 batch and it returns all successful responses"""

        invoices = self.env['account.move']
        for i in range(2):
            invoices |= self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)

        send_and_print = self._create_account_move_send_wizard_multi(invoices)
        mock_responses = [
            {
                'data': {
                    invoices[0].name: {
                        'transactionId': 'TRX-12345',
                    },
                    invoices[1].name: {
                        'transactionId': 'TRX-67890',
                    },
                },
            },
            {
                'data': {
                    'TRX-12345': {
                        'status': 'APPROVAL_SUKSES',
                        'data': {
                            'nofa': 'INV-001-DJP',
                            'urlPdf': 'testurlpdf.com',
                            'jenisFaktur': 'NORMAL',
                        },
                    },
                    'TRX-67890': {
                        'status': 'APPROVAL_SUKSES',
                        'data': {
                            'nofa': 'INV-002-DJP',
                            'urlPdf': 'testurlpdf2.com',
                            'jenisFaktur': 'NORMAL',
                        },
                    },
                },
            },
        ]

        with patch(IAP_PROXY_METHOD, side_effect=mock_responses) as mock_iap:
            send_and_print.action_send_and_print(force_synchronous=True)
            self.assertEqual(mock_iap.call_count, 2)

        self.assertEqual(invoices[0].l10n_id_coretax_document.l10n_id_pajakio_transaction_id, 'TRX-12345')
        self.assertEqual(invoices[0].l10n_id_coretax_document.l10n_id_pajakio_status, 'approved')
        self.assertEqual(invoices[0].l10n_id_coretax_document.l10n_id_pajakio_invoice_number, 'INV-001-DJP')

        self.assertEqual(invoices[1].l10n_id_coretax_document.l10n_id_pajakio_transaction_id, 'TRX-67890')
        self.assertEqual(invoices[1].l10n_id_coretax_document.l10n_id_pajakio_status, 'approved')
        self.assertEqual(invoices[1].l10n_id_coretax_document.l10n_id_pajakio_invoice_number, 'INV-002-DJP')

    def test_create_invoices_partial_succes(self):
        """ Test the flow when the batch creation is partially successful, successful ones should hav ethe pajakio fields set, while
        the failed ones should have an error shown on the log message"""

        invoices = self.env['account.move']
        for i in range(2):
            invoices |= self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)

        send_and_print = self._create_account_move_send_wizard_multi(invoices)
        mock_responses = [
            {
                'data': {
                    invoices[0].name: {
                        'transactionId': 'TRX-12345',
                    },
                    invoices[1].name: {
                        'error': 'Input contains invalid NITKU format',
                        'transactionId': None,
                    },
                },
            },
            {
                'data': {
                    'TRX-12345': {
                        'status': 'APPROVAL_SUKSES',
                        'data': {
                            'nofa': 'INV-001-DJP',
                            'urlPdf': 'testurlpdf.com',
                            'jenisFaktur': 'NORMAL',
                        },
                    },
                },
            },
        ]

        with patch(IAP_PROXY_METHOD, side_effect=mock_responses) as mock_iap:
            send_and_print.action_send_and_print()
            self.env['account.move.send']._generate_and_send_invoices(invoices, from_cron=True)
            self.assertEqual(mock_iap.call_count, 2)

        # First invoice should have the pajakio fields set while second one should have error
        self.assertEqual(invoices[0].l10n_id_coretax_document.l10n_id_pajakio_transaction_id, 'TRX-12345')
        self.assertEqual(invoices[0].l10n_id_coretax_document.l10n_id_pajakio_status, 'approved')
        self.assertEqual(invoices[0].l10n_id_coretax_document.l10n_id_pajakio_invoice_number, 'INV-001-DJP')

        self.assertFalse(invoices[1].l10n_id_coretax_document.l10n_id_pajakio_transaction_id)
        self.assertFalse(invoices[1].l10n_id_coretax_document.l10n_id_pajakio_status)
        self.assertTrue(any('Input contains invalid NITKU format' in msg.body for msg in invoices[1].message_ids))

    def test_create_invoices_all_fail(self):
        """ Test when all invoices fail, it should raise errors in each invoice as a message"""

        invoices = self.env['account.move']
        for i in range(2):
            invoices |= self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)

        send_and_print = self._create_account_move_send_wizard_multi(invoices)
        mock_response = {
            'data': {
                invoices[0].name: {
                    'error': 'Input contains invalid NITKU format',
                    'transactionId': None,
                },
                invoices[1].name: {
                    'error': 'Input contains invalid NPWP format',
                    'transactionId': None,
                },
            },
        }

        with patch(IAP_PROXY_METHOD, return_value=mock_response) as mock_iap:
            send_and_print.action_send_and_print()
            self.env['account.move.send']._generate_and_send_invoices(invoices, from_cron=True)
            self.assertEqual(mock_iap.call_count, 1)  # only the batched create_invoices call, nothing succeeded to poll a status for

        self.assertFalse(invoices[0].l10n_id_coretax_document.l10n_id_pajakio_transaction_id)
        self.assertFalse(invoices[0].l10n_id_coretax_document.l10n_id_pajakio_status)
        self.assertTrue(any('Input contains invalid NITKU format' in msg.body for msg in invoices[0].message_ids))

        self.assertFalse(invoices[1].l10n_id_coretax_document.l10n_id_pajakio_transaction_id)
        self.assertFalse(invoices[1].l10n_id_coretax_document.l10n_id_pajakio_status)
        self.assertTrue(any('Input contains invalid NPWP format' in msg.body for msg in invoices[1].message_ids))

    def test_create_invoices_all_fail_non_api(self):
        """ Test when create invoices fail but nothing related to the API (e.g. connection timeout, network error),
        error message should be posted on each invoice and no pajakio fields should be set"""

        invoices = self.env['account.move']
        for i in range(2):
            invoices |= self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)

        send_and_print = self._create_account_move_send_wizard_multi(invoices)
        mock_response = {
            'error': 'Connection timeout',
            'code': 'create_invoices_failed',
        }

        with patch(IAP_PROXY_METHOD, return_value=mock_response) as mock_iap:
            send_and_print.action_send_and_print()
            self.env['account.move.send']._generate_and_send_invoices(invoices, from_cron=True)
            self.assertEqual(mock_iap.call_count, 1)  # only the batched create_invoices call, it failed outright so nothing to poll a status for

        for invoice in invoices:
            self.assertFalse(invoice.l10n_id_coretax_document.l10n_id_pajakio_transaction_id)
            self.assertFalse(invoice.l10n_id_coretax_document.l10n_id_pajakio_status)
            self.assertTrue(any('Connection timeout' in msg.body for msg in invoice.message_ids))

    # invoice update status

    def test_pajakio_update_status_approved(self):
        """Test that update_status sets approved status with invoice number and URL."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document = self._create_pajakio_document(invoice)
        document.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {
            'data': {
                'TRX-12345': {
                    'status': 'APPROVAL_SUKSES',
                    'data': {
                        'nofa': 'INV-001-DJP',
                        'urlPdf': 'testurlpdf.com',
                        'jenisFaktur': 'NORMAL',
                    },
                },
            },
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            result = document._l10n_id_pajakio_update_status()
            self.assertFalse(result)
            self.assertEqual(document.l10n_id_pajakio_status, 'approved')
            self.assertEqual(document.l10n_id_pajakio_invoice_number, 'INV-001-DJP')
            self.assertEqual(document.l10n_id_pajakio_transaction_url, 'testurlpdf.com')

    def test_pajakio_update_status_waiting(self):
        """Test that status is updated to waiting when getting a 'MENUNGGU_VERIFIKASI_DJP' status from Pajak.io."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document = self._create_pajakio_document(invoice)
        document.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {
            'data': {
                'TRX-12345': {
                    'status': 'MENUNGGU_VERIFIKASI_DJP',
                    'data': {'jenisFaktur': 'NORMAL'},
                },
            },
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            document._l10n_id_pajakio_update_status()
            self.assertEqual(document.l10n_id_pajakio_status, 'waiting')

    def test_pajakio_update_status_rejected(self):
        """Test that when status is updated with rejection, it should set the status to 'rejected' and record the reject reason."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document = self._create_pajakio_document(invoice)
        document.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {
            'data': {
                'TRX-12345': {
                    'status': 'DITOLAK',
                    'data': {
                        'alasan': 'Invalid NPWP format',
                        'jenisFaktur': 'NORMAL',
                    },
                },
            },
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            document._l10n_id_pajakio_update_status()
            self.assertEqual(document.l10n_id_pajakio_status, 'rejected')
            self.assertEqual(document.l10n_id_pajakio_reject_reason, 'Invalid NPWP format')

    def test_pajakio_update_status_cancelled(self):
        """Test that update_status sets cancel status when jenisFaktur is BATAL."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document = self._create_pajakio_document(invoice)
        document.l10n_id_pajakio_transaction_id = 'TRX-12345'

        mock_response = {
            'data': {
                'TRX-12345': {
                    'status': 'APPROVAL_SUKSES',
                    'data': {'jenisFaktur': 'BATAL'},
                },
            },
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response):
            document._l10n_id_pajakio_update_status()
            self.assertEqual(document.l10n_id_pajakio_status, 'cancel')

    def test_cron_update_waiting_status(self):
        """Cron only refreshes documents still 'waiting', batching same-company documents into one IAP call."""
        invoice_waiting = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document_waiting = self._create_pajakio_document(invoice_waiting)
        document_waiting.l10n_id_pajakio_transaction_id = 'TRX-WAITING'
        document_waiting.l10n_id_pajakio_status = 'waiting'

        invoice_approved = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document_approved = self._create_pajakio_document(invoice_approved)
        document_approved.l10n_id_pajakio_transaction_id = 'TRX-APPROVED'
        document_approved.l10n_id_pajakio_status = 'approved'

        mock_response = {
            'data': {
                'TRX-WAITING': {
                    'status': 'APPROVAL_SUKSES',
                    'data': {'nofa': 'INV-001-DJP', 'urlPdf': 'testurlpdf.com', 'jenisFaktur': 'NORMAL'},
                },
            },
        }
        with patch(IAP_PROXY_METHOD, return_value=mock_response) as mock_iap:
            self.env['l10n_id_efaktur_coretax.document']._cron_l10n_id_pajakio_update_waiting_status()
            self.assertEqual(mock_iap.call_count, 1, "one IAP call for the single company with waiting documents")
            self.assertEqual(mock_iap.call_args[0][0]['transaction_ids'], ['TRX-WAITING'])

        self.assertEqual(document_waiting.l10n_id_pajakio_status, 'approved')
        self.assertEqual(document_approved.l10n_id_pajakio_status, 'approved')

    def test_pajakio_rejected_invoice_can_be_resent(self):
        """Test that a rejected invoice is eligible for resending via pajak.io EDI."""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True)
        self._create_pajakio_document(invoice).l10n_id_pajakio_status = 'rejected'
        wizard = self.create_send_and_print(invoice)
        self.assertIn('id_pajakio', wizard.extra_edis)

    # Cancel flow

    def test_pajakio_button_request_cancel_opens_wizard_when_approved(self):
        """Test that a wizard is returned upon calling the button_request_cancel method instead of the standrad cancel request process"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        self._create_pajakio_document(invoice).l10n_id_pajakio_status = 'approved'

        action = invoice.button_request_cancel()
        self.assertEqual(action['res_model'], 'l10n_id_pajakio.invoice.cancel')
        self.assertEqual(action['context']['default_invoice_id'], invoice.id)

    def test_pajakio_button_request_cancel_falls_back_when_not_approved(self):
        """Test that if the request cancel is called when invoice is not in approved status yet, error is raised"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document = self._create_pajakio_document(invoice)
        document.l10n_id_pajakio_status = 'waiting'
        with self.assertRaises(UserError):
            invoice.button_request_cancel()

        document.l10n_id_pajakio_status = 'draft'
        with self.assertRaises(UserError):
            invoice.button_request_cancel()

    def test_pajakio_wizard_request_cancel_success(self):
        """Test the full flow of successful request cancel and the effects"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document = self._create_pajakio_document(invoice)
        document.l10n_id_pajakio_status = 'approved'
        document.l10n_id_pajakio_transaction_id = 'TRX-12345'
        wizard = self.env['l10n_id_pajakio.invoice.cancel'].create({
            'invoice_id': invoice.id,
            'reason': 'Customer requested cancellation',
        })

        mock_responses = [
            # when requesting the cancel itself
            {
                'data': True,
            },
            # when updating the status after cancel
            {
                'data': {  #
                    'TRX-12345': {
                        'status': 'APPROVAL_SUKSES',
                        'data': {'jenisFaktur': 'BATAL'},
                    },
                },
            },
        ]
        with patch(IAP_PROXY_METHOD, side_effect=mock_responses) as mock_iap:
            wizard.button_request_cancel()

        self.assertEqual(document.l10n_id_pajakio_cancel_reason, 'Customer requested cancellation')
        self.assertEqual(document.l10n_id_pajakio_status, 'cancel')
        self.assertEqual(invoice.state, 'cancel')
        self.assertEqual(mock_iap.call_count, 2)

    def test_pajakio_wizard_request_cancel_status_update_failure(self):
        """Test that when cancel succeeds but the follow-up status update fails, the invoice is still
        cancelled in Odoo and a chatter message is posted with the error of failed status update"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        document = self._create_pajakio_document(invoice)
        document.l10n_id_pajakio_status = 'approved'
        document.l10n_id_pajakio_transaction_id = 'TRX-12345'
        wizard = self.env['l10n_id_pajakio.invoice.cancel'].create({
            'invoice_id': invoice.id,
            'reason': 'Customer requested cancellation',
        })

        mock_responses = [
            {'data': True},                    # cancel request succeeds
            {'error': 'Connection timeout'},   # status update fails
        ]
        with patch(IAP_PROXY_METHOD, side_effect=mock_responses) as mock_iap:
            wizard.button_request_cancel()  # must NOT raise
            self.assertEqual(mock_iap.call_count, 2)

        self.assertEqual(invoice.state, 'cancel')
        self.assertEqual(document.l10n_id_pajakio_status, 'cancel')

        # Error should appear in log messages
        self.assertTrue(any('Connection timeout' in msg.body for msg in document.message_ids))

    def test_pajakio_wizard_request_cancel_requires_reason(self):
        """Test that if reason is not given or blank during cancellation request, error is raised"""
        invoice = self.init_invoice("out_invoice", partner=self.partner_a, amounts=[1000], post=True, taxes=self.tax_sale_a)
        wizard = self.env['l10n_id_pajakio.invoice.cancel'].create({
            'invoice_id': invoice.id,
            'reason': '   ',
        })

        with self.assertRaises(UserError):
            wizard.button_request_cancel()
