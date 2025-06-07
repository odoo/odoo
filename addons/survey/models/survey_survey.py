# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
import uuid
from collections import defaultdict

import werkzeug

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.tools import is_html_empty


class Survey(models.Model):
    """ Settings for a multi-page/multi-question survey. Each survey can have one or more attached pages
    and each page can display one or more questions. """
    _name = 'survey.survey'
    _description = 'Survey'
    _order = 'create_date DESC'
    _rec_name = 'title'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_default_access_token(self):
        return str(uuid.uuid4())

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        # allows to propagate the text one write in a many2one widget after
        # clicking on 'Create and Edit...' to the popup form.
        if 'title' in fields_list and not result.get('title') and self.env.context.get('default_name'):
            result['title'] = self.env.context.get('default_name')
        return result

    # description
    survey_type = fields.Selection([
        ('survey', 'Survey'),
        ('live_session', 'Live session'),
        ('assessment', 'Assessment'),
        ('custom', 'Custom'),
    ],
        string='Survey Type', required=True, default='custom')
    allowed_survey_types = fields.Json(string='Allowed survey types', compute="_compute_allowed_survey_types")
    title = fields.Char('Survey Title', required=True, translate=True)
    color = fields.Integer('Color Index', default=0)
    description = fields.Html(
        "Description", translate=True, sanitize=True, sanitize_overridable=True,
        help="The description will be displayed on the home page of the survey. You can use this to give the purpose and guidelines to your candidates before they start it.")
    description_done = fields.Html(
        "End Message", translate=True,
        help="This message will be displayed when survey is completed")
    background_image = fields.Image("Background Image")
    background_image_url = fields.Char('Background Url', compute="_compute_background_image_url")
    active = fields.Boolean("Active", default=True)
    user_id = fields.Many2one(
        'res.users', string='Responsible',
        domain=[('share', '=', False)], tracking=1,
        default=lambda self: self.env.user)
    restrict_user_ids = fields.Many2many('res.users', string='Restricted to', domain=[('share', '=', False)], tracking=2)
    # questions
    question_and_page_ids = fields.One2many('survey.question', 'survey_id', string='Sections and Questions', copy=True)
    page_ids = fields.One2many('survey.question', string='Pages', compute="_compute_page_and_question_ids")
    question_ids = fields.One2many('survey.question', string='Questions', compute="_compute_page_and_question_ids")
    question_count = fields.Integer('# Questions', compute="_compute_page_and_question_ids")
    questions_layout = fields.Selection([
        ('page_per_question', 'One page per question'),
        ('page_per_section', 'One page per section'),
        ('one_page', 'One page with all the questions')],
        string="Pagination", required=True, default='page_per_question')
    questions_selection = fields.Selection([
        ('all', 'All questions'),
        ('random', 'Randomized per Section')],
        string="Question Selection", required=True, default='all',
        help="If randomized is selected, you can configure the number of random questions by section. This mode is ignored in live session.")
    progression_mode = fields.Selection([
        ('percent', 'Percentage left'),
        ('number', 'Number')], string='Display Progress as', default='percent',
        help="If Number is selected, it will display the number of questions answered on the total number of question to answer.")
    # attendees
    user_input_ids = fields.One2many('survey.user_input', 'survey_id', string='User responses', readonly=True)
    # security / access
    access_mode = fields.Selection([
        ('public', 'Anyone with the link'),
        ('token', 'Invited people only')], string='Access Mode',
        default='public', required=True)
    access_token = fields.Char('Access Token', default=lambda self: self._get_default_access_token(), copy=False)
    users_login_required = fields.Boolean('Require Login', help="If checked, users have to login before answering even with a valid token.")
    users_can_go_back = fields.Boolean('Users can go back', help="If checked, users can go back to previous pages.")
    users_can_signup = fields.Boolean('Users can signup', compute='_compute_users_can_signup')
    # statistics
    answer_count = fields.Integer("Registered", compute="_compute_survey_statistic")
    answer_done_count = fields.Integer("Attempts", compute="_compute_survey_statistic")
    answer_score_avg = fields.Float("Avg Score (%)", compute="_compute_survey_statistic")
    answer_duration_avg = fields.Float("Average Duration", compute="_compute_answer_duration_avg", help="Average duration of the survey (in hours)")
    success_count = fields.Integer("Success", compute="_compute_survey_statistic")
    success_ratio = fields.Integer("Success Ratio (%)", compute="_compute_survey_statistic")
    # scoring
    scoring_type = fields.Selection([
        ('no_scoring', 'No scoring'),
        ('scoring_with_answers_after_page', 'Scoring with answers after each page'),
        ('scoring_with_answers', 'Scoring with answers at the end'),
        ('scoring_without_answers', 'Scoring without answers')],
        string='Scoring', required=True, store=True, readonly=False, compute='_compute_scoring_type', precompute=True)
    scoring_success_min = fields.Float('Required Score (%)', default=80.0)
    scoring_max_obtainable = fields.Float('Maximum obtainable score', compute='_compute_scoring_max_obtainable')
    # attendees context: attempts and time limitation
    is_attempts_limited = fields.Boolean('Limited number of attempts', help="Check this option if you want to limit the number of attempts per user",
                                         compute="_compute_is_attempts_limited", store=True, readonly=False)
    attempts_limit = fields.Integer('Number of attempts', default=1)
    is_time_limited = fields.Boolean('The survey is limited in time')
    time_limit = fields.Float("Time limit (minutes)", default=10)
    # certification
    certification = fields.Boolean('Is a Certification', compute='_compute_certification',
                                   readonly=False, store=True, precompute=True)
    certification_mail_template_id = fields.Many2one(
        'mail.template', 'Certified Email Template',
        domain="[('model', '=', 'survey.user_input')]",
        help="Automated email sent to the user when they succeed the certification, containing their certification document.")
    certification_report_layout = fields.Selection([
        ('modern_purple', 'Modern Purple'),
        ('modern_blue', 'Modern Blue'),
        ('modern_gold', 'Modern Gold'),
        ('classic_purple', 'Classic Purple'),
        ('classic_blue', 'Classic Blue'),
        ('classic_gold', 'Classic Gold')],
        string='Certification template', default='modern_purple')
    # Certification badge
    #   certification_badge_id_dummy is used to have two different behaviours in the form view :
    #   - If the certification badge is not set, show certification_badge_id and only display create option in the m2o
    #   - If the certification badge is set, show certification_badge_id_dummy in 'no create' mode.
    #       So it can be edited but not removed or replaced.
    certification_give_badge = fields.Boolean('Give Badge', compute='_compute_certification_give_badge',
                                              readonly=False, store=True, copy=False)
    certification_badge_id = fields.Many2one('gamification.badge', 'Certification Badge', copy=False)
    certification_badge_id_dummy = fields.Many2one(related='certification_badge_id', string='Certification Badge ')
    # live sessions
    session_available = fields.Boolean('Live session available', compute='_compute_session_available')
    session_state = fields.Selection([
        ('ready', 'Ready'),
        ('in_progress', 'In Progress'),
        ], string="Session State", copy=False)
    session_code = fields.Char('Session Code', copy=False, compute="_compute_session_code",
                               precompute=True, store=True, readonly=False,
        help="This code will be used by your attendees to reach your session. Feel free to customize it however you like!")
    session_link = fields.Char('Session Link', compute='_compute_session_link')
    # live sessions - current question fields
    session_question_id = fields.Many2one('survey.question', string="Current Question", copy=False,
        help="The current question of the survey session.")
    session_start_time = fields.Datetime("Current Session Start Time", copy=False)
    session_question_start_time = fields.Datetime("Current Question Start Time", copy=False,
        help="The time at which the current question has started, used to handle the timer for attendees.")
    session_answer_count = fields.Integer("Answers Count", compute='_compute_session_answer_count')
    session_question_answer_count = fields.Integer("Question Answers Count", compute='_compute_session_question_answer_count')
    # live sessions - settings
    session_show_leaderboard = fields.Boolean("Show Session Leaderboard", compute='_compute_session_show_leaderboard',
        help="Whether or not we want to show the attendees leaderboard for this survey.")
    session_speed_rating = fields.Boolean("Reward quick answers", help="Attendees get more points if they answer quickly")
    session_speed_rating_time_limit = fields.Integer(
        "Time limit (seconds)", help="Default time given to receive additional points for right answers")
    # conditional questions management
    has_conditional_questions = fields.Boolean("Contains conditional questions", compute="_compute_has_conditional_questions")

    _sql_constraints = [
        ('access_token_unique', 'unique(access_token)', 'Access token should be unique'),
        ('session_code_unique', 'unique(session_code)', 'Session code should be unique'),
        ('certification_check', "CHECK( scoring_type!='no_scoring' OR certification=False )",
            'You can only create certifications for surveys that have a scoring mechanism.'),
        ('scoring_success_min_check', "CHECK( scoring_success_min IS NULL OR (scoring_success_min>=0 AND scoring_success_min<=100) )",
            'The percentage of success has to be defined between 0 and 100.'),
        ('time_limit_check', "CHECK( (is_time_limited=False) OR (time_limit is not null AND time_limit > 0) )",
            'The time limit needs to be a positive number if the survey is time limited.'),
        ('attempts_limit_check', "CHECK( (is_attempts_limited=False) OR (attempts_limit is not null AND attempts_limit > 0) )",
            'The attempts limit needs to be a positive number if the survey has a limited number of attempts.'),
        ('badge_uniq', 'unique (certification_badge_id)', "The badge for each survey should be unique!"),
        ('session_speed_rating_has_time_limit',
         "CHECK (session_speed_rating != TRUE OR session_speed_rating_time_limit IS NOT NULL AND session_speed_rating_time_limit > 0)",
         'A positive default time limit is required when the session rewards quick answers.'),
    ]

    @api.depends('background_image', 'access_token')
    def _compute_background_image_url(self):
        self.background_image_url = False
        for survey in self.filtered(lambda s: s.background_image and s.access_token):
            survey.background_image_url = "/survey/%s/get_background_image" % survey.access_token

    @api.depends(
        'question_and_page_ids',
        'question_and_page_ids.suggested_answer_ids',
        'question_and_page_ids.suggested_answer_ids.answer_score',
    )
    def _compute_scoring_max_obtainable(self):
        for survey in self:
            survey.scoring_max_obtainable = sum(
                question.answer_score
                or sum(answer.answer_score for answer in question.suggested_answer_ids if answer.answer_score > 0)
                for question in survey.question_ids
            )

    def _compute_users_can_signup(self):
        signup_allowed = self.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'
        for survey in self:
            survey.users_can_signup = signup_allowed

    @api.depends('user_input_ids.state', 'user_input_ids.test_entry', 'user_input_ids.scoring_percentage', 'user_input_ids.scoring_success')
    def _compute_survey_statistic(self):
        default_vals = {
            'answer_count': 0, 'answer_done_count': 0, 'success_count': 0,
            'answer_score_avg': 0.0, 'success_ratio': 0.0
        }
        stat = dict((cid, dict(default_vals, answer_score_avg_total=0.0)) for cid in self.ids)
        UserInput = self.env['survey.user_input']
        base_domain = [('survey_id', 'in', self.ids)]

        read_group_res = UserInput._read_group(base_domain, ['survey_id', 'state', 'scoring_percentage', 'scoring_success'], ['__count'])
        for survey, state, scoring_percentage, scoring_success, count in read_group_res:
            stat[survey.id]['answer_count'] += count
            stat[survey.id]['answer_score_avg_total'] += scoring_percentage
            if state == 'done':
                stat[survey.id]['answer_done_count'] += count
            if scoring_success:
                stat[survey.id]['success_count'] += count

        for survey_stats in stat.values():
            avg_total = survey_stats.pop('answer_score_avg_total')
            survey_stats['answer_score_avg'] = avg_total / (survey_stats['answer_count'] or 1)
            survey_stats['success_ratio'] = (survey_stats['success_count'] / (survey_stats['answer_count'] or 1.0))*100

        for survey in self:
            survey.update(stat.get(survey._origin.id, default_vals))

    @api.depends('user_input_ids.survey_id', 'user_input_ids.start_datetime', 'user_input_ids.end_datetime')
    def _compute_answer_duration_avg(self):
        result_per_survey_id = {}
        if self.ids:
            self.env.cr.execute(
                """SELECT survey_id,
                          avg((extract(epoch FROM end_datetime)) - (extract (epoch FROM start_datetime)))
                     FROM survey_user_input
                    WHERE survey_id = any(%s) AND state = 'done'
                          AND end_datetime IS NOT NULL
                          AND start_datetime IS NOT NULL
                 GROUP BY survey_id""",
                [self.ids]
            )
            result_per_survey_id = dict(self.env.cr.fetchall())

        for survey in self:
            # as avg returns None if nothing found, set 0 if it's the case.
            survey.answer_duration_avg = (result_per_survey_id.get(survey.id) or 0) / 3600

    @api.depends('question_and_page_ids')
    def _compute_page_and_question_ids(self):
        for survey in self:
            survey.page_ids = survey.question_and_page_ids.filtered(lambda question: question.is_page)
            survey.question_ids = survey.question_and_page_ids - survey.page_ids
            survey.question_count = len(survey.question_ids)

    @api.depends('question_and_page_ids.triggering_answer_ids', 'users_login_required', 'access_mode')
    def _compute_is_attempts_limited(self):
        for survey in self:
            if not survey.is_attempts_limited or \
               (survey.access_mode == 'public' and not survey.users_login_required) or \
               any(question.triggering_answer_ids for question in survey.question_and_page_ids):
                survey.is_attempts_limited = False

    @api.depends('session_start_time', 'user_input_ids')
    def _compute_session_answer_count(self):
        """ We have to loop since our result is dependent of the survey.session_start_time.
        This field is currently used to display the count about a single survey, in the
        context of sessions, so it should not matter too much. """

        for survey in self:
            [answer_count] = self.env['survey.user_input']._read_group(
                [('survey_id', '=', survey.id),
                 ('is_session_answer', '=', True),
                 ('state', '!=', 'done'),
                 ('create_date', '>=', survey.session_start_time)],
                aggregates=['create_uid:count'],
            )[0]
            survey.session_answer_count = answer_count

    @api.depends('session_question_id', 'session_start_time', 'user_input_ids.user_input_line_ids')
    def _compute_session_question_answer_count(self):
        """ We have to loop since our result is dependent of the survey.session_question_id and
        the survey.session_start_time.
        This field is currently used to display the count about a single survey, in the
        context of sessions, so it should not matter too much. """
        for survey in self:
            [answer_count] = self.env['survey.user_input.line']._read_group(
                [('question_id', '=', survey.session_question_id.id),
                 ('survey_id', '=', survey.id),
                 ('create_date', '>=', survey.session_start_time)],
                aggregates=['user_input_id:count_distinct'],
            )[0]
            survey.session_question_answer_count = answer_count

    @api.depends('access_token')
    def _compute_session_code(self):
        survey_without_session_code = self.filtered(lambda survey: not survey.session_code)
        session_codes = self._generate_session_codes(
            code_count=len(survey_without_session_code),
            excluded_codes=set((self - survey_without_session_code).mapped('session_code'))
        )
        for survey, session_code in zip(survey_without_session_code, session_codes):
            survey.session_code = session_code

    @api.depends('session_code')
    def _compute_session_link(self):
        for survey in self:
            if survey.session_code:
                survey.session_link = werkzeug.urls.url_join(
                    survey.get_base_url(),
                    '/s/%s' % survey.session_code)
            else:
                survey.session_link = werkzeug.urls.url_join(
                    survey.get_base_url(),
                    survey.get_start_url())

    @api.depends('scoring_type', 'question_and_page_ids.save_as_nickname')
    def _compute_session_show_leaderboard(self):
        for survey in self:
            survey.session_show_leaderboard = survey.scoring_type != 'no_scoring' and \
                any(question.save_as_nickname for question in survey.question_and_page_ids)

    @api.depends('question_and_page_ids.triggering_answer_ids')
    def _compute_has_conditional_questions(self):
        for survey in self:
            survey.has_conditional_questions = any(question.triggering_answer_ids for question in survey.question_and_page_ids)

    @api.depends('scoring_type')
    def _compute_certification(self):
        for survey in self:
            if not survey.certification or survey.scoring_type == 'no_scoring':
                survey.certification = False

    @api.depends('users_login_required', 'certification')
    def _compute_certification_give_badge(self):
        for survey in self:
            if not survey.certification_give_badge or \
               not survey.users_login_required or \
               not survey.certification:
                survey.certification_give_badge = False

    @api.depends('certification')
    def _compute_scoring_type(self):
        for survey in self:
            if survey.certification and survey.scoring_type in {False, 'no_scoring'}:
                survey.scoring_type = 'scoring_without_answers'
            elif not survey.scoring_type:
                survey.scoring_type = 'no_scoring'

    @api.depends('survey_type', 'certification')
    def _compute_session_available(self):
        for survey in self:
            survey.session_available = survey.survey_type in {'live_session', 'custom'} and not survey.certification

    @api.depends_context('uid')
    def _compute_allowed_survey_types(self):
        self.allowed_survey_types = [
            'survey',
            'live_session',
            'assessment',
            'custom',
        ] if self.env.user.has_group('survey.group_survey_user') else False

    @api.onchange('survey_type')
    def _onchange_survey_type(self):
        if self.survey_type == 'survey':
            self.write({
                'certification': False,
                'is_time_limited': False,
                'scoring_type': 'no_scoring',
            })
        elif self.survey_type == 'live_session':
            self.write({
                'access_mode': 'public',
                'is_attempts_limited': False,
                'is_time_limited': False,
                'progression_mode': 'percent',
                'questions_layout': 'page_per_question',
                'questions_selection': 'all',
                'scoring_type': 'scoring_with_answers',
                'users_can_go_back': False,
            })
        elif self.survey_type == 'assessment':
            self.write({
                'access_mode': 'token',
                'scoring_type': 'scoring_with_answers',
            })

    @api.onchange('session_speed_rating', 'session_speed_rating_time_limit')
    def _onchange_session_speed_rating(self):
        """Show impact on questions in the form view (before survey is saved)."""
        for survey in self.filtered('question_ids'):
            survey.question_ids._update_time_limit_from_survey(
                is_time_limited=survey.session_speed_rating, time_limit=survey.session_speed_rating_time_limit)

    @api.onchange('restrict_user_ids', 'user_id')
    def _onchange_restrict_user_ids(self):
        """
         Add survey user_id to restrict_user_ids when:
         - restrict_user_ids is not False
         - user_id is not part of restrict_user_ids
         - user_id is not a survey manager
        """
        surveys_to_check = self.filtered(lambda s: s.restrict_user_ids and bool(s.user_id - s.restrict_user_ids))
        users_are_managers = surveys_to_check.user_id.filtered(lambda user: user.has_group('survey.group_survey_manager'))
        for survey in surveys_to_check.filtered(lambda s: s.user_id not in users_are_managers):
            survey.restrict_user_ids += survey.user_id

    @api.constrains('scoring_type', 'users_can_go_back')
    def _check_scoring_after_page_availability(self):
        failing = self.filtered(lambda survey: survey.scoring_type == 'scoring_with_answers_after_page' and survey.users_can_go_back)
        if failing:
            raise ValidationError(
                _('Combining roaming and "Scoring with answers after each page" is not possible; please update the following surveys:\n- %(survey_names)s',
                  survey_names="\n- ".join(failing.mapped('title')))
            )

    @api.constrains('user_id', 'restrict_user_ids')
    def _check_survey_responsible_access(self):
        """ When:
                - a survey access is restricted to a list of users
                - and there is a survey responsible,
                - and this responsible is not survey manager (just survey officer),
            check the responsible is part of the list."""
        surveys_to_check = self.filtered(lambda s: bool(s.user_id - s.restrict_user_ids))
        if surveys_to_check:
            valid_surveys = surveys_to_check._filtered_access("write")
            failing_surveys_sudo = (self - valid_surveys).sudo()
            if failing_surveys_sudo:
                raise ValidationError(
                    _('The access of the following surveys is restricted. Make sure their responsible still has access to it: \n%(survey_names)s\n',
                        survey_names='\n'.join(f'- {survey.title}: {survey.user_id.name}' for survey in failing_surveys_sudo)))

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        surveys = super(Survey, self).create(vals_list)
        for survey_sudo in surveys.filtered(lambda survey: survey.certification_give_badge).sudo():
            survey_sudo._create_certification_badge_trigger()
        return surveys

    def write(self, vals):
        speed_rating, speed_limit = vals.get('session_speed_rating'), vals.get('session_speed_rating_time_limit')

        surveys_to_update = self.filtered(lambda s: (
            speed_rating is not None and s.session_speed_rating != speed_rating
            or speed_limit is not None and s.session_speed_rating_time_limit != speed_limit
        ))

        result = super(Survey, self).write(vals)
        if 'certification_give_badge' in vals:
            return self.sudo()._handle_certification_badges(vals)

        if questions_to_update := surveys_to_update.question_ids:
            questions_to_update._update_time_limit_from_survey(is_time_limited=speed_rating, time_limit=speed_limit)

        return result

    def copy(self, default=None):
        """Correctly copy the 'triggering_answer_ids' field from the original to the clone.

        This needs to be done in post-processing to make sure we get references to the newly
        created answers from the copy instead of references to the answers of the original.
        This implementation assumes that the order of created answers will be kept between
        the original and the clone, using 'zip()' to match the records between the two.

        Note that when `question_ids` is provided in the default parameter, it falls back to the
        standard copy, meaning that triggering logic will not be maintained.
        """
        new_surveys = super().copy(default)
        if default and 'question_ids' in default:
            return new_surveys

        for old_survey, new_survey in zip(self, new_surveys):
            cloned_question_ids = new_survey.question_ids.sorted()

            answers_map = {
                src_answer.id: dst_answer.id
                for src, dst
                in zip(old_survey.question_ids, cloned_question_ids)
                for src_answer, dst_answer
                in zip(src.suggested_answer_ids, dst.suggested_answer_ids.sorted())
            }
            for src, dst in zip(old_survey.question_ids, cloned_question_ids):
                if src.triggering_answer_ids:
                    dst.triggering_answer_ids = [answers_map[src_answer_id.id] for src_answer_id in src.triggering_answer_ids]
        return new_surveys

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, title=self.env._("%s (copy)", survey.title)) for survey, vals in zip(self, vals_list)]

    def toggle_active(self):
        super(Survey, self).toggle_active()
        activated = self.filtered(lambda survey: survey.active)
        activated.certification_badge_id.action_unarchive()
        (self - activated).certification_badge_id.action_archive()

    # ------------------------------------------------------------
    # ANSWER MANAGEMENT
    # ------------------------------------------------------------

    def _create_answer(self, user=False, partner=False, email=False, test_entry=False, check_attempts=True, **additional_vals):
        """ Main entry point to get a token back or create a new one. This method
        does check for current user access in order to explicitly validate security.

          :param user: target user asking for a token; it might be void or a
                       public user in which case an email is welcomed;
          :param email: email of the person asking the token is no user exists;
        """
        self.check_access('read')

        user_inputs = self.env['survey.user_input']
        for survey in self:
            if partner and not user and partner.user_ids:
                user = partner.user_ids[0]

            invite_token = additional_vals.pop('invite_token', False)
            survey._check_answer_creation(user, partner, email, test_entry=test_entry, check_attempts=check_attempts, invite_token=invite_token)
            answer_vals = {
                'survey_id': survey.id,
                'test_entry': test_entry,
                'is_session_answer': survey.session_state in ['ready', 'in_progress']
            }
            if survey.session_state == 'in_progress':
                # if the session is already in progress, the answer skips the 'new' state
                answer_vals.update({
                    'state': 'in_progress',
                    'start_datetime': fields.Datetime.now(),
                })
            if user and not user._is_public():
                answer_vals['partner_id'] = user.partner_id.id
                answer_vals['email'] = user.email
                answer_vals['nickname'] = user.name
            elif partner:
                answer_vals['partner_id'] = partner.id
                answer_vals['email'] = partner.email
                answer_vals['nickname'] = partner.name
            else:
                answer_vals['email'] = email
                answer_vals['nickname'] = email

            if invite_token:
                answer_vals['invite_token'] = invite_token
            elif survey.is_attempts_limited and survey.access_mode != 'public':
                # attempts limited: create a new invite_token
                # exception made for 'public' access_mode since the attempts pool is global because answers are
                # created every time the user lands on '/start'
                answer_vals['invite_token'] = self.env['survey.user_input']._generate_invite_token()

            answer_vals.update(additional_vals)
            user_inputs += user_inputs.create(answer_vals)

        for question in self.mapped('question_ids').filtered(
                lambda q: q.question_type == 'char_box' and (q.save_as_email or q.save_as_nickname)):
            for user_input in user_inputs:
                if question.save_as_email and user_input.email:
                    user_input._save_lines(question, user_input.email)
                if question.save_as_nickname and user_input.nickname:
                    user_input._save_lines(question, user_input.nickname)

        return user_inputs

    def _check_answer_creation(self, user, partner, email, test_entry=False, check_attempts=True, invite_token=False):
        """ Ensure conditions to create new tokens are met. """
        self.ensure_one()
        if test_entry:
            try:
                self.with_user(user).check_access('read')
            except AccessError:
                raise exceptions.UserError(_('Creating test token is not allowed for you.'))

        if not test_entry:
            if not self.active:
                raise exceptions.UserError(_('Creating token for closed/archived surveys is not allowed.'))
            if self.access_mode == 'authentication':
                # signup possible -> should have at least a partner to create an account
                if self.users_can_signup and not user and not partner:
                    raise exceptions.UserError(_('Creating token for external people is not allowed for surveys requesting authentication.'))
                # no signup possible -> should be a not public user (employee or portal users)
                if not self.users_can_signup and (not user or user._is_public()):
                    raise exceptions.UserError(_('Creating token for external people is not allowed for surveys requesting authentication.'))
            if self.access_mode == 'internal' and (not user or not user._is_internal()):
                raise exceptions.UserError(_('Creating token for anybody else than employees is not allowed for internal surveys.'))
            if check_attempts and not self._has_attempts_left(partner or (user and user.partner_id), email, invite_token):
                raise exceptions.UserError(_('No attempts left.'))

    def _prepare_user_input_predefined_questions(self):
        """ Will generate the questions for a randomized survey.
        It uses the random_questions_count of every sections of the survey to
        pick a random number of questions and returns the merged recordset """
        self.ensure_one()

        questions = self.env['survey.question']

        # First append questions without page
        for question in self.question_ids:
            if not question.page_id:
                questions |= question

        # Then, questions in sections

        for page in self.page_ids:
            if self.questions_selection == 'all':
                questions |= page.question_ids
            else:
                if 0 < page.random_questions_count < len(page.question_ids):
                    questions = questions.concat(*random.sample(page.question_ids, page.random_questions_count))
                else:
                    questions |= page.question_ids

        return questions

    def _can_go_back(self, answer, page_or_question):
        """ Check if the user can go back to the previous question/page for the currently
        viewed question/page.
        Back button needs to be configured on survey and, depending on the layout:
        - In 'page_per_section', we can go back if we're not on the first page
        - In 'page_per_question', we can go back if:
          - It is not a session answer (doesn't make sense to go back in session context)
          - We are not on the first question
          - The survey does not have pages OR this is not the first page of the survey
            (pages are displayed in 'page_per_question' layout when they have a description, see PR#44271)
        """
        self.ensure_one()
        if self.questions_layout == "one_page" or not self.users_can_go_back:
            return False
        if answer.state != 'in_progress' or answer.is_session_answer:
            return False
        if self.page_ids and page_or_question == self.page_ids[0]:
            return False
        return self.questions_layout == 'page_per_section' or page_or_question != answer.predefined_question_ids[0]

    def _has_attempts_left(self, partner, email, invite_token):
        self.ensure_one()

        if (self.access_mode != 'public' or self.users_login_required) and self.is_attempts_limited:
            return self._get_number_of_attempts_lefts(partner, email, invite_token) > 0

        return True

    def _get_number_of_attempts_lefts(self, partner, email, invite_token):
        """ Returns the number of attempts left. """
        self.ensure_one()

        domain = [
            ('survey_id', '=', self.id),
            ('test_entry', '=', False),
            ('state', '=', 'done')
        ]

        if partner:
            domain = expression.AND([domain, [('partner_id', '=', partner.id)]])
        else:
            domain = expression.AND([domain, [('email', '=', email)]])

        if invite_token:
            domain = expression.AND([domain, [('invite_token', '=', invite_token)]])

        return self.attempts_limit - self.env['survey.user_input'].search_count(domain)

    # ------------------------------------------------------------
    # QUESTIONS MANAGEMENT
    # ------------------------------------------------------------

    @api.model
    def _get_pages_or_questions(self, user_input):
        """ Returns the pages or questions (depending on the layout) that will be shown
        to the user taking the survey.
        In 'page_per_question' layout, we also want to show pages that have a description. """

        result = self.env['survey.question']
        if self.questions_layout == 'page_per_section':
            result = self.page_ids
        elif self.questions_layout == 'page_per_question':
            if self.questions_selection == 'random' and not self.session_state:
                result = user_input.predefined_question_ids
            else:
                result = self._get_pages_and_questions_to_show()

        return result

    def _get_pages_and_questions_to_show(self):
        """Filter question_and_pages_ids to include only valid pages and questions.

        Pages are invalid if they have no description. Questions are invalid if
        they are conditional and all their triggers are invalid.
        Triggers are invalid if they:
          - Are a page (not a question)
          - Have the wrong question type (`simple_choice` and `multiple_choice` are supported)
          - Are misplaced (positioned after the conditional question)
          - They are themselves conditional and were found invalid
        """
        self.ensure_one()
        invalid_questions = self.env['survey.question']
        questions_and_valid_pages = self.question_and_page_ids.filtered(
            lambda question: not question.is_page or not is_html_empty(question.description))

        for question in questions_and_valid_pages.filtered('triggering_answer_ids').sorted():
            for trigger in question.triggering_question_ids:
                if (trigger not in invalid_questions
                        and not trigger.is_page
                        and trigger.question_type in ['simple_choice', 'multiple_choice']
                        and (trigger.sequence < question.sequence
                             or (trigger.sequence == question.sequence and trigger.id < question.id))):
                    break
            else:
                # No valid trigger found
                invalid_questions |= question
        return questions_and_valid_pages - invalid_questions

    def _get_next_page_or_question(self, user_input, page_or_question_id, go_back=False):
        """ Generalized logic to retrieve the next question or page to show on the survey.
        It's based on the page_or_question_id parameter, that is usually the currently displayed question/page.

        There is a special case when the survey is configured with conditional questions:
        - for "page_per_question" layout, the next question to display depends on the selected answers and
          the questions 'hierarchy'.
        - for "page_per_section" layout, before returning the result, we check that it contains at least a question
          (all section questions could be disabled based on previously selected answers)

        The whole logic is inverted if "go_back" is passed as True.

        As pages with description are considered as potential question to display, we show the page
        if it contains at least one active question or a description.

        :param user_input: user's answers
        :param page_or_question_id: current page or question id
        :param go_back: reverse the logic and get the PREVIOUS question/page
        :return: next or previous question/page
        """

        survey = user_input.survey_id
        pages_or_questions = survey._get_pages_or_questions(user_input)
        Question = self.env['survey.question']

        # Get Next
        if not go_back:
            if not pages_or_questions:
                return Question
            # First page
            if page_or_question_id == 0:
                return pages_or_questions[0]

        current_page_index = pages_or_questions.ids.index(page_or_question_id)

        # Get previous and we are on first page  OR Get Next and we are on last page
        if (go_back and current_page_index == 0) or (not go_back and current_page_index == len(pages_or_questions) - 1):
            return Question

        # Conditional Questions Management
        triggering_answers_by_question, _, selected_answers = user_input._get_conditional_values()
        inactive_questions = user_input._get_inactive_conditional_questions()
        if survey.questions_layout == 'page_per_question':
            question_candidates = pages_or_questions[0:current_page_index] if go_back \
                else pages_or_questions[current_page_index + 1:]
            for question in question_candidates.sorted(reverse=go_back):
                # pages with description are potential questions to display (are part of question_candidates)
                if question.is_page:
                    contains_active_question = any(sub_question not in inactive_questions for sub_question in question.question_ids)
                    is_description_section = not question.question_ids and not is_html_empty(question.description)
                    if contains_active_question or is_description_section:
                        return question
                else:
                    triggering_answers = triggering_answers_by_question.get(question)
                    if not triggering_answers or triggering_answers & selected_answers:
                        # question is visible because not conditioned or conditioned by a selected answer
                        return question
        elif survey.questions_layout == 'page_per_section':
            section_candidates = pages_or_questions[0:current_page_index] if go_back \
                else pages_or_questions[current_page_index + 1:]
            for section in section_candidates.sorted(reverse=go_back):
                contains_active_question = any(question not in inactive_questions for question in section.question_ids)
                is_description_section = not section.question_ids and not is_html_empty(section.description)
                if contains_active_question or is_description_section:
                    return section
            return Question

    def _is_first_page_or_question(self, page_or_question):
        """ This method checks if the given question or page is the first one to display.
            If the first section of the survey as a description, this will be the first screen to display.
            else, the first question will be the first screen to be displayed.
            This method is used for survey session management where the host should not be able to go back on the
            first page or question."""
        first_section_has_description = self.page_ids and not is_html_empty(self.page_ids[0].description)
        is_first_page_or_question = (first_section_has_description and page_or_question == self.page_ids[0]) or \
            (not first_section_has_description and page_or_question == self.question_ids[0])
        return is_first_page_or_question

    def _is_last_page_or_question(self, user_input, page_or_question):
        """ Check if the given question or page is the last one, accounting for conditional questions.

        A question/page will be determined as the last one if any of the following is true:
          - The survey layout is "one_page",
          - There are no more questions/page after `page_or_question` in `user_input`,
          - All the following questions are conditional AND were not triggered by previous answers,
            AND cannot be triggered by any answer given on the current page/question.
        """
        if self.questions_layout == "one_page":
            return True
        pages_or_questions = self._get_pages_or_questions(user_input)
        current_page_index = pages_or_questions.ids.index(page_or_question.id)
        next_page_or_question_candidates = pages_or_questions[current_page_index + 1:]
        if not next_page_or_question_candidates:
            return True
        inactive_questions = user_input._get_inactive_conditional_questions()
        __, triggered_questions_by_answer, __ = user_input._get_conditional_values()
        if self.questions_layout == 'page_per_question':
            return not (
                any(next_question not in inactive_questions for next_question in next_page_or_question_candidates)
                or any(answer in triggered_questions_by_answer for answer in page_or_question.suggested_answer_ids)
            )
        elif self.questions_layout == 'page_per_section':
            for question in page_or_question.question_ids:
                if any(answer in triggered_questions_by_answer for answer in question.suggested_answer_ids):
                    return False
            for section in next_page_or_question_candidates:
                if any(next_question not in inactive_questions for next_question in section.question_ids):
                    return False
        return True

    def _get_survey_questions(self, answer=None, page_id=None, question_id=None):
        """ Returns a tuple containing: the survey question and the passed question_id / page_id
        based on the question_layout and the fact that it's a session or not.

        Breakdown of use cases:
        - We are currently running a session
          We return the current session question and it's id
        - The layout is page_per_section
          We return the questions for that page and the passed page_id
        - The layout is page_per_question
          We return the question for the passed question_id and the question_id
        - The layout is one_page
          We return all the questions of the survey and None

        In addition, we cross the returned questions with the answer.predefined_question_ids,
        that allows to handle the randomization of questions. """
        if answer and answer.is_session_answer:
            return self.session_question_id, self.session_question_id.id
        if self.questions_layout == 'page_per_section':
            if not page_id:
                raise ValueError("Page id is needed for question layout 'page_per_section'")
            page_or_question_id = int(page_id)
            questions = self.env['survey.question'].sudo().search(
                expression.AND([[('survey_id', '=', self.id)], [('page_id', '=', page_or_question_id)]]))
        elif self.questions_layout == 'page_per_question':
            if not question_id:
                raise ValueError("Question id is needed for question layout 'page_per_question'")
            page_or_question_id = int(question_id)
            questions = self.env['survey.question'].sudo().browse(page_or_question_id)
        else:
            page_or_question_id = None
            questions = self.question_ids

        # we need the intersection of the questions of this page AND the questions prepared for that user_input
        # (because randomized surveys do not use all the questions of every page)
        if answer:
            questions = questions & answer.predefined_question_ids
        return questions, page_or_question_id

    # ------------------------------------------------------------
    # CONDITIONAL QUESTIONS MANAGEMENT
    # ------------------------------------------------------------

    def _get_conditional_maps(self):
        triggering_answers_by_question = defaultdict(lambda: self.env['survey.question.answer'])
        triggered_questions_by_answer = defaultdict(lambda: self.env['survey.question'])
        for question in self.question_ids:
            triggering_answers_by_question[question] |= question.triggering_answer_ids

            for triggering_answer_id in question.triggering_answer_ids:
                triggered_questions_by_answer[triggering_answer_id] |= question

        return triggering_answers_by_question, triggered_questions_by_answer

    # ------------------------------------------------------------
    # SESSIONS MANAGEMENT
    # ------------------------------------------------------------

    def _session_open(self):
        """ The session start is sudo'ed to allow survey user to manage sessions of surveys
        they do not own.

        We flush after writing to make sure it's updated before bus takes over. """

        if self.env.user.has_group('survey.group_survey_user'):
            self.sudo().write({'session_state': 'in_progress'})
            self.sudo().flush_recordset(['session_state'])

    def _get_session_next_question(self, go_back):
        self.ensure_one()

        if not self.question_ids or not self.env.user.has_group('survey.group_survey_user'):
            return

        most_voted_answers = self._get_session_most_voted_answers()
        return self._get_next_page_or_question(
            most_voted_answers,
            self.session_question_id.id if self.session_question_id else 0, go_back=go_back)

    def _get_session_most_voted_answers(self):
        """ In sessions of survey that has conditional questions, as the survey is passed at the same time by
        many users, we need to extract the most chosen answers, to determine the next questions to display. """

        # get user_inputs from current session
        current_user_inputs = self.user_input_ids.filtered(lambda ui: ui.create_date > self.session_start_time)
        current_user_input_lines = current_user_inputs.user_input_line_ids.filtered('suggested_answer_id')

        # count the number of vote per answer
        votes_by_answer = dict.fromkeys(current_user_input_lines.mapped('suggested_answer_id'), 0)
        for answer in current_user_input_lines:
            votes_by_answer[answer.suggested_answer_id] += 1

        # extract most voted answer for each question
        most_voted_answer_by_questions = dict.fromkeys(current_user_input_lines.mapped('question_id'))
        for question in most_voted_answer_by_questions.keys():
            for answer in votes_by_answer.keys():
                if answer.question_id != question:
                    continue
                most_voted_answer = most_voted_answer_by_questions[question]
                if not most_voted_answer or votes_by_answer[most_voted_answer] < votes_by_answer[answer]:
                    most_voted_answer_by_questions[question] = answer

        # return a fake 'audience' user_input
        fake_user_input = self.env['survey.user_input'].new({
            'survey_id': self.id,
            'predefined_question_ids': [(6, 0, self._prepare_user_input_predefined_questions().ids)]
        })

        fake_user_input_lines = self.env['survey.user_input.line']
        for question, answer in most_voted_answer_by_questions.items():
            fake_user_input_lines |= self.env['survey.user_input.line'].new({
                'question_id': question.id,
                'suggested_answer_id': answer.id,
                'survey_id': self.id,
                'user_input_id': fake_user_input.id
            })

        return fake_user_input

    def _prepare_leaderboard_values(self):
        """ The leaderboard is descending and takes the total of the attendee points minus the
        current question score.
        We need both the total and the current question points to be able to show the attendees
        leaderboard and shift their position based on the score they have on the current question.
        This prepares a structure containing all the necessary data for the animations done on
        the frontend side.
        The leaderboard is sorted based on attendees score *before* the current question.
        The frontend will shift positions around accordingly. """

        self.ensure_one()

        leaderboard = self.env['survey.user_input'].search_read([
            ('survey_id', '=', self.id),
            ('create_date', '>=', self.session_start_time)
        ], [
            'id',
            'nickname',
            'scoring_total',
        ], limit=15, order="scoring_total desc")

        if leaderboard and self.session_state == 'in_progress' and \
           any(answer.answer_score for answer in self.session_question_id.suggested_answer_ids):
            question_scores = {}
            input_lines = self.env['survey.user_input.line'].search_read(
                    [('user_input_id', 'in', [score['id'] for score in leaderboard]),
                        ('question_id', '=', self.session_question_id.id)],
                    ['user_input_id', 'answer_score'])
            for input_line in input_lines:
                question_scores[input_line['user_input_id'][0]] = \
                    question_scores.get(input_line['user_input_id'][0], 0) + input_line['answer_score']

            score_position = 0
            for leaderboard_item in leaderboard:
                question_score = question_scores.get(leaderboard_item['id'], 0)
                leaderboard_item.update({
                    'updated_score': leaderboard_item['scoring_total'],
                    'scoring_total': leaderboard_item['scoring_total'] - question_score,
                    'leaderboard_position': score_position,
                    'max_question_score': sum(
                        score for score in self.session_question_id.suggested_answer_ids.mapped('answer_score')
                        if score > 0
                    ) or 1,
                    'question_score': question_score
                })
                score_position += 1
            leaderboard = sorted(
                leaderboard,
                key=lambda score: score['scoring_total'],
                reverse=True)

        return leaderboard

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def check_validity(self):
        # Ensure that this survey has at least one question.
        if not self.question_ids:
            raise UserError(_('You cannot send an invitation for a survey that has no questions.'))

        # Ensure scored survey have a positive total score obtainable.
        if self.scoring_type != 'no_scoring' and self.scoring_max_obtainable <= 0:
            raise UserError(_("A scored survey needs at least one question that gives points.\n"
                              "Please check answers and their scores."))

        # Ensure that this survey has at least one section with question(s), if question layout is 'One page per section'.
        if self.questions_layout == 'page_per_section':
            if not self.page_ids:
                raise UserError(_('You cannot send an invitation for a "One page per section" survey if the survey has no sections.'))
            if not self.page_ids.mapped('question_ids'):
                raise UserError(_('You cannot send an invitation for a "One page per section" survey if the survey only contains empty sections.'))

        if not self.active:
            raise exceptions.UserError(_("You cannot send invitations for closed surveys."))

    def action_send_survey(self):
        """ Open a window to compose an email, pre-filled with the survey message """
        self.check_validity()

        template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)

        local_context = dict(
            self.env.context,
            default_survey_id=self.id,
            default_template_id=template and template.id or False,
            default_email_layout_xmlid='mail.mail_notification_light',
            default_send_email=(self.access_mode != 'public'),
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _("Share a Survey"),
            'view_mode': 'form',
            'res_model': 'survey.invite',
            'target': 'new',
            'context': local_context,
        }

    def action_start_survey(self, answer=None):
        """ Open the website page with the survey form """
        self.ensure_one()
        url = '%s?%s' % (self.get_start_url(), werkzeug.urls.url_encode({'answer_token': answer and answer.access_token or None}))
        return {
            'type': 'ir.actions.act_url',
            'name': "Start Survey",
            'target': 'self',
            'url': url,
        }

    def action_print_survey(self, answer=None):
        """ Open the website page with the survey printable view """
        self.ensure_one()
        url = '%s?%s' % (self.get_print_url(), werkzeug.urls.url_encode({'answer_token': answer and answer.access_token or None}))
        return {
            'type': 'ir.actions.act_url',
            'name': "Print Survey",
            'target': 'new',
            'url': url
        }

    def action_result_survey(self):
        """ Open the website page with the survey results view """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'new',
            'url': '/survey/results/%s' % self.id
        }

    def action_test_survey(self):
        ''' Open the website page with the survey form into test mode'''
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Test Survey",
            'target': 'new',
            'url': '/survey/test/%s' % self.access_token,
        }

    def action_survey_user_input_completed(self):
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_user_input')
        ctx = dict(self.env.context)
        ctx.update({'search_default_survey_id': self.ids[0],
                    'search_default_completed': 1})
        action['context'] = ctx
        return action

    def action_survey_user_input_certified(self):
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_user_input')
        ctx = dict(self.env.context)
        ctx.update({'search_default_survey_id': self.ids[0],
                    'search_default_scoring_success': 1})
        action['context'] = ctx
        return action

    def action_survey_user_input(self):
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_user_input')
        ctx = dict(self.env.context)
        ctx.update({'search_default_survey_id': self.ids[0]})
        action['context'] = ctx
        return action

    def action_survey_preview_certification_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': f'/survey/{self.id}/certification_preview'
        }

    def action_start_session(self):
        """ Sets the necessary fields for the session to take place and starts it.
        The write is sudo'ed because a survey user can start a session even if it's
        not their own survey. """

        if not self.env.user.has_group('survey.group_survey_user'):
            raise AccessError(_('Only survey users can manage sessions.'))

        self.ensure_one()
        self.sudo().write({
            'questions_layout': 'page_per_question',
            'session_start_time': fields.Datetime.now(),
            'session_question_id': None,
            'session_state': 'ready'
        })
        return self.action_open_session_manager()

    def action_open_session_manager(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_url',
            'name': "Open Session Manager",
            'target': 'new',
            'url': '/survey/session/manage/%s' % self.access_token
        }

    def action_end_session(self):
        """ The write is sudo'ed because a survey user can end a session even if it's
        not their own survey. """

        if not self.env.user.has_group('survey.group_survey_user'):
            raise AccessError(_('Only survey users can manage sessions.'))

        self.sudo().write({'session_state': False})
        self.user_input_ids.sudo().write({'state': 'done'})
        self.env['bus.bus']._sendone(self.access_token, 'end_session', {})

    def get_start_url(self):
        return '/survey/start/%s' % self.access_token

    def get_start_short_url(self):
        """ See controller method docstring for more details. """
        return '/s/%s' % self.access_token[:6]

    def get_print_url(self):
        return '/survey/print/%s' % self.access_token

    # ------------------------------------------------------------
    # GRAPH / RESULTS
    # ------------------------------------------------------------

    def _prepare_statistics(self, user_input_lines=None):
        if user_input_lines:
            user_input_domain = [
                ('survey_id', 'in', self.ids),
                ('id', 'in', user_input_lines.mapped('user_input_id').ids)
            ]
        else:
            user_input_domain = [
                ('survey_id', 'in', self.ids),
                ('state', '=', 'done'),
                ('test_entry', '=', False)
            ]
        count_data_success = self.env['survey.user_input'].sudo()._read_group(user_input_domain, ['scoring_success'], ['__count'])
        completed_count = self.env['survey.user_input'].sudo().search_count(user_input_domain + [('state', "=", "done")])

        scoring_success_count = 0
        scoring_failed_count = 0
        for scoring_success, count in count_data_success:
            if scoring_success:
                scoring_success_count += count
            else:
                scoring_failed_count += count

        total = scoring_success_count + scoring_failed_count
        return {
            'global_success_rate': round((scoring_success_count / total) * 100, 1) if total > 0 else 0,
            'count_all': total,
            'count_finished': completed_count,
            'count_failed': scoring_failed_count,
            'count_passed': total - scoring_failed_count
        }

    # ------------------------------------------------------------
    # GAMIFICATION / BADGES
    # ------------------------------------------------------------

    def _prepare_challenge_category(self):
        return 'certification'

    def _create_certification_badge_trigger(self):
        self.ensure_one()
        if not self.certification_badge_id:
            raise ValueError(_('Certification Badge is not configured for the survey %(survey_name)s', survey_name=self.title))

        goal = self.env['gamification.goal.definition'].create({
            'name': self.title,
            'description': _("%s certification passed", self.title),
            'domain': "['&', ('survey_id', '=', %s), ('scoring_success', '=', True)]" % self.id,
            'computation_mode': 'count',
            'display_mode': 'boolean',
            'model_id': self.env.ref('survey.model_survey_user_input').id,
            'condition': 'higher',
            'batch_mode': True,
            'batch_distinctive_field': self.env.ref('survey.field_survey_user_input__partner_id').id,
            'batch_user_expression': 'user.partner_id.id'
        })
        challenge = self.env['gamification.challenge'].create({
            'name': _('%s challenge certification', self.title),
            'reward_id': self.certification_badge_id.id,
            'state': 'inprogress',
            'period': 'once',
            'challenge_category': self._prepare_challenge_category(),
            'reward_realtime': True,
            'report_message_frequency': 'never',
            'user_domain': [('karma', '>', 0)],
            'visibility_mode': 'personal'
        })
        self.env['gamification.challenge.line'].create({
            'definition_id': goal.id,
            'challenge_id': challenge.id,
            'target_goal': 1
        })

    def _handle_certification_badges(self, vals):
        if vals.get('certification_give_badge'):
            self.certification_badge_id.action_unarchive()
            # (re-)create challenge and goal
            for survey in self:
                survey._create_certification_badge_trigger()
        else:
            # if badge with owner : archive them, else delete everything (badge, challenge, goal)
            badges = self.mapped('certification_badge_id')
            challenges_to_delete = self.env['gamification.challenge'].search([('reward_id', 'in', badges.ids)])
            goals_to_delete = challenges_to_delete.mapped('line_ids').mapped('definition_id')
            badges.action_archive()
            # delete all challenges and goals because not needed anymore (challenge lines are deleted in cascade)
            challenges_to_delete.unlink()
            goals_to_delete.unlink()

    # ------------------------------------------------------------
    # TOOLING / MISC
    # ------------------------------------------------------------

    def _generate_session_codes(self, code_count=1, excluded_codes=False):
        """ Generate {code_count} session codes for surveys.

        We try to generate 4 digits code first and see if we have {code_count} unique ones.
        Then we raise up to 5 digits if we need more, etc until up to 10 digits.
        (We generate an extra 20 codes per loop to try to mitigate back luck collisions). """

        self.flush_model(['session_code'])

        session_codes = set()
        excluded_codes = excluded_codes or set()
        existing_codes = self.sudo().search_read(
            [('session_code', '!=', False)],
            ['session_code']
        )
        unavailable_codes = excluded_codes | {existing_code['session_code'] for existing_code in existing_codes}
        for digits_count in range(4, 10):
            range_lower_bound = 10 ** (digits_count - 1)
            range_upper_bound = (range_lower_bound * 10) - 1
            code_candidates = {str(random.randint(range_lower_bound, range_upper_bound)) for _ in range(code_count + 20)}
            session_codes |= code_candidates - unavailable_codes
            if len(session_codes) >= code_count:
                return list(session_codes)[:code_count]

        # could not generate enough codes, fill with False for remainder
        return session_codes + [False] * (code_count - len(session_codes))
