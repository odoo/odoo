from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.iap_extract.tests.test_extract_mixin import TestExtractMixin
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged

from ..models.account_bank_statement import OCR_VERSION


@tagged('post_install', '-at_install')
class TestBankStatementExtractProcess(AccountTestInvoicingCommon, TestExtractMixin, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.groups_id |= cls.env.ref('base.group_system')

        cls.bank_journal = cls.env['account.journal'].create({
            'name': 'Bank 123456',
            'code': 'BNK67',
            'type': 'bank',
            'bank_acc_number': '123456',
            'currency_id': cls.env.ref('base.EUR').id,
        })
        cls.bank_statement = cls.env['account.bank.statement'].create({
            'journal_id': cls.bank_journal.id,
        })
        cls.attachment = cls.env['ir.attachment'].create({
            'name': "an attachment",
            'raw': b'My attachment',
            'mimetype': 'plain/text'
        })

    def get_result_success_response(self):
        return {
            'status': 'success',
            'results': [{
                'balance_start': {'selected_value': {'content': -669.79}, 'candidates': []},
                'balance_end': {'selected_value': {'content': -588.62}, 'candidates': []},
                'date': {'selected_value': {'content': '2021-08-24'}, 'candidates': []},
                'bank_statement_lines': [
                    {
                        "amount": 669.79,
                        "description": "Domiciliation auprès de votre banque",
                        "date": "2021-07-26",
                    },
                    {
                        "amount": -15.0,
                        "description": "STIB-MIVB GO 50411 ETTERBEEK BEL",
                        "date": "2021-07-31",
                    },
                    {
                        "amount": -121.63,
                        "description": "LUFTHANSA AG2202464500936KOELN DE",
                        "date": "2021-08-18",
                    },
                    {
                        "amount": -253.54,
                        "description": "IWG BELGIUM BUSINESS CENTBRUSSELS BE",
                        "date": "2021-08-19",
                    },
                    {
                        "amount": -18.0,
                        "description": "Taxi Risou Bruxelles BE",
                        "date": "2021-08-21",
                    },
                    {
                        "amount": -180.45,
                        "description": "LUFTHANSA AG2202464565889KOELN DE",
                        "date": "2021-08-24",
                    },
                ],
            }],
        }

    def test_auto_send_for_digitization(self):
        # test the `auto_send` mode for digitization does send the attachment upon upload
        self.env.company.extract_bank_statement_digitalization_mode = 'auto_send'
        expected_parse_params = {
            'version': OCR_VERSION,
            'account_token': 'test_token',
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'documents': [self.attachment.datas.decode('utf-8')],
            'user_infos': {
                'user_email': self.user.email,
                'user_lang': self.env.ref('base.user_root').lang,
                'journal_type': self.bank_journal.type,
            },
            'webhook_url': f'{self.bank_statement.get_base_url()}/account_bank_statement_extract/request_done',
        }

        with self._mock_iap_extract(
            extract_response=self.parse_success_response(),
            assert_params=expected_parse_params,
        ):
            self.bank_statement.message_post(attachment_ids=[self.attachment.id])

        self.assertEqual(self.bank_statement.extract_state, 'waiting_extraction')
        self.assertEqual(self.bank_statement.extract_document_uuid, 'some_token')
        self.assertTrue(self.bank_statement.extract_state_processed)
        self.assertFalse(self.bank_statement.balance_start)
        self.assertFalse(self.bank_statement.balance_end)
        self.assertFalse(self.bank_statement.date)
        self.assertFalse(self.bank_statement.line_ids)

        extract_response = self.get_result_success_response()
        expected_get_results_params = {
            'version': OCR_VERSION,
            'document_token': 'some_token',
            'account_token': self.bank_statement._get_iap_account().account_token,
        }
        with self._mock_iap_extract(
            extract_response=extract_response,
            assert_params=expected_get_results_params,
        ):
            self.bank_statement.check_all_status()

        extract_results = extract_response['results'][0]
        self.assertEqual(self.bank_statement.balance_start, extract_results['balance_start']['selected_value']['content'])
        self.assertEqual(self.bank_statement.balance_end, extract_results['balance_end']['selected_value']['content'])
        self.assertEqual(str(self.bank_statement.date), extract_results['date']['selected_value']['content'])
        self.assertEqual(len(self.bank_statement.line_ids), len(extract_results['bank_statement_lines']))

    def test_no_send_for_digitization(self):
        # test that the `no_send` mode for digitization prevents the users from sending
        self.env.company.extract_bank_statement_digitalization_mode = 'no_send'

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.bank_statement.message_post(attachment_ids=[self.attachment.id])

        self.assertEqual(self.bank_statement.extract_state, 'no_extract_requested')
        self.assertFalse(self.bank_statement.extract_can_show_send_button)

    def test_show_resend_button_when_not_enough_credits(self):
        # test that upon not enough credit error, the retry button is provided
        self.env.company.extract_bank_statement_digitalization_mode = 'auto_send'

        with self._mock_iap_extract(extract_response=self.parse_credit_error_response()):
            self.bank_statement.message_post(attachment_ids=[self.attachment.id])

        self.assertFalse(self.bank_statement.extract_can_show_send_button)

    def test_status_not_ready(self):
        # test the 'processing' ocr status effects
        self.env.company.extract_bank_statement_digitalization_mode = 'auto_send'

        with self._mock_iap_extract(extract_response=self.parse_processing_response()):
            self.bank_statement._check_ocr_status()

        self.assertEqual(self.bank_statement.extract_state, 'extract_not_ready')
        self.assertFalse(self.bank_statement.extract_can_show_send_button)
