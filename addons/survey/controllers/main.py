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
import werkzeug
import logging

_logger = logging.getLogger(__name__)


class WebsiteSurvey(http.Controller):

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

    @website.route(['/survey/fill/<model("survey.survey"):survey>/'],
        type='http', auth='public', multilang=True)
    def fill_survey(self, survey=None, **post):
        '''Display and validates a survey'''
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']

        # In case of bad survey, redirect to surveys list
        if survey_obj.exists(cr, uid, survey.id, context=context) == []:
            return werkzeug.utils.redirect("/survey/")

        _logger.debug('Post request data: %s', post)

        # Answer validation and storage
        problems = []
        if post and int(post['current']) != -1:
            for question in survey.page_ids[int(post['current'])].question_ids:

                # validation methods are dynamically loaded, if defined for the
                # question type
                #
                # eg: if question type is 'new_question_type', this will try to
                # load validate_new_question_type

                try:
                    checker = getattr(self, 'validate_' + question.type)
                except AttributeError:
                    _logger.warning(question.type + ": This type of question has no validation method")
                else:
                    problems = problems + checker(survey.id, post['current'], question, post)

        # Return the same survey page if problems occur
        if problems:
            _logger.debug('Problems in the survey: %s', problems)
            pagination = {'current': int(post['current']), 'next': int(post['next'])}
            return request.website.render('survey.survey',
                                    {'survey': survey,
                                    'pagination': pagination,
                                    'problems': problems})

        # Display success message if totally succeeded
        if post and post['next'] == "finished":
            return request.website.render('survey.finished')

        # Page selection
        pagination = {'current': -1, 'next': 0}  # Default pagination if first opening
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
                                    'pagination': pagination,
                                    'problems': None})

    @website.route(['/survey/print/<model("survey.survey"):survey>/'],
        type='http', auth='public', multilang=True)
    def print_empty_survey(self, survey=None, **post):
        '''Display an empty survey in printable view'''
        pagination = {'current': -1, 'next': 0}
        return request.website.render('survey.survey_print',
                                    {'survey': survey,
                                    'pagination': pagination})

    def validate_free_text(self, survey_id, page_nr, question, post):
        answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
        problems = []
        if question.constr_mandatory:
            problems = problems + self.__has_empty_input(question, post, answer_tag)
        return problems

    def validate_textbox(self, survey_id, page_nr, question, post):
        answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
        problems = []
        if question.constr_mandatory:
            problems = problems + self.__has_empty_input(question, post, answer_tag)
        return problems

    def validate_numerical_box(self, survey_id, page_nr, question, post):
        answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
        # Check for an empty input
        problems = []
        if question.constr_mandatory:
            problems = problems + self.__has_empty_input(question, post, answer_tag)
        # Check for a non number input
        if answer_tag in post and post[answer_tag].strip() != "":
            try:
                float(post[answer_tag].strip())
            except ValueError:
                problems = problems + [{'qlabel': question.question,
                                    'errmsg': "This is not a number"}]

        return problems

    def validate_datetime(self, survey_id, page_nr, question, post):
        answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
        problems = []
        if question.constr_mandatory:
            problems = problems + self.__has_empty_input(question, post, answer_tag)

        # TODO CHECK, check if this is a date

        return problems

    def validate_simple_choice_scale(self, survey_id, page_nr, question, post):
        answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
        problems = []
        if question.constr_mandatory:
            problems = problems + self.__has_empty_input(question, post, answer_tag)
        return problems

    def validate_simple_choice_dropdown(self, survey_id, page_nr, question, post):
        answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
        problems = []
        if question.constr_mandatory:
            problems = problems + self.__has_empty_input(question, post, answer_tag)
        return problems

    def validate_multiple_choice(self, survey_id, page_nr, question, post):
        answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
        problems = []
        if question.constr_mandatory:
            answers = dict_keys_startswith(post, answer_tag)
            print(answers)
            if not answers:
                return [{'qlabel': question.question,
                'errmsg': "This question is mandatory"}]
        return problems

    # def validate_vector(self, survey_id, page_nr, question, post):
    #     answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
    #     problems = []
    #     return problems

    # def validate_matrix(self, survey_id, page_nr, question, post):
    #     answer_tag = survey_id.__str__() + '--' + page_nr + '--' + question.id.__str__()
    #     problems = []
    #     return problems

    def __has_empty_input(self, question, post, answer_tag):
        ''' Check for an empty input '''
        if answer_tag not in post or post[answer_tag].strip() == "":
            return [{'qlabel': question.question,
                'errmsg': "This question is mandatory"}]
        else:
            return []


def dict_keys_startswith(dictionary, string):
    '''Returns a dictionary containing the elements of <dict> whose keys start
    with <string>.

    .. note::
        This function uses dictionary comprehensions (Python >= 2.7)'''
    return {k: dictionary[k] for k in filter(lambda key: key.startswith(string), dictionary.keys())}
