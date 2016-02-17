# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from openerp import api, fields, models, _


class ProjectTaskType(models.Model):

    _inherit = 'project.task.type'

    rating_template_id = fields.Many2one(
        'mail.template',
        string='Rating Email Template',
        domain=[('model', '=', 'rating.rating')],
        help="Select an email template. An email will be sent to the customer when the task reach this step.")
    auto_validation_kanban_state = fields.Boolean('Auto Kanban state validation', default=False,
        help="Automatically modify the kanban state when the customer reply to the feedback for this stage.\n"
            " * A great feedback from the customer will update the kanban state to 'ready for the new stage' (green bullet).\n"
            " * A medium or a bad feedback will set the kanban state to 'blocked' (red bullet).\n")

class Task(models.Model):

    _name = 'project.task'
    _inherit = ['project.task', 'rating.mixin']

    rating_latest = fields.Float(default=-1)
    rating_count = fields.Integer(compute="_compute_rating_count")

    @api.multi
    def write(self, values):
        result = super(Task, self).write(values)
        if 'stage_id' in values and values.get('stage_id'):
            self.filtered(lambda x: x.project_id.rating_status == 'stage')._send_task_rating_mail()
        return result

    def _send_task_rating_mail(self):
        for task in self:
            rating_template = task.stage_id.rating_template_id
            if rating_template:
                partner = self._get_partner_to_send_rating_mail(task)
                rated_partner = task.user_id.partner_id
                if partner and rated_partner:
                    task.rating_send_request(rating_template, partner, rated_partner, False)

    def _get_partner_to_send_rating_mail(self, task):
        return task.partner_id or task.project_id.partner_id or None

    def _compute_rating_count(self):
        for task in self:
            task.rating_count = len(task.rating_ids)


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
        domain = [('create_date', '>=', fields.Datetime.to_string(datetime.today() - timedelta(days=30)))]
        for project in self:
            activity = project.tasks.rating_get_grades(domain)
            project.percentage_satisfaction_project = activity['great'] * 100 / sum(activity.values()) if sum(activity.values()) else -1

    @api.one
    @api.depends('tasks.rating_ids.rating')
    def _compute_percentage_satisfaction_task(self):
        activity = self.tasks.rating_get_grades()
        self.percentage_satisfaction_task = activity['great'] * 100 / sum(activity.values()) if sum(activity.values()) else -1

    percentage_satisfaction_task = fields.Integer(
        compute='_compute_percentage_satisfaction_task', string='% Happy', store=True, default=-1)
    percentage_satisfaction_project = fields.Integer(
        compute="_compute_percentage_satisfaction_project", string="% Happy", store=True, default=-1)
    rating_request_deadline = fields.Datetime(compute='_compute_rating_request_deadline', store=True)
    rating_status = fields.Selection([('stage', 'Rating on Stage'), ('periodic', 'Periodical Rating')], 'Customer Ratings', help="How to send rating mail?:\n"
                    "- Rating on stage : Rating mail will be sent when a stage of a task/issue is changed\n"
                    "- Periodical Rating: Rating mail will be sent periodically on a task/issue")
    rating_status_period = fields.Selection([
            ('daily', 'Every Day'), ('weekly', 'Every Week'), ('bimonthly', 'Twice a Month'),
            ('monthly', 'Once a Month'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')
        ], 'Rating Frequency')

    @api.depends('rating_status', 'rating_status_period')
    def _compute_rating_request_deadline(self):
        periods = {'daily': 1, 'weekly': 7, 'bimonthly': 15, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        for project in self:
            project.rating_request_deadline = datetime.today() + timedelta(days=periods.get(project.rating_status_period, 0))

    @api.multi
    def action_view_task_rating(self):
        """ return the action to see all the rating about the tasks of the project """
        action = self.env['ir.actions.act_window'].for_xml_id('rating', 'action_view_rating')
        return dict(action, domain=[('rating', '!=', -1), ('res_id', 'in', self.tasks.ids), ('res_model', '=', 'project.task')])

    @api.multi
    def action_view_all_rating(self):
        """ return the action to see all the rating about the all sort of activity of the project (tasks, issues, ...) """
        return self.action_view_task_rating()



class Rating(models.Model):

    _inherit = "rating.rating"

    @api.model
    def apply_rating(self, rate, res_model=None, res_id=None, token=None):
        """ check if the auto_validation_kanban_state is activated. If so, apply the modification of the
            kanban state according to the given rating.
        """
        rating = super(Rating, self).apply_rating(rate, res_model, res_id, token)
        if rating.res_model == 'project.task':
            task = self.env[rating.res_model].sudo().browse(rating.res_id)
            task.rating_latest = rating.rating
            if task.stage_id.auto_validation_kanban_state:
                if rating.rating > 5:
                    task.write({'kanban_state' : 'done'})
                else:
                    task.write({'kanban_state' : 'blocked'})
        return rating
