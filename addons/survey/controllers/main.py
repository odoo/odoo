# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
# from openerp.tools.translate import _
# from openerp.tools.safe_eval import safe_eval

# import simplejson
# import werkzeug


class WebsiteSurvey(http.Controller):

    @website.route(['/survey/',
        '/survey/list/'],
        type='http', auth='public', multilang=True)
    def list_surveys(self, survey_id=None, page_id=None, **post):
        '''All the public surveys'''
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']
        survey_ids = survey_obj.search(cr, uid, [('state', '=', 'open')],
            context=context)
        surveys = survey_obj.browse(cr, uid, survey_ids, context=context)
        return request.website.render('survey.list', {'surveys': surveys})

    @website.route(["/survey/fill/id/<int:survey_id>/",
        "/survey/fill/id/<int:survey_id>/page/<int:page_id>"],
        type='http', auth='public', multilang=True)
    def fill_survey(self, survey_id=None, page_id=None, **post):
        '''Display a survey'''
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']

        survey = survey_obj.browse(cr, uid, survey_id, context=context)
        return request.website.render('survey.survey',
            {'survey': survey})
