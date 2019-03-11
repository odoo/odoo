# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteSlidesSurvey(http.Controller):
    @http.route(['/slides_survey/certification/search_read'], type='json', auth='user', methods=['POST'], website=True)
    def slides_certification_search_read(self, fields):
        return {
            'read_results': request.env['survey.survey'].search_read([('certificate', '=', True)], fields),
        }

    @http.route(['/slides_survey/certification_url/get'], type='json', auth='user', website=True)
    def get_certification_url(self, slide_id):
        slide = request.env['slide.slide'].browse(slide_id)
        slide.action_set_viewed()
        certification_url = None
        if not request.env.user._is_public() and slide.slide_type == 'certification' and slide.survey_id:
            if slide.channel_id.is_member:
                user_membership_id_sudo = slide.user_membership_id.sudo()
                quizz_passed = user_membership_id_sudo.survey_quizz_passed
                if not quizz_passed:
                    last_user_input = next(user_input for user_input in user_membership_id_sudo.user_input_ids.sorted(
                        lambda user_input: user_input.create_date, reverse=True
                    ))
                    certification_url = last_user_input._get_survey_url()
        return  {
            "certification_url": certification_url
        }
