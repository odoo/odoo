# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.exceptions import UserError
from odoo.tests import tagged
from unittest.mock import patch

CONTACT_PROXY_METHOD = 'odoo.addons.l10n_my_edi.models.account_edi_proxy_user.AccountEdiProxyClientUser._l10n_my_edi_contact_proxy'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMyEDITestNewSubmission(TestAccountMoveSendCommon):
    """ The tests in this file are similar to the ones in test_submissions but use the new flow (outside of send & print)
    to test the features of the EDI.
    These will fully replace the old tests in master.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref='my'):
        super().setUpClass(chart_template_ref=chart_template_ref)

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

        cls.env['ir.config_parameter'].set_param('l10n_my_edi.disable.send_and_print.first', 'True')

    @freeze_time('2024-07-15 10:00:00')
    def test_01_new_basic_submission(self):
        """
        This tests the most basic flow: an invoice is successfully sent to the MyInvois platform, and then pass validation.
        """
        # Send to MyInvois
        with patch(CONTACT_PROXY_METHOD, new=self._test_01_mock):
            self.basic_invoice.action_l10n_my_edi_send_invoice()

        # Now that the invoice has been sent successfully, we assert that some info have been saved correctly.
        self.assertRecordValues(
            self.basic_invoice,
            [{
                'l10n_my_edi_state': 'valid',
                'l10n_my_edi_validation_time': datetime.strptime('2024-07-15 05:00:00', '%Y-%m-%d %H:%M:%S'),
                'l10n_my_edi_invoice_long_id': '123-789-654',
                'l10n_my_edi_submission_uid': '123456789',
                'l10n_my_edi_external_uuid': '123458974513518',
            }]
        )

        # We will test the actual file in another test class, but we ensure it was generated as expected.
        self.assertTrue(self.basic_invoice.l10n_my_edi_file_id)

    @freeze_time('2024-07-15 10:00:00')
    def test_02_new_failed_submission(self):
        """
        This test will test a flow where the submission itself (not the documents inside) fails for any reason.
        A general error as such should be handled, but is not expected and should be treated as a bug on our side.

        As we submit a single invoice, we expect a UserError to be raised.
        """
        with patch(CONTACT_PROXY_METHOD, new=self._test_02_mock):
            with self.assertRaisesRegex(UserError, 'Server error; If the problem persists, please contact the Odoo support.'):
                self.basic_invoice.action_l10n_my_edi_send_invoice()

    @freeze_time('2024-07-15 10:00:00')
    def test_03_new_failed_document_submission(self):
        """
        Unlike the previous test, this will test the use case where the submission is done correctly but the document
        itself is incorrect.

        This would be due to an incorrect supplier tin for example.
        """
        with patch(CONTACT_PROXY_METHOD, new=self._test_03_mock):
            # We want to assert that some values are saved during the commit, which won't happen during a test if we raise all the way.
            # So instead of doing an assertRaises, we will catch the error (ensuring that it does happen) then continue.
            try:
                self.basic_invoice.action_l10n_my_edi_send_invoice()
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

    @freeze_time('2024-07-15 10:00:00')
    def test_04_new_cancellation(self):
        """
        An invoice can be cancelled up to 72h after validation.
        Test the cancellation flow when it works well.
        """
        with patch(CONTACT_PROXY_METHOD, new=self._test_04_mock):
            self.basic_invoice.action_l10n_my_edi_send_invoice()

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

    @freeze_time('2024-07-15 10:00:00')
    def test_05_new_cancellation_failures(self):
        """
        Tests two scenarios when cancellation fails.
        First on is trying to launch the wizard past the 72h mark, and then an actual cancellation error.
        """
        with patch(CONTACT_PROXY_METHOD, new=self._test_05_mock):
            self.basic_invoice.action_l10n_my_edi_send_invoice()

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

    @freeze_time('2024-07-15 10:00:00')
    def test_06_new_invalid_reset(self):
        """
        Test that an invalid invoice can be reset, and that after reset the edi related fields are correctly reset beside the hash and retry time.
        Also test that the invoice can be sent again after correction.
        """
        with patch(CONTACT_PROXY_METHOD, new=self._test_06_mock):
            # We want to assert that some values are saved during the commit, which won't happen during a test if we raise all the way.
            # So instead of doing an assertRaises, we will catch the error (ensuring that it does happen) then continue.
            try:
                self.basic_invoice.action_l10n_my_edi_send_invoice()
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

            self.basic_invoice.action_l10n_my_edi_send_invoice()

            self.assertRecordValues(
                self.basic_invoice,
                [{
                    'l10n_my_edi_state': 'valid',
                }]
            )

    @freeze_time('2024-07-15 10:00:00')
    def test_07_new_pending_submission(self):
        """
        Test the case of a submission status being unavailable at the time of submission.
        No errors should be raised, and it should be handled by the cron later on.
        """
        self.get_submission_status_count = 0  # Needed for the mock; we get it twice. Once during submission and once from the cron.
        with patch(CONTACT_PROXY_METHOD, new=self._test_07_mock):
            self.basic_invoice.action_l10n_my_edi_send_invoice()

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
            self.assertRecordValues(
                self.basic_invoice,
                [{
                    'l10n_my_edi_state': 'valid',
                    'l10n_my_edi_validation_time': datetime.strptime('2024-07-15 05:00:00', '%Y-%m-%d %H:%M:%S'),
                    'l10n_my_edi_invoice_long_id': '123-789-654',
                }]
            )

    @freeze_time('2024-07-15 10:00:00')
    def test_08_new_mass_submission(self):
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

        with patch(CONTACT_PROXY_METHOD, new=self._test_08_mock), \
             patch('odoo.addons.l10n_my_edi.models.account_move.SUBMISSION_MAX_SIZE', 2):
            self.submission_invoice.action_l10n_my_edi_send_invoice()

        # we have 10 invoices, with a max size of 2 we expect 5 different submissions.
        self.assertEqual(self.submission_count, 5)

    @freeze_time('2024-07-15 10:00:00')
    def test_09_new_fetch_status(self):
        """ After pushing an invoice, we can optionally fetch the status manually if needed. """
        with patch(CONTACT_PROXY_METHOD, new=self._test_09_mock):
            self.basic_invoice.action_l10n_my_edi_send_invoice()

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

    @freeze_time('2024-07-15 10:00:00')
    def test_10_new_full_rejection_flow_invoice(self):
        """
        We issue an invoice to our customer with the wrong address.
        The customer reject it for that reason.
        We receive the updated status later on, and cancel the invoice to issue a new one later.
        """
        with patch(CONTACT_PROXY_METHOD, new=self._test_10_mock):
            # Issue the invoice, and get a valid status.
            self.basic_invoice.action_l10n_my_edi_send_invoice()
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

    @freeze_time('2024-07-15 10:00:00')
    def test_11_qr_code_generation(self):
        """ Basic test that ensure that a valid invoice can generate a QR code. """
        with patch(CONTACT_PROXY_METHOD, new=self._test_11_mock):
            self.basic_invoice.action_l10n_my_edi_send_invoice()

        qr_data_uri = self.basic_invoice._generate_myinvois_qr_code()
        self.assertTrue(qr_data_uri)

    def test_12_multiple_moves_with_one_failed_submission(self):
        """Test that an error happening in the middle of multiple submissions is correctly handled."""
        self.submission_count = 0
        invoice_vals = []
        for i in range(1, 5):
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

        with patch(CONTACT_PROXY_METHOD, new=self._test_12_mock), \
             patch('odoo.addons.l10n_my_edi.models.account_move.SUBMISSION_MAX_SIZE', 1):
            self.submission_invoice.action_l10n_my_edi_send_invoice()

        self.assertEqual(self.submission_count, 5)
        valid_invoices = self.submission_invoice.filtered(lambda inv: inv.l10n_my_edi_state == "valid")
        self.assertEqual(len(valid_invoices), 4, 'The four invoices are in a valid state.')

        failed_invoice = self.submission_invoice.filtered(lambda inv: not inv.l10n_my_edi_state)
        self.assertEqual(len(failed_invoice), 1, 'One invoice has no state.')

    def test_13_multiple_cron_runs(self):
        """
        Simulate the cron running more than once; ensure that we correctly update l10n_my_edi_retry_at for valid invoices.
        For the purpose of the test, we will use two separate submissions.
        """
        all_invoices = self.env['account.move']
        # First submission of 5 invoices
        with patch(CONTACT_PROXY_METHOD, new=self._test_13_mock_first_submission):
            first_batch = self.env['account.move']
            for i in range(5):
                first_batch |= self.init_invoice(
                    'out_invoice', products=self.product_a, post=True,
                )
            with freeze_time('2024-07-15 10:00:00'):
                first_batch.action_l10n_my_edi_send_invoice()

        all_invoices |= first_batch

        # Second submission of 5 invoices.
        self.submission_status_count = 0
        with patch(CONTACT_PROXY_METHOD, new=self._test_13_mock):
            second_batch = self.basic_invoice
            for i in range(4):
                second_batch |= self.init_invoice(
                    'out_invoice', products=self.product_a, post=True,
                )
            with freeze_time('2024-07-15 10:00:00'):
                second_batch.action_l10n_my_edi_send_invoice()
                self.submission_status_count += 1  # Done once during the sending flow

        all_invoices |= second_batch

        with patch(CONTACT_PROXY_METHOD, new=self._test_13_mock):
            with freeze_time('2024-07-15 10:00:00'):
                # We use multiple invoices to test the cron logic, but all of them will always keep a same status so we can just validate the one.
                self.assertRecordValues(
                    self.basic_invoice,
                    [{
                        'l10n_my_edi_state': 'in_progress',
                        'l10n_my_edi_submission_uid': '123456789',
                        'l10n_my_edi_external_uuid': '123458974513510',
                    }]
                )

                # ... some time later, the cron runs.
                self.env['account.move']._cron_l10n_my_edi_synchronize_myinvois()
                self.submission_status_count += 1

                # The move got updated to valid, and the retry time should have been set.
                self.assertRecordValues(
                    self.basic_invoice,
                    [{
                        'l10n_my_edi_state': 'valid',
                        'l10n_my_edi_validation_time': datetime.strptime('2024-07-15 05:00:00', '%Y-%m-%d %H:%M:%S'),
                        'l10n_my_edi_invoice_long_id': '123-789-654',
                        'l10n_my_edi_retry_at': '2024-07-15 11:00:00',
                    }]
                )

            with freeze_time('2024-07-15 10:01:00'):
                # We have more invoices to process, the cron got triggered again. Our invoice won't trigger an API call
                self.env['account.move']._cron_l10n_my_edi_synchronize_myinvois()  # If failed to avoid the query, the mock method will raise.
                self.submission_status_count += 1

            with freeze_time('2024-07-15 11:00:00'):
                # One hour later, the next cron run starts and our invoice is updated again
                self.env['account.move']._cron_l10n_my_edi_synchronize_myinvois()
                self.submission_status_count += 1
                # We should have updated the status again, and thus pushed the l10n_my_edi_retry_at time to one hour later.
                self.assertRecordValues(
                    self.basic_invoice,
                    [{
                        'l10n_my_edi_state': 'valid',
                        'l10n_my_edi_validation_time': datetime.strptime('2024-07-15 05:00:00', '%Y-%m-%d %H:%M:%S'),
                        'l10n_my_edi_invoice_long_id': '123-789-654',
                        'l10n_my_edi_retry_at': '2024-07-15 12:00:00',
                    }]
                )


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
                        'long_id': '123-789-654',
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
                        'long_id': '123-789-654',
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
                        'long_id': '123-789-654',
                        'valid_datetime': '2024-07-15T05:00:00Z',
                    }
                },
                'document_count': 1,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_12_mock(self, endpoint, params):
        """ Mock response simulating multiple invoice submissions where one fails. """
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            self.submission_count += 1
            if self.submission_count == 5:
                return {
                    'error': {
                        'reference': 'internal_server_error',
                        'data': {},
                    }
                }
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

    def _test_13_mock_first_submission(self, endpoint, params):
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            res = {
                'submission_uid': '123456788',
                'documents': []
            }
            for i, document in enumerate(params['documents']):
                res['documents'].append({
                    'move_id': document['move_id'],
                    'uuid': f'12345897451350{i}',
                    'success': True,
                })
            return res
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses':
            return {
                'statuses': {
                    '123458974513500': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                    '123458974513501': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                    '123458974513502': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                    '123458974513503': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                    '123458974513504': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                },
                'document_count': 5,
            }
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))

    def _test_13_mock(self, endpoint, params):
        if endpoint == 'api/l10n_my_edi/1/submit_invoices':
            res = {
                'submission_uid': '123456789',
                'documents': []
            }
            for i, document in enumerate(params['documents']):
                res['documents'].append({
                    'move_id': document['move_id'],
                    'uuid': f'12345897451351{i}',
                    'success': True,
                })
            return res
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses' and self.submission_status_count == 0:
            return {
                'statuses': {
                    '123458974513510': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                    '123458974513511': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                    '123458974513512': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                    '123458974513513': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                    '123458974513514': {
                        'status': 'in_progress',
                        'reason': '',
                        'long_id': '',
                        'valid_datetime': '',
                    },
                },
                'document_count': 5,
            }
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses' and self.submission_status_count == 1:
            res = {'statuses': {}, 'document_count': 10}
            # Build the res using loops otherwise it'd take a lot of lines.
            for i in range(2):
                for j in range(5):
                    res['statuses'][f'1234589745135{i}{j}'] = {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '123-789-654',
                        'valid_datetime': '2024-07-15T05:00:00Z',
                    }
            return res
        elif endpoint == 'api/l10n_my_edi/1/get_submission_statuses' and self.submission_status_count == 3:
            res = {'statuses': {}, 'document_count': 10}
            # Build the res using loops otherwise it'd take a lot of lines.
            for i in range(2):
                for j in range(5):
                    res['statuses'][f'1234589745135{i}{j}'] = {
                        'status': 'valid',
                        'reason': '',
                        'long_id': '123-789-654',
                        'valid_datetime': '2024-07-15T05:00:00Z',
                    }
            return res
        else:
            raise UserError('Unexpected endpoint called during a test: %s with params %s.' % (endpoint, params))
