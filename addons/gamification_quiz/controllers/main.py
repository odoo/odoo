# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http, _
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.exceptions import AccessError
from odoo.http import request


class GamificationQuiz(WebsiteProfile):

    # --------------------------------------------------
    # Overrides
    # --------------------------------------------------

    """
    Returns the name of the relational model between the model that holds the quiz and the partner.
    Params:
        object_model: name of the model that holds the quiz
    """
    def _get_quiz_partner_model(self, object_model):
        return ''

    def _get_object_quiz_partner_info(self, obj, quiz_done=False):
        return {}

    def _get_m2o_field_name(self, model):
        return ''

    # --------------------------------------------------
    # Utilities
    # --------------------------------------------------

    def _fetch_object(self, model, object_id):
        obj = request.env[model].browse(int(object_id)).exists()
        if not obj:
            return {'error': '%s_wrong' % (model)}
        try:
            obj.check_access_rights('read')
            obj.check_access_rule('read')
        except AccessError:
            return {'error': '%s_access' % (model)}

        return {'object': obj}

    def _get_rank_values(self, user):
        lower_bound = user.rank_id.karma_min or 0
        next_rank = user._get_next_rank()
        upper_bound = next_rank.karma_min
        progress = 100
        if next_rank and (upper_bound - lower_bound) != 0:
            progress = 100 * ((user.karma - lower_bound) / (upper_bound - lower_bound))
        return {
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'karma': user.karma,
            'motivational': next_rank.description_motivational,
            'progress': progress
        }

    # --------------------------------------------------
    # Quiz Partner Relation
    # --------------------------------------------------

    """
    Returns the relational object between the quiz and the partner
    Params:
        model: name of the model that holds the quiz
        obj: object that holds the quiz
    """
    def _get_quiz_partner_object(self, model, obj):
        quiz_partner_model = self._get_quiz_partner_model(model)
        m2o_field = self._get_m2o_field_name(model)
        partner = request.env.user.partner_id
        quiz_partner = request.env[quiz_partner_model].sudo().search([(m2o_field, '=', obj.id), ('partner_id', '=', partner.id)])
        if not quiz_partner:
            values = {
                'partner_id': partner.id,
                'quiz_attempts_count': 0,
                'quiz_completed': False,
                'points_gained': 0,
                'karma_gained': 0
            }
            values[m2o_field] = obj.id
            quiz_partner = request.env[quiz_partner_model].sudo().create(values)
        return quiz_partner

    def _get_is_completed(self, quiz_partner):
        return quiz_partner.quiz_completed

    def _set_completed(self, quiz_partner):
        if quiz_partner:
            quiz_partner.sudo().write({'completed': True, 'quiz_attempts_count': quiz_partner.quiz_attempts_count + 1})

    def _update_partner_to_object_relation(self, quiz_partner, values, reset=None):
        if reset:
            values.update({
                'quiz_attempts_count': 0,
                'quiz_completed': False,
                'points_gained': 0,
                'karma_gained': 0
            })
        quiz_partner.sudo().write(values)
        return quiz_partner

    # --------------------------------------------------
    # Quiz
    # --------------------------------------------------

    def _get_quiz_data(self, model, obj):
        quiz_partner = self._get_quiz_partner_object(model, obj)
        quiz_completed = self._get_is_completed(quiz_partner)
        values = {
            'quiz_questions': [{
                'id': question.id,
                'question': question.question,
                'answer_ids': [{
                    'id': answer.id,
                    'text_value': answer.text_value,
                    'is_correct': answer.is_correct if quiz_completed or request.website.is_publisher() else None,
                    'comment': answer.comment if request.website.is_publisher else None
                } for answer in question.sudo().answer_ids],
            } for question in obj.question_ids],
            'completed': quiz_completed
        }
        if 'quiz_answers' in request.session:
            quiz_answers = json.loads(request.session['quiz_answers'])
            if str(obj.id) in quiz_answers:
                values['session_answers'] = quiz_answers[str(obj.id)]
        values.update(self._get_object_quiz_partner_info(obj))
        return values

    # =====================================================================================
    # Routes
    # =====================================================================================

    # --------------------------------------------------
    # Quiz routes
    # --------------------------------------------------

    @http.route('/gamification_quiz/quiz/get', type="json", auth="public", website=True)
    def quiz_get(self, model, object_id):
        fetch_res = self._fetch_object(model, object_id)
        print(fetch_res)
        if fetch_res.get('error'):
            return fetch_res
        obj = fetch_res['object']
        return self._get_quiz_data(model, obj)

    def _get_quiz_answers_details(self, model, obj, answer_ids):
        m2o_field = self._get_m2o_field_name(model)

        all_questions = request.env['quiz.question'].sudo().search([(m2o_field, '=', obj.id)])

        user_answers = request.env['quiz.question.answer'].sudo().search([('id', 'in', answer_ids)])
        if user_answers.mapped('question_id') != all_questions:
            return {'error': 'quiz_incomplete'}

        user_bad_answers = user_answers.filtered(lambda answer: not answer.is_correct)
        user_good_answers = user_answers - user_bad_answers
        return {
            'user_bad_answers': user_bad_answers,
            'user_good_answers': user_good_answers,
            'user_answers': user_answers,
            'points': sum([answer.awarded_points for answer in user_good_answers])
        }

    @http.route('/gamification_quiz/quiz/submit', type="json", auth="public", website=True)
    def quiz_submit(self, model, object_id, answer_ids, karma=False):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        fetch_res = self._fetch_object(model, object_id)
        if fetch_res.get('error'):
            return fetch_res
        obj = fetch_res['object']

        quiz_partner = self._get_quiz_partner_object(model, obj)
        quiz_completed = self._get_is_completed(quiz_partner)

        if quiz_completed:
            return {'error': 'quiz_done'}

        if quiz_partner.quiz_attempts_count >= obj.quiz_max_attempts:
            return {'error': 'quiz_done'}

        answers_details = self._get_quiz_answers_details(model, obj, answer_ids)

        if quiz_partner.quiz_attempts_count == obj.quiz_max_attempts - 1:
            quiz_completed = True
            quiz_partner_update_values = {
                'quiz_attempts_count': quiz_partner.quiz_attempts_count + 1,
                'quiz_completed': quiz_partner.quiz_attempts_count == obj.quiz_max_attempts - 1,
                'points_gained': answers_details['points'],
            }
            self._update_partner_to_object_relation(quiz_partner, quiz_partner_update_values)

        quiz_info = self._get_object_quiz_partner_info(obj, quiz_done=True)

        values = {
            'answers': {
                answer.question_id.id: {
                    'is_correct': answer.is_correct,
                    'comment': answer.comment
                } for answer in answers_details['user_answers']
            },
            'quiz_completed': quiz_completed,
            'points_gained': answers_details['points'],
            'quizAttemptsCount': quiz_partner.quiz_attempts_count,
        }

        ## TODO: HANDLE KARMA MODE !!!
        ## Set amount of point for a finished quiz. The amount depends on the number of attempts
        # if karma:
        #     rank_progress = {}
        #     if not answers_details['user_bad_answers']:
        #         rank_progress['previous_rank'] = self._get_rank_values(request.env.user)
        #         self._set_object_as_completed(obj)
        #         rank_progress['new_rank'] = self._get_rank_values(request.env.user)
        #         rank_progress.update({
        #             'description': request.env.user.rank_id.description,
        #             'last_rank': not request.env.user._get_next_rank(),
        #             'level_up': rank_progress['previous_rank']['lower_bound'] != rank_progress['new_rank']['lower_bound']
        #         })
        #         values.update({
        #             'quizKarmaWon': quiz_info['quiz_karma_won'],
        #             'quizKarmaGain': quiz_info['quiz_karma_gain'],
        #             'rankProgress': rank_progress
        #         })

        return values

    @http.route('/gamification_quiz/quiz/reset', type="json", auth="user", website=True)
    def quiz_reset(self, model, object_id):
        fetch_res = self._fetch_object(model, object_id)
        if fetch_res.get('error'):
            return fetch_res
        obj = fetch_res['object']
        quiz_partner = self._get_quiz_partner_object(model, obj)
        self._update_partner_to_object_relation(quiz_partner, {}, reset=True)

    @http.route('/gamification_quiz/quiz/question_add_or_update', type='json', methods=['POST'], auth='user', website=True)
    def quiz_question_add_or_update(self, model, object_id, question, sequence, answer_ids, existing_question_id=None):
        """ Add a new question to an existing object. Completed field of the quiz-partner
        link is set to False to make sure that the creator can take the quiz again.

        An optional question_id to udpate can be given. In this case question is
        deleted first before creating a new one to simplify management.

        :param string model: Model
        :param integer object_id: Object ID
        :param string question: Question Title
        :param integer sequence: Question Sequence
        :param array answer_ids: Array containing all the answers :
                [
                    'sequence': Answer Sequence (Integer),
                    'text_value': Answer Title (String),
                    'is_correct': Answer Is Correct (Boolean)
                ]
        :param integer existing_question_id: question ID if this is an update

        :return: rendered question template
        """
        fetch_res = self._fetch_object(model, object_id)
        m2o_field = self._get_m2o_field_name(model)
        if fetch_res.get('error'):
            return fetch_res
        obj = fetch_res['object']
        if existing_question_id:
            request.env['quiz.question'].search([
                (m2o_field, '=', obj.id),
                ('id', '=', int(existing_question_id))
            ]).unlink()

        values = {'quiz_completed': False}
        self._update_partner_to_object_relation(obj, values, reset=False)

        quiz_question = request.env['quiz.question'].create({
            'sequence': sequence,
            'question': question,
            'answer_ids': [(0, 0, {
                'sequence': answer['sequence'],
                'text_value': answer['text_value'],
                'is_correct': answer['is_correct'],
                'comment': answer['comment']
            }) for answer in answer_ids]
        })
        quiz_question[m2o_field] = object_id

        return request.env.ref('gamification_quiz.quiz_question').render({
            'object': obj,
            'question': quiz_question,
        })

    # --------------------------------------------------
    # Quiz Partner routes
    # --------------------------------------------------

    @http.route('/gamification_quiz/object/set_completed', website=True, type="json", auth="public")
    def set_completed(self, model, object_id):
        if request.website.is_public_user():
            return {'error': 'public_user'}
        fetch_res = self._fetch_object(model, object_id)
        if fetch_res.get('error'):
            return fetch_res

        obj = fetch_res['object']
        quiz_partner = self._get_quiz_partner_object(model, obj)
        self._set_completed(quiz_partner)
        return quiz_partner

    # --------------------------------------------------
    # Session
    # --------------------------------------------------

    @http.route(['/gamification_quiz/quiz/save_to_session'], type='json', auth='public', website=True)
    def quiz_save_to_session(self, quiz_answers):
        session_quiz_answers = json.loads(request.session.get('quiz_answers', '{}'))
        object_id = quiz_answers['object_id']
        session_quiz_answers[str(object_id)] = quiz_answers['quiz_answers']
        request.session['quiz_answers'] = json.dumps(session_quiz_answers)
