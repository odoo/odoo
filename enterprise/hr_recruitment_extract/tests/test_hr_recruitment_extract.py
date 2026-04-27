# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.iap_extract.tests.test_extract_mixin import TestExtractMixin
from odoo.tests import tagged

from ..models.hr_candidate import OCR_VERSION


@tagged('post_install', '-at_install')
class TestRecruitmentExtractProcess(TestHrCommon, TestExtractMixin):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.candidate = cls.env['hr.candidate'].create({'partner_name': 'John Doe'})
        cls.attachment = cls.env['ir.attachment'].create({
            'name': "an attachment",
            'raw': b'My attachment',
            'mimetype': 'plain/text'
        })

    def get_result_success_response(self):
        return {
            'status': 'success',
            'results': [{
                'name': {'selected_value': {'content': 'Johnny Doe'}, 'candidates': []},
                'email': {'selected_value': {'content': 'john@doe.com'}, 'candidates': []},
                'phone': {'selected_value': {'content': '+32488888888'}, 'candidates': []},
                'full_text_annotation': '',
            }],
        }

    def test_auto_send_for_digitization(self):
        # test the `auto_send` mode for digitization does send the attachment upon upload
        self.env.company.recruitment_extract_show_ocr_option_selection = 'auto_send'
        expected_parse_params = {
            'version': OCR_VERSION,
            'account_token': 'test_token',
            'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'documents': [self.attachment.datas.decode('utf-8')],
            'user_infos': {
                'user_email': self.env.ref('base.user_root').email,
                'user_lang': self.env.ref('base.user_root').lang,
            },
            'webhook_url': f'{self.candidate.get_base_url()}/hr_recruitment_extract/request_done',
        }

        with self._mock_iap_extract(
            extract_response=self.parse_success_response(),
            assert_params=expected_parse_params,
        ):
            self.candidate.message_post(attachment_ids=[self.attachment.id])

        self.assertEqual(self.candidate.extract_state, 'waiting_extraction')
        self.assertEqual(self.candidate.extract_document_uuid, 'some_token')
        self.assertTrue(self.candidate.extract_state_processed)
        self.assertTrue(self.candidate.partner_name)
        self.assertFalse(self.candidate.email_from)
        self.assertFalse(self.candidate.partner_phone)

        extract_response = self.get_result_success_response()
        expected_get_results_params = {
            'version': OCR_VERSION,
            'document_token': 'some_token',
            'account_token': self.candidate._get_iap_account().account_token,
        }
        with self._mock_iap_extract(
            extract_response=extract_response,
            assert_params=expected_get_results_params,
        ):
            self.candidate.check_all_status()

        self.assertEqual(self.candidate.partner_name, extract_response['results'][0]['name']['selected_value']['content'])
        self.assertEqual(self.candidate.email_from, extract_response['results'][0]['email']['selected_value']['content'])
        self.assertEqual(self.candidate.partner_phone, extract_response['results'][0]['phone']['selected_value']['content'])

    def test_manual_send_for_digitization(self):
        # test the `manual_send` mode for digitization
        self.env.company.recruitment_extract_show_ocr_option_selection = 'manual_send'

        self.assertEqual(self.candidate.extract_state, 'no_extract_requested')
        self.assertFalse(self.candidate.extract_can_show_send_button)

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.candidate.message_post(attachment_ids=[self.attachment.id])

        self.assertEqual(self.candidate.extract_state, 'no_extract_requested')
        self.assertTrue(self.candidate.extract_can_show_send_button)

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.candidate.action_send_batch_for_digitization()

        # upon success, no button shall be provided
        self.assertFalse(self.candidate.extract_can_show_send_button)

        extract_response = self.get_result_success_response()
        with self._mock_iap_extract(extract_response=extract_response):
            self.candidate.check_all_status()

        self.assertEqual(self.candidate.partner_name, extract_response['results'][0]['name']['selected_value']['content'])
        self.assertEqual(self.candidate.email_from, extract_response['results'][0]['email']['selected_value']['content'])
        self.assertEqual(self.candidate.partner_phone, extract_response['results'][0]['phone']['selected_value']['content'])

    def test_no_send_for_digitization(self):
        # test that the `no_send` mode for digitization prevents the users from sending
        self.env.company.recruitment_extract_show_ocr_option_selection = 'no_send'

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.candidate.message_post(attachment_ids=[self.attachment.id])

        self.assertEqual(self.candidate.extract_state, 'no_extract_requested')
        self.assertFalse(self.candidate.extract_can_show_send_button)

    def test_show_resend_button_when_not_enough_credits(self):
        # test that upon not enough credit error, the retry button is provided
        self.env.company.recruitment_extract_show_ocr_option_selection = 'auto_send'

        with self._mock_iap_extract(extract_response=self.parse_credit_error_response()):
            self.candidate.message_post(attachment_ids=[self.attachment.id])

        self.assertFalse(self.candidate.extract_can_show_send_button)

    def test_status_not_ready(self):
        # test the 'processing' ocr status effects
        self.env.company.recruitment_extract_show_ocr_option_selection = 'auto_send'

        with self._mock_iap_extract(extract_response=self.parse_processing_response()):
            self.candidate._check_ocr_status()

        self.assertEqual(self.candidate.extract_state, 'extract_not_ready')
        self.assertFalse(self.candidate.extract_can_show_send_button)

    def test_applicant_validation(self):
        # test that when the applicant is hired, the validation is sent to the server
        self.env.company.recruitment_extract_show_ocr_option_selection = 'auto_send'

        with self._mock_iap_extract(extract_response=self.parse_success_response()):
            self.candidate.message_post(attachment_ids=[self.attachment.id])

        with self._mock_iap_extract(extract_response=self.get_result_success_response()):
            self.candidate._check_ocr_status()

        self.assertEqual(self.candidate.extract_state, 'waiting_validation')

        expected_validation_params = {
            'version': OCR_VERSION,
            'values': {
                'email': {'content': self.candidate.email_from},
                'phone': {'content': self.candidate.partner_phone},
                'name': {'content': self.candidate.partner_name},
            },
            'document_token': 'some_token',
            'account_token': self.candidate._get_iap_account().account_token,
        }

        hired_stages = self.env['hr.recruitment.stage'].search([('hired_stage', '=', True)])
        applicant = self.env['hr.applicant'].create({'candidate_id': self.candidate.id})
        with self._mock_iap_extract(
            extract_response=self.validate_success_response(),
            assert_params=expected_validation_params,
        ):
            applicant.write({'stage_id': hired_stages[0].id})

        self.assertEqual(self.candidate.extract_state, 'done')

    def test_skill_search_on_ocr_results(self):
        if not self.env['ir.module.module']._get('hr_recruitment_skills').state == 'installed':
            self.skipTest("If the 'hr_recruitment_skills' module isn't installed we don't extract skills!")

        extract_response = self.get_result_success_response()
        extract_response['results'][0]['full_text_annotation'] = 'UIUX designer and graphist'

        levels = self.env['hr.skill.level'].create([{
            'name': f'Level {x}',
            'level_progress': x * 10,
        } for x in range(10)])

        skill_type = self.env['hr.skill.type'].create({
            'name': 'Technical',
            'skill_level_ids': levels.ids,
        })
        skills = self.env['hr.skill'].create([{
            'name': 'UIUX',
            'skill_type_id': skill_type.id,
        }, {
            'name': 'graphist',
            'skill_type_id': skill_type.id,
        }])

        with self._mock_iap_extract(extract_response=extract_response):
            self.candidate._check_ocr_status()

        created_candidate_skills = self.env['hr.candidate.skill'].search(
            [('candidate_id', '=', self.candidate.id)],
        ).mapped('skill_id.id')

        self.assertCountEqual(created_candidate_skills, skills.mapped('id'))
