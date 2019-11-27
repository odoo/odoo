# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteSlidesSurvey(http.Controller):
    @http.route(['/slides_survey/certification/fetch_certification_info'], type='json', auth='user', methods=['POST'], website=True)
    def slides_fetch_certification_info(self, fields):
        can_create = request.env['survey.survey'].check_access_rights('create', raise_exception=False)
        return {
            'read_results': request.env['survey.survey'].search_read([('certificate', '=', True)], fields),
            'can_create': can_create,
        }
