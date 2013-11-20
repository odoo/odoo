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

import werkzeug
import json
import logging
import re

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

    # Survey displaying
    @website.route(['/survey/fill/<model("survey.survey"):survey>',
        '/survey/fill/<model("survey.survey"):survey>/<string:token>'],
        type='http', auth='public', multilang=True)
    def fill_survey(self, survey, token=None, **post):
        '''Display and validates a survey'''
        cr, uid, context = request.cr, request.uid, request.context
        survey_obj = request.registry['survey.survey']
        user_input_obj = request.registry['survey.user_input']

        # In case of bad survey, redirect to surveys list
        if survey_obj.exists(cr, uid, survey.id, context=context) == []:
            return werkzeug.utils.redirect("/survey/")

        # In case of auth required, block public user
        if survey.auth_required and uid == request.registry['website'].get_public_user(request.cr, SUPERUSER_ID, request.context).id:
            return request.website.render("website.401")

        # In case of non open surveys
        if survey.state != 'open':
                return request.website.render("survey.notopen")

        # If enough surveys completed
        if survey.user_input_limit > 0:
            completed = user_input_obj.search(cr, SUPERUSER_ID, [('state', '=', 'done')], count=True)
            if completed >= survey.user_input_limit:
                return request.website.render("survey.notopen")

        # Manual surveying
        if not token:
            if survey.visible_to_user:
                user_input_id = user_input_obj.create(cr, uid, {'survey_id': survey.id})
                user_input = user_input_obj.browse(cr, uid, [user_input_id], context=context)[0]
            else:  # An user cannot open hidden surveys without token
                return request.website.render("website.403")

        # if not auth_required and not token:
        #   create un token et un user input
        #   page = précédente + 1
        # if token:
        #   calculer la prochaine page à visiter



        _logger.debug('Incoming data: %s', post)

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
                    type='http', auth='public', multilang=True)
    def submit(self, survey, **post):
        _logger.debug('Incoming data: %s', post)
        page_nr = int(post['current'])
        questions = survey.page_ids[page_nr].question_ids

        errors = {}
        for question in questions:
            answer_tag = "%s_%s_%s" % (survey.id, page_nr, question.id)
            errors.update(self.validate_question(survey.id, page_nr, question, post, answer_tag))

        ret = {}
        if (len(errors) != 0):
            ret['errors'] = errors
        else:
            cr, uid, context = request.cr, request.uid, request.context
            # Store here data if allowed
            ret['redirect'] = "nexturl"
        return json.dumps(ret)

    # Printing routes
    @website.route(['/survey/print/<model("survey.survey"):survey>/'],
        type='http', auth='public', multilang=True)
    def print_empty_survey(self, survey=None, **post):
        '''Display an empty survey in printable view'''
        pagination = {'current': -1, 'next': 0}
        return request.website.render('survey.survey_print',
                                    {'survey': survey,
                                    'pagination': pagination})

    # Validation methods

    def validate_question(self, survey_id, page_nr, question, post, answer_tag):
        ''' Routing to the right question valider, depending on question type '''
        try:
            checker = getattr(self, 'validate_' + question.type)
        except AttributeError:
            _logger.warning(question.type + ": This type of question has no validation method")
            return {}
        else:
            return checker(survey_id, page_nr, question, post, answer_tag)

    def validate_free_text(self, survey_id, page_nr, question, post, answer_tag):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        return errors

    def validate_textbox(self, survey_id, page_nr, question, post, answer_tag):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        # Answer validation (if properly defined)
        if answer and question.validation_required and question.validation_type:
            # Length of the answer must be in a range
            if question.validation_type == "has_length":
                if not (question.validation_length_min <= len(answer) <= question.validation_length_max):
                    errors.update({answer_tag: question.validation_error_msg})

            # Answer must be an integer in a particular range
            elif question.validation_type == "is_integer":
                try:
                    intanswer = int(answer)
                # Answer is not an integer
                except ValueError:
                    errors.update({answer_tag: question.validation_error_msg})
                else:
                    # Answer is not in the right range
                    if not (question.validation_min_int_value <= intanswer <= question.validation_max_int_value):
                        errors.update({answer_tag: question.validation_error_msg})
            # Answer must be a float in a particular range
            elif question.validation_type == "is_decimal":
                try:
                    floatanswer = float(answer)
                # Answer is not an integer
                except ValueError:
                    errors.update({answer_tag: question.validation_error_msg})
                else:
                    # Answer is not in the right range
                    if not (question.validation_min_float_value <= floatanswer <= question.validation_max_float_value):
                        errors.update({answer_tag: question.validation_error_msg})

            # Answer must be a date in a particular range
            elif question.validation_type == "is_date":
                raise Exception("Not implemented")
            # Answer must be an email address
            # Note: this validation is very basic:
            #       all the strings of the form
            #       <something>@<anything>.<extension>
            #       will be accepted
            elif question.validation_type == "is_email":
                if not re.match(r"[^@]+@[^@]+\.[^@]+", answer):
                    errors.update({answer_tag: question.validation_error_msg})
            else:
                pass
        return errors

    def validate_numerical_box(self, survey_id, page_nr, question, post, answer_tag):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        # Checks if user input is a number
        if answer:
            try:
                float(answer)
            except ValueError:
                errors.update({answer_tag: question.constr_error_msg})
        return errors

    def validate_datetime(self, survey_id, page_nr, question, post, answer_tag):
        errors = {}
        answer = post[answer_tag].strip()
        # Empty answer to mandatory question
        if question.constr_mandatory and not answer:
            errors.update({answer_tag: question.constr_error_msg})
        # Checks if user input is a datetime
        # TODO when datepicker will be available
        return errors

    # def validate_simple_choice(self, survey_id, page_nr, question, post, answer_tag):
    #     answer_tag = survey_id.__str__() + '*' + page_nr + '*' + question.id.__str__()
    #     problems = []
    #     if question.constr_mandatory:
    #         problems = problems + self.__has_empty_input(question, post, answer_tag)
    #     return problems

    # def validate_multiple_choice(self, survey_id, page_nr, question, post, answer_tag):
    #     answer_tag = survey_id.__str__() + '*' + page_nr + '*' + question.id.__str__()
    #     problems = []
    #     return problems

    # def validate_matrix(self, survey_id, page_nr, question, post, answer_tag):
    #     answer_tag = survey_id.__str__() + '*' + page_nr + '*' + question.id.__str__()
    #     problems = []
    #     return problems


def dict_keys_startswith(self, dictionary, string):
    '''Returns a dictionary containing the elements of <dict> whose keys start
    with <string>.

    .. note::
        This function uses dictionary comprehensions (Python >= 2.7)'''
    return {k: dictionary[k] for k in filter(lambda key: key.startswith(string), dictionary.keys())}
