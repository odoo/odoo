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
from openerp import SUPERUSER_ID
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from datetime import datetime
import werkzeug
import json
import logging


_logger = logging.getLogger(__name__)


class WebsiteSurvey(http.Controller):

    ## HELPER METHODS ##

    def _check_bad_cases(self, cr, uid, request, survey_obj, survey, user_input_obj, context=None):
        # In case of bad survey, redirect to surveys list
        if survey_obj.exists(cr, SUPERUSER_ID, survey.id, context=context) == []:
            return werkzeug.utils.redirect("/survey/")

        # In case of auth required, block public user
        if survey.auth_required and uid == request.registry['website'].get_public_user(cr, uid, context):
            return request.website.render("website.401")

        # In case of non open surveys
        if survey.state != 'open':
            return request.website.render("survey.notopen")

        # If enough surveys completed
        if survey.user_input_limit > 0:
            completed = user_input_obj.search(cr, uid, [('state', '=', 'done')], count=True)
            if completed >= survey.user_input_limit:
                return request.website.render("survey.notopen")

        # Everything seems to be ok
        return None

    def _check_deadline(self, cr, uid, user_input, context=None):
        '''Prevent opening of the survey if the deadline has turned out

        ! This will NOT disallow access to users who have already partially filled the survey !'''
        if user_input.deadline:
            dt_deadline = datetime.strptime(user_input.deadline, DTF)
            dt_now = datetime.now()
            if dt_now > dt_deadline:  # survey is not open anymore
                return request.website.render("survey.notopen")

        return None

    ## ROUTES HANDLERS ##

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

    # Survey start
    @website.route(['/survey/start/<model("survey.survey"):survey>',
                    '/survey/start/<model("survey.survey"):survey>/<string:token>'],
                   type='http', auth='public', multilang=True)
    def start_survey(self, survey, token=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']
        user_input_obj = request.registry['survey.user_input']

        # Controls if the survey can be displayed
        errpage = self._check_bad_cases(cr, uid, request, survey_obj, survey, user_input_obj, context=context)
        if errpage:
            return errpage

        # Manual surveying
        if not token:
            if survey.visible_to_user:
                user_input_id = user_input_obj.create(cr, uid, {'survey_id': survey.id})
                user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]
            else:  # An user cannot open hidden surveys without token
                return request.website.render("website.403")
        else:
            try:
                user_input_id = user_input_obj.search(cr, uid, [('token', '=', token)])[0]
            except IndexError:  # Invalid token
                return request.website.render("website.403")
            else:
                user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]

        # Do not open expired survey
        errpage = self._check_deadline(cr, uid, user_input, context=context)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # Intro page
            data = {'survey': survey, 'page': None, 'token': user_input.token}
            return request.website.render('survey.survey_init', data)
        else:
            return request.redirect('/survey/fill/%s/%s' % (survey.id, user_input.token))

    # Survey displaying
    @website.route(['/survey/fill/<model("survey.survey"):survey>/<string:token>',
                    '/survey/fill/<model("survey.survey"):survey>/<string:token>/<string:prev>'],
                   type='http', auth='public', multilang=True)
    def fill_survey(self, survey, token, prev=None, **post):
        '''Display and validates a survey'''
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']
        user_input_obj = request.registry['survey.user_input']

        # Controls if the survey can be displayed
        errpage = self._check_bad_cases(cr, uid, request, survey_obj, survey, user_input_obj, context=context)
        if errpage:
            return errpage

        # Load the user_input
        try:
            user_input_id = user_input_obj.search(cr, uid, [('token', '=', token)])[0]
        except IndexError:  # Invalid token
            return request.website.render("website.403")
        else:
            user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]

        # Do not display expired survey (even if some pages have already been
        # displayed -- There's a time for everything!)
        errpage = self._check_deadline(cr, uid, user_input, context=context)
        if errpage:
            return errpage

        # Select the right page
        if user_input.state == 'new':  # First page
            page, page_nr, last = survey_obj.next_page(cr, uid, user_input, 0, go_back=False, context=context)
            data = {'survey': survey, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            if last:
                data.update({'last': True})
            return request.website.render('survey.survey', data)
        elif user_input.state == 'done':  # Display success message
            return request.website.render('survey.finished', {'survey': survey})
        elif user_input.state == 'skip':
            flag = (True if prev and prev == 'prev' else False)
            page, page_nr, last = survey_obj.next_page(cr, uid, user_input, user_input.last_displayed_page_id.id, go_back=flag, context=context)
            data = {'survey': survey, 'page': page, 'page_nr': page_nr, 'token': user_input.token}
            if last:
                data.update({'last': True})
            return request.website.render('survey.survey', data)
        else:
            return request.website.render("website.403")

    # AJAX prefilling of a survey
    @website.route(['/survey/prefill/<model("survey.survey"):survey>/<string:token>',
                    '/survey/prefill/<model("survey.survey"):survey>/<string:token>/<model("survey.page"):page>'],
                   type='http', auth='public', multilang=True)
    def prefill(self, survey, token, page=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        user_input_line_obj = request.registry['survey.user_input_line']
        ret = {}

        # Fetch previous answers
        if page:
            ids = user_input_line_obj.search(cr, uid, [('user_input_id.token', '=', token), ('page_id', '=', page.id)], context=context)
        else:
            ids = user_input_line_obj.search(cr, uid, [('user_input_id.token', '=', token)], context=context)
        previous_answers = user_input_line_obj.browse(cr, uid, ids, context=context)

        # Return non empty answers in a JSON compatible format
        for answer in previous_answers:
            if not answer.skipped:
                answer_tag = '%s_%s_%s' % (answer.survey_id.id, answer.page_id.id, answer.question_id.id)
                answer_value = None
                if answer.answer_type == 'free_text':
                    answer_value = answer.value_free_text
                elif answer.answer_type == 'text':
                    answer_value = answer.value_text
                elif answer.answer_type == 'number':
                    answer_value = answer.value_number
                elif answer.answer_type == 'date':
                    answer_value = answer.value_date
                # TODO mettre les QCM ici
                if answer_value:
                    ret.update({answer_tag: answer_value})
                else:
                    _logger.warning("[survey] Fetching None answer for question %s" % answer_tag)

        return json.dumps(ret)

    # load all the user input lines corresponding to token & page (or survey)
    # format them into a json dict
    # return them to JS

    # AJAX validation of some questions
    # @website.route(['/survey/validate/<model("survey.survey"):survey>'],
    #                type='http', auth='public', multilang=True)
    # def validate(self, survey, **post):

    # AJAX submission of a page
    @website.route(['/survey/submit/<model("survey.survey"):survey>'],
                   type='http', auth='public', multilang=True)
    def submit(self, survey, **post):
        _logger.debug('Incoming data: %s', post)
        page_id = int(post['page_id'])
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']
        questions_obj = request.registry['survey.question']
        questions_ids = questions_obj.search(cr, uid, [('page_id', '=', page_id)], context=context)
        questions = questions_obj.browse(cr, uid, questions_ids, context=context)

        # Answer validation
        errors = {}
        for question in questions:
            answer_tag = "%s_%s_%s" % (survey.id, page_id, question.id)
            errors.update(questions_obj.validate_question(cr, uid, question, post, answer_tag, context=context))

        ret = {}
        if (len(errors) != 0):
            # Return errors messages to webpage
            ret['errors'] = errors
        else:
            # Store answers into database
            user_input_obj = request.registry['survey.user_input']

            user_input_line_obj = request.registry['survey.user_input_line']
            try:
                user_input_id = user_input_obj.search(cr, uid, [('token', '=', post['token'])], context=context)[0]
            except KeyError:  # Invalid token
                return request.website.render("website.403")
            for question in questions:
                answer_tag = "%s_%s_%s" % (survey.id, page_id, question.id)
                user_input_line_obj.save_lines(cr, uid, user_input_id, question, post, answer_tag, context=context)

            user_input = user_input_obj.browse(cr, uid, user_input_id, context=context)
            go_back = post['button_submit'] == 'previous'
            next_page, _, last = survey_obj.next_page(cr, uid, user_input, page_id, go_back=go_back, context=context)
            vals = {'last_displayed_page_id': page_id}
            if next_page is None and not go_back:
                vals.update({'state': 'done'})
            else:
                vals.update({'state': 'skip'})
            user_input_obj.write(cr, uid, user_input_id, vals, context=context)
            ret['redirect'] = '/survey/fill/%s/%s' % (survey.id, post['token'])
            if go_back:
                ret['redirect'] += '/prev'
        return json.dumps(ret)

    # Printing routes
    @website.route(['/survey/print/<model("survey.survey"):survey>/'],
                   type='http', auth='user', multilang=True)
    def print_empty_survey(self, survey=None, **post):
        '''Display an empty survey in printable view'''
        return request.website.render('survey.survey_print',
                                      {'survey': survey, 'page_nr': 0})

# vim: exp and tab: smartindent: tabstop=4: softtabstop=4: shiftwidth=4:
