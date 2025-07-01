# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from unittest.mock import patch

CONTACT_PROXY_METHOD = 'odoo.addons.l10n_my_edi.models.account_edi_proxy_user.AccountEdiProxyClientUser._l10n_my_edi_contact_proxy'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMyEDITestSubmission(TestAccountMoveSendCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()

        # TIN number is required
        cls.company_data['company'].write({
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
            'l10n_my_edi_industrial_classification': cls.env['l10n_my_edi.industry_classification'].search([('code', '=', '01111')]).id,
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that one street, 5',
            'city': 'Main city',
            'phone': '+60123456789',
        })
        cls.partner_a.write({
            'vat': 'C2584563201',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234568',
            'country_id': cls.env.ref('base.my').id,
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'street': 'that other street, 3',
            'city': 'Main city',
            'phone': '+60123456786',
            'ref': "MY-REF",
        })
        cls.product_a.l10n_my_edi_classification_code = "001"

        # We can reuse this invoice for the flow tests.
        cls.basic_invoice = cls.init_invoice(
            'out_invoice', products=cls.product_a
        )
        cls.basic_invoice.action_post()

        # For simplicity, we will test everything using a 'test' mode user, but we create it using demo to avoid triggering any api calls.
        cls.proxy_user = cls.env['account_edi_proxy_client.user']._register_proxy_user(cls.company_data['company'], 'l10n_my_edi', 'demo')
        cls.proxy_user.edi_mode = 'test'

        # This will allow to still use the send and print flow when testing, even if the new module is installed.
        # It's best to keep the code tested even if we expect users to use the new flow.
        cls.env['ir.config_parameter'].set_param('l10n_my_edi.disable.send_and_print.first', 'False')

        cls.fakenow = datetime(2024, 7, 15, 10, 00, 00)
        cls.startClassPatcher(freeze_time(cls.fakenow))

    def test_01_basic_submission(self):
        """
        This tests the most basic flow: an invoice is successfully sent to the MyInvois platform, and then pass validation.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_01_mock):
            send_and_print._generate_and_send_invoices(
                self.basic_invoice,
                invoice_edi_format='my_myinvois',
            )

        # Now that the invoice has been sent successfully, we assert that some info have been saved correctly.
        self.assertRecordValues(
            self.basic_invoice,
            [{
                'l10n_my_edi_state': 'valid',
                'l10n_my_edi_validation_time': datetime.strptime('2024-07-15 05:00:00', '%Y-%m-%d %H:%M:%S'),
                'l10n_my_edi_submission_uid': '123456789',
                'l10n_my_edi_external_uuid': '123458974513518',
            }]
        )

        # We will test the actual file in another test class, but we ensure it was generated as expected.
        self.assertTrue(self.basic_invoice.l10n_my_edi_file_id)

    def test_02_failed_submission(self):
        """
        This test will test a flow where the submission itself (not the documents inside) fails for any reason.
        A general error as such should be handled, but is not expected and should be treated as a bug on our side.

        As we submit a single invoice, we expect a UserError to be raised.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_02_mock):
            with self.assertRaises(UserError, msg='Server error; If the problem persists, please contact the Odoo support.'):
                send_and_print._generate_and_send_invoices(
                    self.basic_invoice,
                    invoice_edi_format='my_myinvois',
                )

    def test_03_failed_document_submission(self):
        """
        Unlike the previous test, this will test the use case where the submission is done correctly but the document
        itself is incorrect.

        This would be due to an incorrect supplier tin for example.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_03_mock):
            # We want to assert that some values are saved during the commit, which won't happen during a test if we raise all the way.
            # So instead of doing an assertRaises, we will catch the error (ensuring that it does happen) then continue.
            try:
                send_and_print._generate_and_send_invoices(
                    self.basic_invoice,
                    invoice_edi_format='my_myinvois',
                )
            except UserError:
                pass  # We expect a user error to be raised here.
            else:
                assert False, 'The expected user error did not raise.'

        # When such error occurs, we expect the hash and retry time to be set, has we need to avoid allowing a user to
        # resend an invoice right away without any changes.
        self.assertRecordValues(
            self.basic_invoice,
            [{
                'l10n_my_error_document_hash': 'HX164532#=',
                'l10n_my_edi_retry_at': '2024-07-15 10:10:00',
                'l10n_my_edi_state': 'invalid',
            }]
        )

    def test_04_cancellation(self):
        """
        An invoice can be cancelled up to 72h after validation.
        Test the cancellation flow when it works well.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_04_mock):
            send_and_print._generate_and_send_invoices(
                self.basic_invoice,
                invoice_edi_format='my_myinvois',
            )

            # Open the wizard successfully, 72h did not pass
            action = self.basic_invoice.button_request_cancel()
            wizard = self.env[action['res_model']].with_context(action['context']).create({
                'reason': 'Discount not applied',
            })
            # Cancel the invoice
            wizard.button_request_update()
        self.assertRecordValues(
            self.basic_invoice,
            [{
                'l10n_my_edi_state': 'cancelled',
                'state': 'cancel',
            }]
        )

    def test_05_cancellation_failures(self):
        """
        Tests two scenarios when cancellation fails.
        First on is trying to launch the wizard past the 72h mark, and then an actual cancellation error.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_05_mock):
            send_and_print._generate_and_send_invoices(
                self.basic_invoice,
                invoice_edi_format='my_myinvois',
            )

            self.basic_invoice.l10n_my_edi_validation_time = datetime.strptime('2024-07-12 10:00:00', '%Y-%m-%d %H:%M:%S')

            # More than 72h, it failed
            with self.assertRaises(UserError, msg='It has been more than 72h since the invoice validation, you can no longer cancel it.\nInstead, you should issue a debit or credit note.'):
                self.basic_invoice.button_request_cancel()

            self.basic_invoice.l10n_my_edi_validation_time = datetime.now()
            action = self.basic_invoice.button_request_cancel()
            wizard = self.env[action['res_model']].with_context(action['context']).create({
                'reason': 'Discount not applied',
            })
            # Cancel the invoice. It failed during cancellation and logged an error.
            wizard.button_request_update()
            self.assertEqual(self.basic_invoice.message_ids[0].preview, 'You do not have the permission to update this invoice.')

    def test_06_invalid_reset(self):
        """
        Test that an invalid invoice can be reset, and that after reset the edi related fields are correctly reset beside the hash and retry time.
        Also test that the invoice can be sent again after correction.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_06_mock):
            # We want to assert that some values are saved during the commit, which won't happen during a test if we raise all the way.
            # So instead of doing an assertRaises, we will catch the error (ensuring that it does happen) then continue.
            try:
                send_and_print._generate_and_send_invoices(
                    self.basic_invoice,
                    invoice_edi_format='my_myinvois',
                )
            except UserError:
                pass  # We expect a user error to be raised here.
            else:
                assert False, 'The expected user error did not raise.'

            # Invalid invoices are cancelled automatically.
            self.assertEqual(self.basic_invoice.state, 'cancel')
            self.basic_invoice.button_draft()

            self.assertRecordValues(
                self.basic_invoice,
                [{
                    'l10n_my_error_document_hash': 'HX164532#=',
                    'l10n_my_edi_retry_at': '2024-07-15 10:10:00',
                    'l10n_my_edi_state': False,
                    'l10n_my_edi_validation_time': False,
                    'l10n_my_edi_submission_uid': False,
                    'l10n_my_edi_external_uuid': False,
                }]
            )

            # ... we change whatever
            self.basic_invoice.action_post()

            send_and_print = self.create_send_and_print(self.basic_invoice)
            send_and_print._generate_and_send_invoices(
                self.basic_invoice,
                invoice_edi_format='my_myinvois',
            )

            self.assertRecordValues(
                self.basic_invoice,
                [{
                    'l10n_my_edi_state': 'valid',
                }]
            )

    def test_07_pending_submission(self):
        """
        Test the case of a submission status being unavailable at the time of submission.
        No errors should be raised, and it should be handled by the cron later on.
        """
        self.get_submission_status_count = 0  # Needed for the mock; we get it twice. Once during submission and once from the cron.
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_07_mock):
            send_and_print._generate_and_send_invoices(
                self.basic_invoice,
                invoice_edi_format='my_myinvois',
            )

            self.assertRecordValues(
                self.basic_invoice,
                [{
                    'l10n_my_edi_state': 'in_progress',
                    'l10n_my_edi_submission_uid': '123456789',
                    'l10n_my_edi_external_uuid': '123458974513518',
                }]
            )

            # ... some time later, the cron runs.
            self.env['account.move']._cron_l10n_my_edi_synchronize_myinvois()

            # The update should be reflected on the move.
            self.assertEqual(self.basic_invoice.l10n_my_edi_state, 'valid')

    def test_08_mass_submission(self):
        """ This test will ensure that invoices are split as expected if there are more than SUBMISSION_MAX_SIZE at once. """
        # For performance purposes we will not create 100 invoices here, but instead patch SUBMISSION_MAX_SIZE to make batches of two invoices.
        self.submission_count = 0
        invoice_vals = []
        for i in range(1, 10):
            invoice_vals.append({
                'move_type': 'out_invoice',
                'partner_id': self.partner_a.id,
                'invoice_line_ids': [
                    Command.create({'product_id': self.product_a.id}),
                ],
            })

        self.submission_invoice = self.env['account.move'].create(invoice_vals)
        self.submission_invoice.action_post()
        self.submission_invoice |= self.basic_invoice

        send_and_print = self.create_send_and_print(self.submission_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_08_mock), \
             patch('odoo.addons.l10n_my_edi.models.account_move.SUBMISSION_MAX_SIZE', 2):
            send_and_print._generate_and_send_invoices(
                self.submission_invoice,
                invoice_edi_format='my_myinvois',
            )

        # we have 10 invoices, with a max size of 2 we expect 5 different submissions.
        self.assertEqual(self.submission_count, 5)

    def test_09_fetch_status(self):
        """ After pushing an invoice, we can optionally fetch the status manually if needed. """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_09_mock):
            send_and_print._generate_and_send_invoices(
                self.basic_invoice,
                invoice_edi_format='my_myinvois',
            )

            self.assertRecordValues(
                self.basic_invoice,
                [{
                    'l10n_my_edi_state': 'in_progress',
                    'l10n_my_edi_submission_uid': '123456789',
                    'l10n_my_edi_external_uuid': '123458974513518',
                }]
            )

            # ... some time later, the user does not want to wait for the cron and press the button.
            self.basic_invoice.action_l10n_my_edi_update_status()

            # The update should be reflected on the move.
            self.assertEqual(self.basic_invoice.l10n_my_edi_state, 'valid')

    def test_10_reject_bill(self):
        """
        An invoice can be cancelled up to 72h after validation.
        Test the cancellation flow when it works well.
        """
        bill = self.init_invoice(
            'in_invoice', products=self.product_a
        )
        bill.action_post()

        # Technically this would have been done at import
        bill.l10n_my_edi_state = 'valid'

        with patch(CONTACT_PROXY_METHOD, new=self._test_10_mock):
            action = bill.action_l10n_my_edi_reject_bill()
            wizard = self.env[action['res_model']].with_context(action['context']).create({
                'reason': 'Discount not applied',
            })
            # Cancel the invoice
            wizard.button_request_update()

        self.assertRecordValues(  # Did not change, not until the supplier cancel.
            bill,
            [{
                'l10n_my_edi_state': 'rejected',
                'state': 'posted',
            }]
        )

    def test_11_full_rejection_flow_invoice(self):
        """
        We issue an invoice to our customer with the wrong address.
        The customer reject it for that reason.
        We receive the updated status later on, and cancel the invoice to issue a new one later.
        """
        send_and_print = self.create_send_and_print(self.basic_invoice)
        with patch(CONTACT_PROXY_METHOD, new=self._test_11_mock):
            # Issue the invoice, and get a valid status.
            send_and_print._generate_and_send_invoices(
                self.basic_invoice,
                invoice_edi_format='my_myinvois',
            )
            # Update the status, and receive a rejection request.
            self.basic_invoice.action_l10n_my_edi_update_status()
            self.assertEqual(self.basic_invoice.l10n_my_edi_state, 'rejected')
            # We then cancel the invoice as the reason is valid.
            action = self.basic_invoice.button_request_cancel()
            wizard = self.env[action['res_model']].with_context(action['context']).create({
                'reason': 'Wrong address',
            })
            # Cancel the invoice
            wizard.button_request_update()
            self.assertEqual(self.basic_invoice.l10n_my_edi_state, 'cancelled')

    # -------------------------------------------------------------------------
    # Patched methods
    # -------------------------------------------------------------------------

    def _test_01_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    '123458974513518': {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '2024-07-15T05:00:00Z',
                    }
                },
                'document_count': 1,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_02_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'error': {
                    'reference': 'internal_server_error',
                    'data': {},
                }
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_03_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'success': False,
                    'errors': [{
                        'reference': 'Y503',
                        'target': 'TIN',
                    }],
                    'error_document_hash': 'HX164532#=',
                    'retry_at': datetime.now() + relativedelta(minutes=10),
                }]
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_04_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    '123458974513518': {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '2024-07-15T13:15:10Z',
                    }
                },
                'document_count': 1,
            }
        elif endpoint == 'api/l10n_my_edi/1/update_status':
            return {
                'success': True,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_05_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    '123458974513518': {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '2024-07-15T13:15:10Z',
                    }
                },
                'document_count': 1,
            }
        elif endpoint == 'api/l10n_my_edi/1/update_status':
            return {
                'error': {
                    'reference': 'update_forbidden',
                    'data': {},
                }
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_06_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices' and not params['documents'][0]['error_document_hash']:
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'success': False,
                    'errors': [{
                        'reference': 'Y503',
                        'target': 'TIN',
                    }],
                    'error_document_hash': 'HX164532#=',
                    'retry_at': datetime.now() + relativedelta(minutes=10),
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/submit_invoices' and params['documents'][0]['error_document_hash']:
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    '123458974513518': {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '2024-07-15T05:00:00Z',
                    }
                },
                'document_count': 1,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_07_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses' and self.get_submission_status_count == 0:
            self.get_submission_status_count += 1
            return {
                'statuses': {
                    '123458974513518': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    }
                },
                'document_count': 1,
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses' and self.get_submission_status_count == 1:
            self.get_submission_status_count += 1
            return {
                'statuses': {
                    '123458974513518': {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '2024-07-15T05:00:00Z',
                    }
                },
                'document_count': 1,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_08_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            # While there are easier ways, holding a count helps make it easy to test many loops.
            self.submission_count += 1
            return {
                'submission_uid': str(123456789 + self.submission_count),
                'documents': [{
                    'move_id': document['move_id'],
                    'uuid': str(123458974513519 + i + self.submission_count),
                    'success': True,
                } for i, document in enumerate(params['documents'])]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            invoices = self.submission_invoice.grouped('l10n_my_edi_submission_uid').get(params['submission_uid'])
            return {
                'statuses': {
                    invoice.l10n_my_edi_external_uuid: {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '2024-07-15T05:00:00Z',
                    } for invoice in invoices
                },
                'document_count': 1,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_09_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    '123458974513518': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    }
                },
                'document_count': 1,
            }
        elif endpoint == 'api/l10n_my_edi/1/get_status':
            return {
                'status': 'valid',
                'status_reason': '',
                'long_id': '',
                'valid_datetime': '2024-07-15T05:00:00Z',
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_10_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/update_status':
            return {
                'success': True,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_11_mock(self, endpoint, params):
        """ Basic mocked method that simulate what the proxy would return depending on the endpoint. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            return {
                'submission_uid': '123456789',
                'documents': [{
                    'move_id': params['documents'][0]['move_id'],
                    'uuid': '123458974513518',
                    'success': True,
                }]
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    '123458974513518': {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '2024-07-15T05:00:00Z',
                    }
                },
                'document_count': 1,
            }
        elif endpoint == 'api/l10n_my_edi/1/get_status':
            return {
                'status': 'rejected',
                'status_reason': 'Wrong address',
                'long_id': '',
                'valid_datetime': '',
            }
        elif endpoint == 'api/l10n_my_edi/1/update_status':
            return {
                'success': True,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))
