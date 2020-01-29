# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import random
import uuid
import werkzeug

from odoo import api, exceptions, fields, models, _
from odoo.osv import expression


class Survey(models.Model):
    """ Settings for a multi-page/multi-question survey. Each survey can have one or more attached pages
    and each page can display one or more questions. """
    _name = 'survey.survey'
    _description = 'Survey'
    _rec_name = 'title'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    # description
    title = fields.Char('Survey Title', required=True, translate=True)
    color = fields.Integer('Color Index', default=0)
    description = fields.Html(
        "Description", translate=True, sanitize=False,  # TDE FIXME: find a way to authorize videos
        help="The description will be displayed on the home page of the survey. You can use this to give the purpose and guidelines to your candidates before they start it.")
    description_done = fields.Html(
        "End Message", translate=True,
        help="This message will be displayed when survey is completed")
    background_image = fields.Binary("Background Image")
    active = fields.Boolean("Active", default=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'), ('open', 'In Progress'), ('closed', 'Closed')
    ], string="Survey Stage", default='draft', required=True,
        group_expand='_read_group_states')
    # questions
    question_and_page_ids = fields.One2many('survey.question', 'survey_id', string='Sections and Questions', copy=True)
    page_ids = fields.One2many('survey.question', string='Pages', compute="_compute_page_and_question_ids")
    question_ids = fields.One2many('survey.question', string='Questions', compute="_compute_page_and_question_ids")
    questions_layout = fields.Selection([
        ('one_page', 'One page with all the questions'),
        ('page_per_section', 'One page per section'),
        ('page_per_question', 'One page per question')],
        string="Layout", required=True, default='one_page')
    questions_selection = fields.Selection([
        ('all', 'All questions'),
        ('random', 'Randomized per section')],
        string="Selection", required=True, default='all',
        help="If randomized is selected, add the number of random questions next to the section.")
    progression_mode = fields.Selection([
        ('percent', 'Percentage'),
        ('number', 'Number')], string='Progression Mode', default='percent',
        help="If Number is selected, it will display the number of questions answered on the total number of question to answer.")
    # attendees
    user_input_ids = fields.One2many('survey.user_input', 'survey_id', string='User responses', readonly=True, groups='survey.group_survey_user')
    # security / access
    access_mode = fields.Selection([
        ('public', 'Anyone with the link'),
        ('token', 'Invited people only')], string='Access Mode',
        default='public', required=True)
    access_token = fields.Char('Access Token', default=lambda self: self._get_default_access_token(), copy=False)
    users_login_required = fields.Boolean('Login Required', help="If checked, users have to login before answering even with a valid token.")
    users_can_go_back = fields.Boolean('Users can go back', help="If checked, users can go back to previous pages.")
    users_can_signup = fields.Boolean('Users can signup', compute='_compute_users_can_signup')
    # statistics
    answer_count = fields.Integer("Registered", compute="_compute_survey_statistic")
    answer_done_count = fields.Integer("Attempts", compute="_compute_survey_statistic")
    answer_score_avg = fields.Float("Avg Score %", compute="_compute_survey_statistic")
    success_count = fields.Integer("Success", compute="_compute_survey_statistic")
    success_ratio = fields.Integer("Success Ratio", compute="_compute_survey_statistic")
    # scoring
    scoring_type = fields.Selection([
        ('no_scoring', 'No scoring'),
        ('scoring_with_answers', 'Scoring with answers at the end'),
        ('scoring_without_answers', 'Scoring without answers at the end')],
        string="Scoring", required=True, default='no_scoring')
    scoring_success_min = fields.Float('Success %', default=80.0)
    # attendees context: attempts and time limitation
    is_attempts_limited = fields.Boolean('Limited number of attempts', help="Check this option if you want to limit the number of attempts per user")
    attempts_limit = fields.Integer('Number of attempts', default=1)
    is_time_limited = fields.Boolean('The survey is limited in time')
    time_limit = fields.Float("Time limit (minutes)")
    # certification
    certification = fields.Boolean('Is a Certification')
    certification_mail_template_id = fields.Many2one(
        'mail.template', 'Email Template',
        domain="[('model', '=', 'survey.user_input')]",
        help="Automated email sent to the user when he succeeds the certification, containing his certification document.")
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
    certification_give_badge = fields.Boolean('Give Badge')
    certification_badge_id = fields.Many2one('gamification.badge', 'Certification Badge')
    certification_badge_id_dummy = fields.Many2one(related='certification_badge_id', string='Certification Badge ')

    _sql_constraints = [
        ('access_token_unique', 'unique(access_token)', 'Access token should be unique'),
        ('certification_check', "CHECK( scoring_type!='no_scoring' OR certification=False )",
            'You can only create certifications for surveys that have a scoring mechanism.'),
        ('time_limit_check', "CHECK( (is_time_limited=False) OR (time_limit is not null AND time_limit > 0) )",
            'The time limit needs to be a positive number if the survey is time limited.'),
        ('attempts_limit_check', "CHECK( (is_attempts_limited=False) OR (attempts_limit is not null AND attempts_limit > 0) )",
            'The attempts limit needs to be a positive number if the survey has a limited number of attempts.'),
        ('badge_uniq', 'unique (certification_badge_id)', "The badge for each survey should be unique!"),
        ('give_badge_check', "CHECK(certification_give_badge=False OR (certification_give_badge=True AND certification_badge_id is not null))",
            'Certification badge must be configured if Give Badge is set.'),
    ]

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
        base_domain = ['&', ('survey_id', 'in', self.ids), ('test_entry', '!=', True)]

        read_group_res = UserInput.read_group(base_domain, ['survey_id', 'state'], ['survey_id', 'state', 'scoring_percentage', 'scoring_success'], lazy=False)
        for item in read_group_res:
            stat[item['survey_id'][0]]['answer_count'] += item['__count']
            stat[item['survey_id'][0]]['answer_score_avg_total'] += item['scoring_percentage']
            if item['state'] == 'done':
                stat[item['survey_id'][0]]['answer_done_count'] += item['__count']
            if item['scoring_success']:
                stat[item['survey_id'][0]]['success_count'] += item['__count']

        for survey_id, values in stat.items():
            avg_total = stat[survey_id].pop('answer_score_avg_total')
            stat[survey_id]['answer_score_avg'] = avg_total / (stat[survey_id]['answer_done_count'] or 1)
            stat[survey_id]['success_ratio'] = (stat[survey_id]['success_count'] / (stat[survey_id]['answer_done_count'] or 1.0))*100

        for survey in self:
            survey.update(stat.get(survey._origin.id, default_vals))

    @api.depends('question_and_page_ids')
    def _compute_page_and_question_ids(self):
        for survey in self:
            survey.page_ids = survey.question_and_page_ids.filtered(lambda question: question.is_page)
            survey.question_ids = survey.question_and_page_ids - survey.page_ids

    @api.onchange('scoring_success_min')
    def _onchange_scoring_success_min(self):
        if self.scoring_success_min < 0 or self.scoring_success_min > 100:
            self.scoring_success_min = 80.0

    @api.onchange('scoring_type')
    def _onchange_scoring_type(self):
        if self.scoring_type == 'no_scoring':
            self.certification = False
            self.is_time_limited = False

    @api.onchange('users_login_required', 'access_mode')
    def _onchange_access_mode(self):
        if self.access_mode == 'public' and not self.users_login_required:
            self.is_attempts_limited = False

    @api.onchange('attempts_limit')
    def _onchange_attempts_limit(self):
        if self.attempts_limit <= 0:
            self.attempts_limit = 1

    @api.onchange('is_time_limited', 'time_limit')
    def _onchange_time_limit(self):
        if self.is_time_limited and (not self.time_limit or self.time_limit <= 0):
            self.time_limit = 10

    def _read_group_states(self, values, domain, order):
        selection = self.env['survey.survey'].fields_get(allfields=['state'])['state']['selection']
        return [s[0] for s in selection]

    @api.onchange('users_login_required', 'certification')
    def _onchange_set_certification_give_badge(self):
        if not self.users_login_required or not self.certification:
            self.certification_give_badge = False

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model
    def create(self, vals):
        survey = super(Survey, self).create(vals)
        if vals.get('certification_give_badge'):
            survey.sudo()._create_certification_badge_trigger()
        return survey

    def write(self, vals):
        result = super(Survey, self).write(vals)
        if 'certification_give_badge' in vals:
            return self.sudo()._handle_certification_badges(vals)
        return result

    def copy_data(self, default=None):
        title = _("%s (copy)") % (self.title)
        default = dict(default or {}, title=title)
        return super(Survey, self).copy_data(default)

    # ------------------------------------------------------------
    # ANSWER MANAGEMENT
    # ------------------------------------------------------------

    def _create_answer(self, user=False, partner=False, email=False, test_entry=False, check_attempts=True, **additional_vals):
        """ Main entry point to get a token back or create a new one. This method
        does check for current user access in order to explicitely validate
        security.

          :param user: target user asking for a token; it might be void or a
                       public user in which case an email is welcomed;
          :param email: email of the person asking the token is no user exists;
        """
        self.check_access_rights('read')
        self.check_access_rule('read')

        user_inputs = self.env['survey.user_input']
        for survey in self:
            if partner and not user and partner.user_ids:
                user = partner.user_ids[0]

            invite_token = additional_vals.pop('invite_token', False)
            survey._check_answer_creation(user, partner, email, test_entry=test_entry, check_attempts=check_attempts, invite_token=invite_token)
            answer_vals = {
                'survey_id': survey.id,
                'test_entry': test_entry,
            }
            if user and not user._is_public():
                answer_vals['partner_id'] = user.partner_id.id
                answer_vals['email'] = user.email
            elif partner:
                answer_vals['partner_id'] = partner.id
                answer_vals['email'] = partner.email
            else:
                answer_vals['email'] = email

            if invite_token:
                answer_vals['invite_token'] = invite_token
            elif survey.is_attempts_limited and survey.access_mode != 'public':
                # attempts limited: create a new invite_token
                # exception made for 'public' access_mode since the attempts pool is global because answers are
                # created every time the user lands on '/start'
                answer_vals['invite_token'] = self.env['survey.user_input']._generate_invite_token()

            answer_vals.update(additional_vals)
            user_inputs += user_inputs.create(answer_vals)

        for question in self.mapped('question_ids').filtered(lambda q: q.question_type == 'char_box' and q.save_as_email):
            for user_input in user_inputs:
                if user_input.email:
                    user_input.save_lines(question, user_input.email)

        return user_inputs

    def _check_answer_creation(self, user, partner, email, test_entry=False, check_attempts=True, invite_token=False):
        """ Ensure conditions to create new tokens are met. """
        self.ensure_one()
        if test_entry:
            # the current user must have the access rights to survey
            if not user.has_group('survey.group_survey_user'):
                raise exceptions.UserError(_('Creating test token is not allowed for you.'))
        else:
            if not self.active:
                raise exceptions.UserError(_('Creating token for archived surveys is not allowed.'))
            elif self.state == 'closed':
                raise exceptions.UserError(_('Creating token for closed surveys is not allowed.'))
            if self.access_mode == 'authentication':
                # signup possible -> should have at least a partner to create an account
                if self.users_can_signup and not user and not partner:
                    raise exceptions.UserError(_('Creating token for external people is not allowed for surveys requesting authentication.'))
                # no signup possible -> should be a not public user (employee or portal users)
                if not self.users_can_signup and (not user or user._is_public()):
                    raise exceptions.UserError(_('Creating token for external people is not allowed for surveys requesting authentication.'))
            if self.access_mode == 'internal' and (not user or not user.has_group('base.group_user')):
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
                if page.random_questions_count > 0 and len(page.question_ids) > page.random_questions_count:
                    questions = questions.concat(*random.sample(page.question_ids, page.random_questions_count))
                else:
                    questions |= page.question_ids

        return questions

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
        if self.questions_layout == 'one_page':
            return None
        elif self.questions_layout == 'page_per_question' and self.questions_selection == 'random':
            return list(enumerate(
                user_input.predefined_question_ids
            ))
        else:
            return list(enumerate(
                self.question_ids if self.questions_layout == 'page_per_question' else self.page_ids
            ))

    @api.model
    def _previous_page_or_question_id(self, user_input, page_or_question_id):
        survey = user_input.survey_id
        pages_or_questions = survey._get_pages_or_questions(user_input)

        current_page_index = pages_or_questions.index(next(p for p in pages_or_questions if p[1].id == page_or_question_id))
        # is first page
        if current_page_index == 0:
            return None

        previous_page_id = pages_or_questions[current_page_index - 1][1].id

        return previous_page_id

    @api.model
    def next_page_or_question(self, user_input, page_or_question_id):
        """ The next page to display to the user, knowing that page_id is the id
            of the last displayed page.

            If page_id == 0, it will always return the first page of the survey.

            If all the pages have been displayed, it will return None

            .. note::
                It is assumed here that a careful user will not try to set go_back
                to True if she knows that the page to display is the first one!
                (doing this will probably cause a giant worm to eat her house)
        """
        survey = user_input.survey_id

        pages_or_questions = survey._get_pages_or_questions(user_input)
        if not pages_or_questions:
            return (None, False)

        # First page
        if page_or_question_id == 0:
            return (pages_or_questions[0][1], len(pages_or_questions) == 1)

        current_page_index = pages_or_questions.index(next(p for p in pages_or_questions if p[1].id == page_or_question_id))

        # All the pages have been displayed
        if current_page_index == len(pages_or_questions) - 1:
            return (None, False)
        else:
            show_last = current_page_index == len(pages_or_questions) - 2
            return (pages_or_questions[current_page_index + 1][1], show_last)

    def _get_survey_questions(self, answer=None, page_id=None, question_id=None):
        questions, page_or_question_id = None, None

        if self.questions_layout == 'page_per_section':
            if not page_id:
                raise ValueError("Page id is needed for question layout 'page_per_section'")
            page_id = int(page_id)
            questions = self.env['survey.question'].sudo().search([('survey_id', '=', self.id), ('page_id', '=', page_id)])
            page_or_question_id = page_id
        elif self.questions_layout == 'page_per_question':
            if not question_id:
                raise ValueError("Question id is needed for question layout 'page_per_question'")
            question_id = int(question_id)
            questions = self.env['survey.question'].sudo().browse(question_id)
            page_or_question_id = question_id
        else:
            questions = self.question_ids

        # we need the intersection of the questions of this page AND the questions prepared for that user_input
        # (because randomized surveys do not use all the questions of every page)
        if answer:
            questions = questions & answer.predefined_question_ids
        return questions, page_or_question_id

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_open(self):
        self.write({'state': 'open'})

    def action_close(self):
        self.write({'state': 'closed'})

    def action_send_survey(self):
        """ Open a window to compose an email, pre-filled with the survey message """
        # Ensure that this survey has at least one page with at least one question.
        if (not self.page_ids and self.questions_layout == 'page_per_section') or not self.question_ids:
            raise exceptions.UserError(_('You cannot send an invitation for a survey that has no questions.'))

        if self.state == 'closed':
            raise exceptions.UserError(_("You cannot send invitations for closed surveys."))

        template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)

        local_context = dict(
            self.env.context,
            default_survey_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            notif_layout='mail.mail_notification_light',
        )
        return {
            'type': 'ir.actions.act_window',
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
            'target': 'self',
            'url': url
        }

    def action_result_survey(self):
        """ Open the website page with the survey results view """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'self',
            'url': '/survey/results/%s' % self.id
        }

    def action_test_survey(self):
        ''' Open the website page with the survey form into test mode'''
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Test Survey",
            'target': 'self',
            'url': '/survey/test/%s' % self.access_token,
        }

    def action_survey_user_input_completed(self):
        action_rec = self.env.ref('survey.action_survey_user_input')
        action = action_rec.read()[0]
        ctx = dict(self.env.context)
        ctx.update({'search_default_survey_id': self.ids[0],
                    'search_default_completed': 1,
                    'search_default_not_test': 1})
        action['context'] = ctx
        return action

    def action_survey_user_input_certified(self):
        action_rec = self.env.ref('survey.action_survey_user_input')
        action = action_rec.read()[0]
        ctx = dict(self.env.context)
        ctx.update({'search_default_survey_id': self.ids[0],
                    'search_default_scoring_success': 1,
                    'search_default_not_test': 1})
        action['context'] = ctx
        return action

    def action_survey_user_input(self):
        action_rec = self.env.ref('survey.action_survey_user_input')
        action = action_rec.read()[0]
        ctx = dict(self.env.context)
        ctx.update({'search_default_survey_id': self.ids[0],
                    'search_default_not_test': 1})
        action['context'] = ctx
        return action

    def action_survey_preview_certification_template(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': '_blank',
            'url': '/survey/%s/get_certification_preview' % (self.id)
        }

    def get_start_url(self):
        return 'survey/start/%s' % self.access_token

    def get_print_url(self):
        return 'survey/print/%s' % self.access_token

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
        count_data = self.env['survey.user_input'].sudo().read_group(user_input_domain, ['scoring_success', 'id:count_distinct'], ['scoring_success'])

        scoring_success_count = 0
        scoring_failed_count = 0
        for count_data_item in count_data:
            if count_data_item['scoring_success']:
                scoring_success_count += count_data_item['scoring_success_count']
            else:
                scoring_failed_count += count_data_item['scoring_success_count']

        success_graph = json.dumps([{
            'text': _('Passed'),
            'count': scoring_success_count,
            'color': '#2E7D32'
        }, {
            'text': _('Missed'),
            'count': scoring_failed_count,
            'color': '#C62828'
        }])

        total = scoring_success_count + scoring_failed_count
        return {
            'global_success_rate': round((scoring_success_count / total) * 100, 1) if total > 0 else 0,
            'global_success_graph': success_graph
        }

    # ------------------------------------------------------------
    # GAMIFICATION / BADGES
    # ------------------------------------------------------------
    def _prepare_challenge_category(self):
        return 'certification'

    def _create_certification_badge_trigger(self):
        self.ensure_one()
        goal = self.env['gamification.goal.definition'].create({
            'name': self.title,
            'description': "%s certification passed" % self.title,
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
            'name': _('%s challenge certification' % self.title),
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
            # If badge already set on records, reactivate the ones that are not active.
            surveys_with_badge = self.filtered(lambda survey: survey.certification_badge_id
                                                                 and not survey.certification_badge_id.active)
            surveys_with_badge.mapped('certification_badge_id').write({'active': True})
            # (re-)create challenge and goal
            for survey in self:
                survey._create_certification_badge_trigger()
        else:
            # if badge with owner : archive them, else delete everything (badge, challenge, goal)
            badges = self.mapped('certification_badge_id')
            challenges_to_delete = self.env['gamification.challenge'].search([('reward_id', 'in', badges.ids)])
            goals_to_delete = challenges_to_delete.mapped('line_ids').mapped('definition_id')
            badges.write({'active': False})
            # delete all challenges and goals because not needed anymore (challenge lines are deleted in cascade)
            challenges_to_delete.unlink()
            goals_to_delete.unlink()
