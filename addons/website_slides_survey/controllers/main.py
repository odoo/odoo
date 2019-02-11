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
