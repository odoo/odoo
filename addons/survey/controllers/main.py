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

import werkzeug
import logging

_logger = logging.getLogger(__name__)


class WebsiteSurvey(http.Controller):

    # Survey list
    @website.route(['/survey/',
        '/survey/list/'],
        type='http', auth='public', multilang=True)
    def list_surveys(self, **post):
        '''Lists all the public surveys'''
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']
        survey_ids = survey_obj.search(cr, uid, [('state', '=', 'open'),
                                                ('page_ids', '!=', 'None')],
            context=context)
        surveys = survey_obj.browse(cr, uid, survey_ids, context=context)
        return request.website.render('survey.list', {'surveys': surveys})

    # Survey filling, validation and storage
    @website.route(['/survey/fill/<model("survey.survey"):survey>'],
        type='http', auth='public', multilang=True)
    def fill_survey(self, survey=None, **post):
        '''Display and validates a survey'''
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']

        # In case of bad survey, redirect to surveys list
        if survey_obj.exists(cr, uid, survey.id, context=context) == []:
            return werkzeug.utils.redirect("/survey/")

        _logger.debug('Post request data: %s', post)

        # Store answer data
        # (/!\ assumes JavaScript validation of answers has succeeded!)
        # TODO

        # Display success message if totally succeeded
        if post and post['next'] == "finished":
            return request.website.render('survey.finished', {'survey': survey})

        # Page selection
        pagination = {'current': -1, 'next': 0}
        # Default pagination if first opening

        if 'current' in post and 'next' in post and post['next'] != "finished":
            oldnext = int(post['next'])
            if oldnext not in range(0, len(survey.page_ids)):
                raise Exception("This page does not exist")
            else:
                pagination['current'] = oldnext
            if oldnext == len(survey.page_ids) - 1:
                pagination['next'] = 'finished'
            else:
                pagination['next'] = oldnext + 1

        return request.website.render('survey.survey',
                                    {'survey': survey,
                                    'pagination': pagination})

    # @website.route(['/survey/prefill/<model("survey.survey"):survey>'], type='json', auth='public', multilang=True):

    # @website.route(['/survey/validate/<model("survey.survey"):survey>'],
    #                 type='json', auth='public', multilang=True)
    # def validate(self, survey=None, **post):
    #     # for each {K:V} in post, check
    #     _logger.debug("Incoming json data: " + post.__str__())
    #     return {'valid': True, 'errors': None}

    @website.route(['/survey/submit/<model("survey.survey"):survey>'],
                    type='json', auth='public', multilang=True)
    def submit(self, survey=None, **post):
        _logger.debug("Incoming json data: " + post.__str__())

        # transform post data into dictionary
        # for each {K:V} in post, check

        return {'redirect': '/survey/'}

    # Printing routes
    @website.route(['/survey/print/<model("survey.survey"):survey>/'],
        type='http', auth='public', multilang=True)
    def print_empty_survey(self, survey=None, **post):
        '''Display an empty survey in printable view'''
        pagination = {'current': -1, 'next': 0}
        return request.website.render('survey.survey_print',
                                    {'survey': survey,
                                    'pagination': pagination})
