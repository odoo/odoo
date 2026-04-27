from unittest.mock import patch

from freezegun import freeze_time

from odoo import fields
from odoo.tests import Form, tagged, users
from odoo.tools import float_compare

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.hr_expense_extract.models.hr_expense import OCR_VERSION
from odoo.addons.hr_expense_predict_product.models.hr_expense import HrExpense
from odoo.addons.iap_extract.tests.test_extract_mixin import TestExtractMixin


@tagged('post_install', '-at_install')
class TestExpenseExtractProcess(TestExpenseCommon, TestExtractMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.expense = cls.env['hr.expense'].create({
            'employee_id': cls.expense_employee.id,
            'product_id': cls.product_c.id,
        })

        cls.attachment = cls.env['ir.attachment'].create({
            'name': "product_c.jpg",
            'raw': b'My expense',
        })

    @classmethod
    def default_env_context(cls):
        # OVERRIDE to reactivate the tracking
        return {}

    def get_result_success_response(self):
        return {
            'status': 'success',
            'results': [{
                'description': {'selected_value': {'content': 'Pizzeria', 'candidates': []}},
                'total': {'selected_value': {'content': 99.99, 'candidates': []}},
                'date': {'selected_value': {'content': '2022-02-22', 'candidates': []}},
                'currency': {'selected_value': {'content': 'euro', 'candidates': []}},
            }],
        }

    def test_auto_send_for_digitization(self):
        # test that the uploaded attachment is sent to the extract server when `auto_send` is set
        self.env.company.expense_extract_show_ocr_option_selection = 'auto_send'
        expected_parse_params = {
            'version': OCR_VERSION,
            'account_token': 'test_token',
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'documents': [self.attachment.datas.decode('utf-8')],
            'user_infos': {
                'user_email': self.user.email,
                'user_lang': self.env.ref('base.user_root').lang,
            },
            'webhook_url': f'{self.expense.get_base_url()}/hr_expense_extract/request_done',
        }

        usd_currency = self.env.ref('base.USD')
        eur_currency = self.env.ref('base.EUR')
        eur_currency.rate_ids.unlink()
        eur_currency.active = True

        with self._mock_iap_extract(
            extract_response=self.parse_success_response(),
            assert_params=expected_parse_params,
        ):
            self.expense.message_post(attachment_ids=[self.attachment.id])

        self.assertEqual(self.expense.extract_state, 'waiting_extraction')
        self.assertEqual(self.expense.extract_document_uuid, 'some_token')
        self.assertTrue(self.expense.extract_state_processed)
        self.assertEqual(self.expense.predicted_category, 'miscellaneous')
        self.assertFalse(self.expense.total_amount)
        self.assertEqual(self.expense.currency_id, usd_currency)

        extract_response = self.get_result_success_response()
        expected_get_results_params = {
            'version': OCR_VERSION,
            'document_token': 'some_token',
            'account_token': self.expense._get_iap_account().account_token,
        }
        with self._mock_iap_extract(
            extract_response=extract_response,
            assert_params=expected_get_results_params,
        ):
            self.expense.check_all_status()

        ext_result = extract_response['results'][0]
        self.assertEqual(self.expense.extract_state, 'waiting_validation')
        self.assertEqual(float_compare(self.expense.total_amount, ext_result['total']['selected_value']['content'], 2), 0)
        self.assertEqual(self.expense.currency_id, eur_currency)
        self.assertEqual(str(self.expense.date), ext_result['date']['selected_value']['content'])
        self.assertEqual(self.expense.product_id, self.product_c)

    def test_manual_send_for_digitization(self):
        # test the `manual_send` mode for digitization.
        self.env.company.expense_extract_show_ocr_option_selection = 'manual_send'
        extract_response = self.get_result_success_response()

        eur_currency = self.env.ref('base.EUR')
        eur_currency.active = True

        self.assertEqual(self.expense.extract_state, 'no_extract_requested')
        self.assertFalse(self.expense.extract_can_show_send_button)

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.expense.message_post(attachment_ids=[self.attachment.id])

        self.assertEqual(self.expense.extract_state, 'no_extract_requested')
        self.assertTrue(self.expense.extract_can_show_send_button)

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.expense.action_send_batch_for_digitization()

        # upon success, no button shall be provided
        self.assertFalse(self.expense.extract_can_show_send_button)

        with self._mock_iap_extract(extract_response=extract_response):
            self.expense.check_all_status()

        ext_result = extract_response['results'][0]
        self.assertEqual(self.expense.extract_state, 'waiting_validation')
        self.assertEqual(float_compare(self.expense.total_amount, ext_result['total']['selected_value']['content'], 2), 0)
        self.assertEqual(self.expense.currency_id, eur_currency)
        self.assertEqual(str(self.expense.date), ext_result['date']['selected_value']['content'])
        self.assertEqual(self.expense.product_id, self.product_c)

    def test_no_send_for_digitization(self):
        # test that the `no_send` mode for digitization prevents the users from sending
        self.env.company.expense_extract_show_ocr_option_selection = 'no_send'

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.expense.message_post(attachment_ids=[self.attachment.id])

        self.assertEqual(self.expense.extract_state, 'no_extract_requested')
        self.assertFalse(self.expense.extract_can_show_send_button)

    def test_show_resend_button_when_not_enough_credits(self):
        # test that upon not enough credit error, the retry button is provided
        self.env.company.expense_extract_show_ocr_option_selection = 'auto_send'

        with self._mock_iap_extract(extract_response=self.parse_credit_error_response()):
            self.expense.message_post(attachment_ids=[self.attachment.id])

        self.assertFalse(self.expense.extract_can_show_send_button)

    def test_status_not_ready(self):
        # test the 'processing' ocr status effects
        self.env.company.expense_extract_show_ocr_option_selection = 'auto_send'

        with self._mock_iap_extract(extract_response=self.parse_processing_response()):
            self.expense._check_ocr_status()

        self.assertEqual(self.expense.extract_state, 'extract_not_ready')
        self.assertFalse(self.expense.extract_can_show_send_button)

    def test_expense_validation(self):
        # test that when the expense is hired, the validation is sent to the server
        self.env.company.expense_extract_show_ocr_option_selection = 'auto_send'

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.expense.message_post(attachment_ids=[self.attachment.id])

        with self._mock_iap_extract(self.get_result_success_response()):
            self.expense._check_ocr_status()

        self.assertEqual(self.expense.extract_state, 'waiting_validation')

        expected_validation_params = {
            'version': OCR_VERSION,
            'values': {
                'total': {'content': self.expense.price_unit},
                    'date': {'content': str(self.expense.date)},
                    'description': {'content': self.expense.name},
                    'currency': {'content': self.expense.currency_id.name},
            },
            'document_token': 'some_token',
            'account_token': self.expense._get_iap_account().account_token,
        }

        with self._mock_iap_extract(
            extract_response=self.validate_success_response(),
            assert_params=expected_validation_params,
        ):
            self.expense.action_submit_expenses()

        self.assertEqual(self.expense.extract_state, 'done')

    def test_no_digitisation_for_posted_entries(self):
        # Tests that if a move is created from an expense, it is not digitised again.
        self.env.company.expense_extract_show_ocr_option_selection = 'auto_send'

        self.expense.message_post(attachment_ids=[self.attachment.id])

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': self.expense.name,
            'employee_id': self.expense.employee_id.id,
            'expense_line_ids': self.expense.ids,
        })
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        move = expense_sheet.account_move_ids
        self.assertFalse(move._needs_auto_extract())

    def test_no_change_in_price_unit_with_expense_no_extract(self):
        """
        Test that the price unit does not change when the quantity changes after uploading an attachment
        when there is no digitisation
        """
        expense = self.env['hr.expense'].create({
            'name': 'expense',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
        })
        with Form(expense) as form:
            self.assertEqual(form.price_unit, 800)

        self.env['ir.attachment'].create({
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
            'name': 'file1.png',
            'res_model': 'hr.expense',
            'res_id': expense.id,
        })

        with Form(expense) as form:
            form.quantity = 2
            self.assertEqual(form.price_unit, 800)

    def test_extract_multi_currencies(self):
        """Test that exchange rate is fetched during extraction"""
        self.env.ref('base.EUR').active = True
        self.env['res.currency.rate'].create({
                'name': '2022-01-01',
                'rate': 3,
                'currency_id': self.env.ref('base.EUR').id,
                'company_id': self.env.company.id,
            })
        ocr_results = self.get_result_success_response()['results'][0]
        self.expense.name = ""
        self.expense._fill_document_with_results(ocr_results=ocr_results)

        self.assertEqual(self.expense.total_amount, 33.33)

    def test_extract_multi_currencies_with_several_possible_currencies(self):
        """Test that the extraction does not crash"""
        ocr_results = {
                'description': {'selected_value': {'content': 'Pizzeria', 'candidates': []}},
                'total': {'selected_value': {'content': 99.99, 'candidates': []}},
                'date': {'selected_value': {'content': '2022-02-22', 'candidates': []}},
                'currency': {'selected_value': {'content': '$', 'candidates': []}},
            }
        self.expense.name = ""
        self.expense._fill_document_with_results(ocr_results=ocr_results)

        self.assertTrue(self.expense.currency_id)

    def test_extract_without_possible_currencies(self):
        """Test that the extraction does not crash"""
        ocr_results = {
                'description': {'selected_value': {'content': 'Pizzeria', 'candidates': []}},
                'total': {'selected_value': {'content': 99.99, 'candidates': []}},
                'date': {'selected_value': {'content': '2022-02-22', 'candidates': []}},
                'currency': {'selected_value': {'content': 'undefined', 'candidates': []}},
            }
        self.expense.name = ""
        self.expense._fill_document_with_results(ocr_results=ocr_results)

        self.assertTrue(self.expense.currency_id)

    def test_extract_no_total(self):
        ocr_results = self.get_result_success_response()['results'][0]
        del ocr_results['total']
        self.expense.name = ""
        self.expense._fill_document_with_results(ocr_results=ocr_results)

        self.assertAlmostEqual(self.expense.total_amount_currency, 0, 2)
        self.assertAlmostEqual(self.expense.total_amount, 0, 2)
        self.assertEqual(self.expense.currency_id.name, 'EUR')
        self.assertEqual(self.expense.date, fields.Date.to_date('2022-02-22'))

    def test_extract_no_currency(self):
        self.env['res.currency.rate'].create({
            'name': '2022-01-01',
            'rate': 3,
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.company.id,
        })

        ocr_results = self.get_result_success_response()['results'][0]
        del ocr_results['currency']
        self.expense.name = ""
        self.expense._fill_document_with_results(ocr_results=ocr_results)

        self.assertAlmostEqual(self.expense.total_amount_currency, 99.99, 2)
        self.assertAlmostEqual(self.expense.total_amount, 99.99, 2)
        self.assertEqual(self.expense.currency_id.name, 'USD')
        self.assertEqual(self.expense.date, fields.Date.to_date('2022-02-22'))

    def test_expense_extract_product_with_cost_only_company_currency(self):
        """
        Test that when an expense having a product whith a standard_price set up, we never change the currency
        from the default company currency
        """
        eur_currency = self.env.ref('base.EUR')
        eur_currency.active = True
        company_currency = self.env.company.currency_id

        self.env['res.currency.rate'].sudo().create({
            'name': '2022-01-01',
            'rate': 10,
            'currency_id': eur_currency.id,
            'company_id': self.env.company.id,
        })

        attachment = self.env['ir.attachment'].with_user(self.expense_user_employee).create({
            'name': 'test_attachment.png',
            'res_model': 'hr.expense',
            'raw': b"R0lGODdhAQABAIAAAP///////ywAAAAAAQABAAACAkQBADs=",
        })
        extract_response = self.get_result_success_response()
        extract_response['document_token'] = 'some_token'
        extract_response['results'][0]['total']['selected_value']['content'] = 100
        extract_response['results'][0]['currency']['selected_value']['content'] = '€'
        with (
            self._mock_iap_extract(extract_response=extract_response),
            patch.object(HrExpense, '_predict_product', side_effect=lambda *args, **kwargs: self.product_a.id)
        ):
            self.env['hr.expense'].with_user(self.expense_user_employee).create_expense_from_attachments(attachment.ids)
            expense = self.env['hr.expense'].search([('attachment_ids', '=', attachment.id)]).ensure_one()
            expense._fill_document_with_results(ocr_results=extract_response['results'][0])

        self.assertNotEqual(company_currency.id, eur_currency.id)
        self.assertRecordValues(
            expense,
            [{'total_amount_currency': 800.0, 'total_amount': 800.0, 'currency_id': company_currency.id, 'product_id': self.product_a.id}],
        )

    @freeze_time('2024-01-01')
    def test_extract_no_date(self):
        self.env['res.currency.rate'].create({
            'name': '2022-01-01',
            'rate': 3,
            'currency_id': self.env.ref('base.EUR').id,
            'company_id': self.env.company.id,
        })

        ocr_results = self.get_result_success_response()['results'][0]
        del ocr_results['date']
        self.expense.name = ""
        self.expense.date = None
        self.expense._fill_document_with_results(ocr_results=ocr_results)

        self.assertAlmostEqual(self.expense.total_amount_currency, 99.99, 2)
        self.assertAlmostEqual(self.expense.total_amount, 33.33, 2)
        self.assertEqual(self.expense.currency_id.name, 'EUR')
        self.assertEqual(self.expense.date, fields.Date.to_date('2024-01-01'))

    @users('admin')
    def test_expense_ocr_note_author(self):
        attachment = self.env['ir.attachment'].create({
            'name': 'test_attachment.png',
            'res_model': 'hr.expense',
            'raw': b'My expense',
        })
        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.env['hr.expense'].create_expense_from_attachments(attachment.ids)

        expense = self.env['hr.expense'].search([('attachment_ids', '=', attachment.id)]).ensure_one()
        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            expense.check_all_status()

        self.env.cr.flush()
        message = self.env['mail.message'].search([
            ('model', '=', 'hr.expense'),
            ('res_id', '=', expense.id),
            ('tracking_value_ids', '!=', False),
        ]).ensure_one()
        author_name = message.author_id.complete_name
        self.assertEqual(author_name, 'OdooBot')

    def test_extract_conversion_when_currency_already_set(self):
        """ Test that if EUR is already set on the record, the USD total still updates correctly from OCR """
        eur_currency = self.env.ref('base.EUR')
        eur_currency.active = True

        self.env['res.currency.rate'].create({
            'name': '2022-02-22',
            'rate': 1.0 / 3.0,
            'currency_id': eur_currency.id,
            'company_id': self.env.company.id,
        })

        self.expense.write({
            'currency_id': eur_currency.id,
            'total_amount_currency': 1.0,
            'total_amount': 3.0,
        })

        ocr_results = self.get_result_success_response()['results'][0]
        ocr_results['total']['selected_value']['content'] = 50.0
        ocr_results['currency']['selected_value']['content'] = 'EUR'
        ocr_results['date']['selected_value']['content'] = '2022-02-22'

        self.expense.name = ""
        self.expense._fill_document_with_results(ocr_results=ocr_results)

        self.assertEqual(self.expense.total_amount_currency, 50.0)
        self.assertAlmostEqual(self.expense.total_amount, 150.0)
