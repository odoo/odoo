# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval


class ProjectTaskType(models.Model):

    _inherit = 'project.task.type'

    def _default_domain_rating_template_id(self):
        return [('model', '=', 'project.task')]

    rating_template_id = fields.Many2one(
        'mail.template',
        string='Rating Email Template',
        domain=lambda self: self._default_domain_rating_template_id(),
        help="If set and if the project's rating configuration is 'Rating when changing stage', then an email will be sent to the customer when the task reaches this step.")
    auto_validation_kanban_state = fields.Boolean('Automatic kanban status', default=False,
        help="Automatically modify the kanban state when the customer replies to the feedback for this stage.\n"
            " * A good feedback from the customer will update the kanban state to 'ready for the new stage' (green bullet).\n"
            " * A medium or a bad feedback will set the kanban state to 'blocked' (red bullet).\n")


class Task(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'rating.mixin']

    @api.multi
    def write(self, values):
        res = super(Task, self).write(values)
        if 'stage_id' in values and values.get('stage_id'):
            self.filtered(lambda x: x.project_id.rating_status == 'stage')._send_task_rating_mail(force_send=True)
        return res

    def _send_task_rating_mail(self, force_send=False):
        for task in self:
            rating_template = task.stage_id.rating_template_id
            if rating_template:
                task.rating_send_request(rating_template, lang=task.partner_id.lang, force_send=force_send)

    def rating_get_partner_id(self):
        res = super(Task, self).rating_get_partner_id()
        if not res and self.project_id.partner_id:
            return self.project_id.partner_id
        return res

    @api.multi
    def rating_apply(self, rate, token=None, feedback=None, subtype=None):
        return super(Task, self).rating_apply(rate, token=token, feedback=feedback, subtype="rating_project.mt_task_rating")


class Project(models.Model):

    _inherit = "project.project"

    # This method should be called once a day by the scheduler
    @api.model
    def _send_rating_all(self):
        projects = self.search([('rating_status', '=', 'periodic'), ('rating_request_deadline', '<=', fields.Datetime.now())])
        projects._send_rating_mail()
        projects._compute_rating_request_deadline()

    def _send_rating_mail(self):
        for project in self:
            project.task_ids._send_task_rating_mail()

    @api.depends('percentage_satisfaction_task')
    def _compute_percentage_satisfaction_project(self):
        domain = [('create_date', '>=', fields.Datetime.to_string(fields.datetime.now() - timedelta(days=30)))]
        for project in self:
            activity = project.tasks.rating_get_grades(domain)
            project.percentage_satisfaction_project = activity['great'] * 100 / sum(pycompat.values(activity)) if sum(pycompat.values(activity)) else -1

    @api.one
    @api.depends('tasks.rating_ids.rating')
    def _compute_percentage_satisfaction_task(self):
        activity = self.tasks.rating_get_grades()
        self.percentage_satisfaction_task = activity['great'] * 100 / sum(pycompat.values(activity)) if sum(pycompat.values(activity)) else -1

    percentage_satisfaction_task = fields.Integer(
        compute='_compute_percentage_satisfaction_task', string="Happy % on Task", store=True, default=-1)
    percentage_satisfaction_project = fields.Integer(
        compute="_compute_percentage_satisfaction_project", string="Happy % on Project", store=True, default=-1)
    rating_request_deadline = fields.Datetime(compute='_compute_rating_request_deadline', store=True)
    rating_status = fields.Selection([('stage', 'Rating when changing stage'), ('periodic', 'Periodical Rating'), ('no','No rating')], 'Customer(s) Ratings', help="How to get the customer's feedbacks?\n"
                    "- Rating when changing stage: Email will be sent when a task/issue is pulled in another stage\n"
                    "- Periodical Rating: Email will be sent periodically\n\n"
                    "Don't forget to set up the mail templates on the stages for which you want to get the customer's feedbacks.", default="no", required=True)
    rating_status_period = fields.Selection([
            ('daily', 'Daily'), ('weekly', 'Weekly'), ('bimonthly', 'Twice a Month'),
            ('monthly', 'Once a Month'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')
        ], 'Rating Frequency')

    @api.depends('rating_status', 'rating_status_period')
    def _compute_rating_request_deadline(self):
        periods = {'daily': 1, 'weekly': 7, 'bimonthly': 15, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        for project in self:
            project.rating_request_deadline = fields.datetime.now() + timedelta(days=periods.get(project.rating_status_period, 0))

    @api.multi
    def action_view_task_rating(self):
        """ return the action to see all the rating about the tasks of the project """
        action = self.env['ir.actions.act_window'].for_xml_id('rating', 'action_view_rating')
        action_domain = safe_eval(action['domain']) if action['domain'] else []
        domain = ['&', ('res_id', 'in', self.tasks.ids), ('res_model', '=', 'project.task')]
        if action_domain:
            domain = ['&'] + domain + action_domain
        return dict(action, domain=domain)

    @api.multi
    def action_view_all_rating(self):
        """ return the action to see all the rating about the all sort of activity of the project (tasks, issues, ...) """
        return self.action_view_task_rating()
