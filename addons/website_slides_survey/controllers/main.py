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
        if slide:
            slide.action_set_viewed()
            return {
                "certification_url": slide.action_get_slide_survey_url()
            }
        return {
            "error": "Slide not found"
        }