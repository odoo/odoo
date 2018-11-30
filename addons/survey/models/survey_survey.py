# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter, OrderedDict
from itertools import product
from werkzeug import urls

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import UserError


class Survey(models.Model):
    """ Settings for a multi-page/multi-question survey.
        Each survey can have one or more attached pages, and each page can display
        one or more questions.
    """

    _name = 'survey.survey'
    _description = 'Survey'
    _rec_name = 'title'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_stage(self):
        return self.env['survey.stage'].search([], limit=1).id

    title = fields.Char('Title', required=True, translate=True)
    page_ids = fields.One2many('survey.page', 'survey_id', string='Pages', copy=True)
    stage_id = fields.Many2one('survey.stage', string="Stage", default=_default_stage,
                               ondelete="restrict", copy=False, group_expand='_read_group_stage_ids')
    auth_required = fields.Boolean('Login required', help="Users with a public link will be requested to login before taking part to the survey",
        oldname="authenticate")
    users_can_go_back = fields.Boolean('Users can go back', help="If checked, users can go back to previous pages.")
    tot_sent_survey = fields.Integer("Number of sent surveys", compute="_compute_survey_statistic")
    tot_start_survey = fields.Integer("Number of started surveys", compute="_compute_survey_statistic")
    tot_comp_survey = fields.Integer("Number of completed surveys", compute="_compute_survey_statistic")
    description = fields.Html("Description", translate=True, help="A long description of the purpose of the survey")
    color = fields.Integer('Color Index', default=0)
    user_input_ids = fields.One2many('survey.user_input', 'survey_id', string='User responses', readonly=True)
    designed = fields.Boolean("Is designed?", compute="_is_designed")
    public_url = fields.Char("Public link", compute="_compute_survey_url")
    public_url_html = fields.Char("Public link (html version)", compute="_compute_survey_url")
    print_url = fields.Char("Print link", compute="_compute_survey_url")
    result_url = fields.Char("Results link", compute="_compute_survey_url")
    email_template_id = fields.Many2one('mail.template', string='Email Template', ondelete='set null')
    thank_you_message = fields.Html("Thanks Message", translate=True, help="This message will be displayed when survey is completed")
    quizz_mode = fields.Boolean("Quizz Mode")
    active = fields.Boolean("Active", default=True)
    is_closed = fields.Boolean("Is closed", related='stage_id.closed', readonly=False)

    def _is_designed(self):
        for survey in self:
            if not survey.page_ids or not [page.question_ids for page in survey.page_ids if page.question_ids]:
                survey.designed = False
            else:
                survey.designed = True

    @api.multi
    def _compute_survey_statistic(self):
        UserInput = self.env['survey.user_input']

        sent_survey = UserInput.search([('survey_id', 'in', self.ids), ('input_type', '=', 'link')])
        start_survey = UserInput.search(['&', ('survey_id', 'in', self.ids), '|', ('state', '=', 'skip'), ('state', '=', 'done')])
        complete_survey = UserInput.search([('survey_id', 'in', self.ids), ('state', '=', 'done')])

        for survey in self:
            survey.tot_sent_survey = len(sent_survey.filtered(lambda user_input: user_input.survey_id == survey))
            survey.tot_start_survey = len(start_survey.filtered(lambda user_input: user_input.survey_id == survey))
            survey.tot_comp_survey = len(complete_survey.filtered(lambda user_input: user_input.survey_id == survey))

    def _compute_survey_url(self):
        """ Computes a public URL for the survey """
        base_url = '/' if self.env.context.get('relative_url') else \
                   self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for survey in self:
            survey.public_url = urls.url_join(base_url, "survey/start/%s" % (slug(survey)))
            survey.print_url = urls.url_join(base_url, "survey/print/%s" % (slug(survey)))
            survey.result_url = urls.url_join(base_url, "survey/results/%s" % (slug(survey)))
            survey.public_url_html = '<a href="%s">%s</a>' % (survey.public_url, _("Click here to start survey"))

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    # Public methods #
    def copy_data(self, default=None):
        title = _("%s (copy)") % (self.title)
        default = dict(default or {}, title=title)
        return super(Survey, self).copy_data(default)

    @api.model
    def next_page(self, user_input, page_id, go_back=False):
        """ The next page to display to the user, knowing that page_id is the id
            of the last displayed page.

            If page_id == 0, it will always return the first page of the survey.

            If all the pages have been displayed and go_back == False, it will
            return None

            If go_back == True, it will return the *previous* page instead of the
            next page.

            .. note::
                It is assumed here that a careful user will not try to set go_back
                to True if she knows that the page to display is the first one!
                (doing this will probably cause a giant worm to eat her house)
        """
        survey = user_input.survey_id
        pages = list(enumerate(survey.page_ids))

        # First page
        if page_id == 0:
            return (pages[0][1], 0, len(pages) == 1)

        current_page_index = pages.index(next(p for p in pages if p[1].id == page_id))

        # All the pages have been displayed
        if current_page_index == len(pages) - 1 and not go_back:
            return (None, -1, False)
        # Let's get back, baby!
        elif go_back and survey.users_can_go_back:
            return (pages[current_page_index - 1][1], current_page_index - 1, False)
        else:
            # This will show the last page
            if current_page_index == len(pages) - 2:
                return (pages[current_page_index + 1][1], current_page_index + 1, True)
            # This will show a regular page
            else:
                return (pages[current_page_index + 1][1], current_page_index + 1, False)

    @api.multi
    def filter_input_ids(self, filters, finished=False):
        """If user applies any filters, then this function returns list of
           filtered user_input_id and label's strings for display data in web.
           :param filters: list of dictionary (having: row_id, ansewr_id)
           :param finished: True for completely filled survey,Falser otherwise.
           :returns list of filtered user_input_ids.
        """
        self.ensure_one()
        if filters:
            domain_filter, choice = [], []
            for current_filter in filters:
                row_id, answer_id = current_filter['row_id'], current_filter['answer_id']
                if row_id == 0:
                    choice.append(answer_id)
                else:
                    domain_filter.extend(['|', ('value_suggested_row.id', '=', row_id), ('value_suggested.id', '=', answer_id)])
            if choice:
                domain_filter.insert(0, ('value_suggested.id', 'in', choice))
            else:
                domain_filter = domain_filter[1:]
            input_lines = self.env['survey.user_input_line'].search(domain_filter)
            filtered_input_ids = [input_line.user_input_id.id for input_line in input_lines]
        else:
            filtered_input_ids = []
        if finished:
            UserInput = self.env['survey.user_input']
            if not filtered_input_ids:
                user_inputs = UserInput.search([('survey_id', '=', self.id)])
            else:
                user_inputs = UserInput.browse(filtered_input_ids)
            return user_inputs.filtered(lambda input_item: input_item.state == 'done').ids
        return filtered_input_ids

    @api.model
    def get_filter_display_data(self, filters):
        """Returns data to display current filters
            :param filters: list of dictionary (having: row_id, answer_id)
            :returns list of dict having data to display filters.
        """
        filter_display_data = []
        if filters:
            Label = self.env['survey.label']
            for current_filter in filters:
                row_id, answer_id = current_filter['row_id'], current_filter['answer_id']
                label = Label.browse(answer_id)
                question = label.question_id
                if row_id == 0:
                    labels = label
                else:
                    labels = Label.browse([row_id, answer_id])
                filter_display_data.append({'question_text': question.question,
                                            'labels': labels.mapped('value')})
        return filter_display_data

    @api.model
    def prepare_result(self, question, current_filters=None):
        """ Compute statistical data for questions by counting number of vote per choice on basis of filter """
        current_filters = current_filters if current_filters else []
        result_summary = {}

        # Calculate and return statistics for choice
        if question.question_type in ['simple_choice', 'multiple_choice']:
            comments = []
            answers = OrderedDict((label.id, {'text': label.value, 'count': 0, 'answer_id': label.id}) for label in question.labels_ids)
            for input_line in question.user_input_line_ids:
                if input_line.answer_type == 'suggestion' and answers.get(input_line.value_suggested.id) and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    answers[input_line.value_suggested.id]['count'] += 1
                if input_line.answer_type == 'text' and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    comments.append(input_line)
            result_summary = {'answers': list(answers.values()), 'comments': comments}

        # Calculate and return statistics for matrix
        if question.question_type == 'matrix':
            rows = OrderedDict()
            answers = OrderedDict()
            res = dict()
            comments = []
            [rows.update({label.id: label.value}) for label in question.labels_ids_2]
            [answers.update({label.id: label.value}) for label in question.labels_ids]
            for cell in product(rows, answers):
                res[cell] = 0
            for input_line in question.user_input_line_ids:
                if input_line.answer_type == 'suggestion' and (not(current_filters) or input_line.user_input_id.id in current_filters) and input_line.value_suggested_row:
                    res[(input_line.value_suggested_row.id, input_line.value_suggested.id)] += 1
                if input_line.answer_type == 'text' and (not(current_filters) or input_line.user_input_id.id in current_filters):
                    comments.append(input_line)
            result_summary = {'answers': answers, 'rows': rows, 'result': res, 'comments': comments}

        # Calculate and return statistics for free_text, textbox, date
        if question.question_type in ['free_text', 'textbox', 'date']:
            result_summary = []
            for input_line in question.user_input_line_ids:
                if not(current_filters) or input_line.user_input_id.id in current_filters:
                    result_summary.append(input_line)

        # Calculate and return statistics for numerical_box
        if question.question_type == 'numerical_box':
            result_summary = {'input_lines': []}
            all_inputs = []
            for input_line in question.user_input_line_ids:
                if not(current_filters) or input_line.user_input_id.id in current_filters:
                    all_inputs.append(input_line.value_number)
                    result_summary['input_lines'].append(input_line)
            if all_inputs:
                result_summary.update({'average': round(sum(all_inputs) / len(all_inputs), 2),
                                       'max': round(max(all_inputs), 2),
                                       'min': round(min(all_inputs), 2),
                                       'sum': sum(all_inputs),
                                       'most_common': Counter(all_inputs).most_common(5)})
        return result_summary

    @api.model
    def get_input_summary(self, question, current_filters=None):
        """ Returns overall summary of question e.g. answered, skipped, total_inputs on basis of filter """
        current_filters = current_filters if current_filters else []
        result = {}
        if question.survey_id.user_input_ids:
            total_input_ids = current_filters or [input_id.id for input_id in question.survey_id.user_input_ids if input_id.state != 'new']
            result['total_inputs'] = len(total_input_ids)
            question_input_ids = []
            for user_input in question.user_input_line_ids:
                if not user_input.skipped:
                    question_input_ids.append(user_input.user_input_id.id)
            result['answered'] = len(set(question_input_ids) & set(total_input_ids))
            result['skipped'] = result['total_inputs'] - result['answered']
        return result

    # Actions

    @api.multi
    def action_start_survey(self):
        """ Open the website page with the survey form """
        self.ensure_one()
        token = self.env.context.get('survey_token')
        trail = "?token=%s" % token if token else ""
        return {
            'type': 'ir.actions.act_url',
            'name': "Start Survey",
            'target': 'self',
            'url': self.with_context(relative_url=True).public_url + trail
        }

    @api.multi
    def action_send_survey(self):
        """ Open a window to compose an email, pre-filled with the survey message """
        # Ensure that this survey has at least one page with at least one question.
        if not self.page_ids or not [page.question_ids for page in self.page_ids if page.question_ids]:
            raise UserError(_('You cannot send an invitation for a survey that has no questions.'))

        if self.stage_id.closed:
            raise UserError(_("You cannot send invitations for closed surveys."))

        template = self.env.ref('survey.email_template_survey', raise_if_not_found=False)

        local_context = dict(
            self.env.context,
            default_model='survey.survey',
            default_res_id=self.id,
            default_survey_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
            notif_layout='mail.mail_notification_light',
        )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'survey.invite',
            'target': 'new',
            'context': local_context,
        }

    @api.multi
    def action_print_survey(self):
        """ Open the website page with the survey printable view """
        self.ensure_one()
        token = self.env.context.get('survey_token')
        trail = "?token=%s" % token if token else ""
        return {
            'type': 'ir.actions.act_url',
            'name': "Print Survey",
            'target': 'self',
            'url': self.with_context(relative_url=True).print_url + trail
        }

    @api.multi
    def action_result_survey(self):
        """ Open the website page with the survey results view """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Results of the Survey",
            'target': 'self',
            'url': self.with_context(relative_url=True).result_url
        }

    @api.multi
    def action_test_survey(self):
        ''' Open the website page with the survey form into test mode'''
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'name': "Test Survey",
            'target': 'self',
            'url': '/survey/test/%s' % self.id,
        }

    @api.multi
    def action_survey_user_input(self):
        action_rec = self.env.ref('survey.action_survey_user_input')
        action = action_rec.read()[0]
        ctx = dict(self.env.context)
        ctx.update({'search_default_survey_id': self.ids[0],
                    'search_default_completed': 1})
        action['context'] = ctx
        return action
