# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import string

from odoo import api, models, _
from odoo.addons.iap.tools import iap_tools

OCR_VERSION = 102


class HrCandidate(models.Model):
    _name = 'hr.candidate'
    _inherit = ['extract.mixin', 'hr.candidate']

    @api.depends('partner_name')
    def _compute_is_in_extractable_state(self):
        self.is_in_extractable_state = True

    def _get_validation(self, field):
        text_to_send = {}
        if field == "email":
            text_to_send["content"] = self.email_from
        elif field == "phone":
            text_to_send["content"] = self.partner_phone
        elif field == "name":
            text_to_send["content"] = self.partner_name
        return text_to_send

    def _fill_document_with_results(self, ocr_results):
        if ocr_results is not None:
            name_ocr = self._get_ocr_selected_value(ocr_results, 'name', "")
            email_from_ocr = self._get_ocr_selected_value(ocr_results, 'email', "")
            phone_ocr = self._get_ocr_selected_value(ocr_results, 'phone', "")

            self.partner_name = name_ocr or self.partner_name
            self.email_from = self.email_from or email_from_ocr
            self.partner_phone = self.partner_phone or phone_ocr

            # If the 'hr_recruitment_skills' module is installed, extract skills from OCR results
            if self.env['ir.module.module']._get('hr_recruitment_skills').state == 'installed':
                ocr_text_lower = ocr_results['full_text_annotation'].lower()
                splitting_characters = string.punctuation.replace('-', '') + ' ' + '\n'
                ocr_tokens = re.sub('|'.join(re.escape(char) for char in splitting_characters), ' ', ocr_text_lower)
                skills = set(self.env['hr.skill'].search([]).filtered(lambda skill: (
                    re.search(rf'\b{re.escape(skill.name.lower())}\b', ocr_tokens)
                    and len(skill.name) >= 3
                )))

                applicant_skills = self.env['hr.candidate.skill']
                for skill in skills:
                    existing_applicant_skill = self.env['hr.candidate.skill'].search([
                        ('candidate_id', '=', self.id),
                        ('skill_id', '=', skill.id),
                    ])

                    skill_levels = skill.skill_type_id.skill_level_ids
                    if not existing_applicant_skill and skill_levels:
                        skill_level = skill_levels.filtered('default_level') or skill_levels[0]
                        applicant_skill = self.env['hr.candidate.skill'].create({
                            'candidate_id': self.id,
                            'skill_id': skill.id,
                            'skill_type_id': skill.skill_type_id.id,
                            'skill_level_id': skill_level.id,
                        })
                        applicant_skills += applicant_skill

    def _autosend_for_digitization(self):
        if self.env.company.recruitment_extract_show_ocr_option_selection == 'auto_send':
            self.filtered('extract_can_show_send_button')._send_batch_for_digitization()

    def _contact_iap_extract(self, pathinfo, params):
        params['version'] = OCR_VERSION
        params['account_token'] = self._get_iap_account().account_token
        endpoint = self.env['ir.config_parameter'].sudo().get_param('iap_extract_endpoint', 'https://extract.api.odoo.com')
        return iap_tools.iap_jsonrpc(endpoint + '/api/extract/applicant/2/' + pathinfo, params=params)

    def _get_ocr_module_name(self):
        return 'hr_recruitment_extract'

    def _get_ocr_option_can_extract(self):
        ocr_option = self.env.company.recruitment_extract_show_ocr_option_selection
        return ocr_option and ocr_option != 'no_send'

    def _get_validation_fields(self):
        return ['email', 'name', 'phone']

    def _get_user_error_invalid_state_message(self):
        return _("You cannot send a CV for this candidate!")

    def _message_set_main_attachment_id(self, attachments, force=False, filter_xml=True):
        res = super()._message_set_main_attachment_id(attachments, force=force, filter_xml=filter_xml)
        self._autosend_for_digitization()
        return res
