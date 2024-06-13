# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import populate

class Survey(models.Model):
    _inherit = 'survey.survey'
    _populate_sizes = {'small': 10, 'medium': 100, 'large': 1000}
    _populate_dependencies = ['res.users']

    def _populate_factories(self):
        random = populate.Random('survey_survey')
        highest_code = int(self._read_group([], [], ['session_code:max'])[0][0]) or 0
        user_ids = self.env.registry.populated_models['res.users']
        active_user_ids = self.env['res.users'].browse(user_ids).filtered(lambda u: u.active).ids  # remove inactive users to avoid validation error on survey creation
        n_survey_users_options = list(range(9))
        question_range = list(range(5, 21))
        answer_range = list(range(1, 5))

        def get_session_code(values=None, counter=None, **kwargs):
            """Assign a unique number that is greater than the largest session
            code already stored in DB"""
            return highest_code + counter + 1

        def get_question_and_page_ids(values=None, **kwargs):
            """Create random number of questions and question's answers"""
            return [
                fields.Command.create({
                    'title': f"Question {question_idx} for {values['title']}",
                    'question_type': 'multiple_choice',
                    'suggested_answer_ids': [
                        fields.Command.create({
                            'value': f"Answer {answer_idx} of question {question_idx} for {values['title']}"
                        }) for answer_idx in range(1, random.choice(answer_range) + 1)
                    ],
                })
                for question_idx in range(1, random.choice(question_range) + 1)
            ]

        def get_restrict_user_ids(values=None, **kwargs):
            """Restrict backend access of some surveys to a random number of
                users
            """
            nb_users = random.choice(n_survey_users_options)
            start_idx = random.randint(0, len(active_user_ids) - nb_users)
            return active_user_ids[start_idx: start_idx + nb_users]

        def get_user_id(values=None, **kwargs):
            """When there is restricted list of users, make sure the survey responsible is part of it"""
            return values['restrict_user_ids'][0] if values['restrict_user_ids'] else self.env.user.id

        return [
            ('title', populate.constant('Survey {counter}')),
            ('scoring_type', populate.constant('no_scoring')),
            ('session_code', populate.compute(get_session_code)),
            ('question_and_page_ids', populate.compute(get_question_and_page_ids)),
            ('restrict_user_ids', populate.compute(get_restrict_user_ids)),
            ('user_id', populate.compute(get_user_id)),
        ]
