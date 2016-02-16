# -*- coding: utf-8 -*-
from openerp import models, fields, api


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

    @api.multi
    def write(self, values):
        res = super(Task, self).write(values)
        if 'stage_id' in values and values.get('stage_id'):
            template = self.env['project.task.type'].browse(values['stage_id']).rating_template_id
            if template:
                self.rating_send_request(template)
        return res


class Project(models.Model):

    _inherit = "project.project"

    @api.one
    @api.depends('percentage_satisfaction_task')
    def _compute_percentage_satisfaction_project(self):
        self.percentage_satisfaction_project = self.percentage_satisfaction_task

    @api.one
    @api.depends('tasks.rating_ids.rating')
    def _compute_percentage_satisfaction_task(self):
        activity = self.tasks.rating_get_grades()
        self.percentage_satisfaction_task = activity['great'] * 100 / sum(activity.values()) if sum(activity.values()) else -1

    percentage_satisfaction_task = fields.Integer(
        compute='_compute_percentage_satisfaction_task', string="Happy % on Task", store=True, default=-1)
    percentage_satisfaction_project = fields.Integer(
        compute="_compute_percentage_satisfaction_project", string="Happy % on Project", store=True, default=-1)
    is_visible_happy_customer = fields.Boolean(string="Customer Satisfaction", default=False,
        help="Display information about rating of the project on kanban and form view. This buttons will only be displayed if at least a rating exists.")


    @api.multi
    def action_view_task_rating(self):
        """ return the action to see all the rating about the tasks of the project """
        action = self.env['ir.actions.act_window'].for_xml_id('rating', 'action_view_rating')
        return dict(action, domain=[('rating', '!=', -1), ('res_id', 'in', self.tasks.ids), ('res_model', '=', 'project.task')])

    @api.multi
    def action_view_all_rating(self):
        """ return the action to see all the rating about the all sort of activity of the project (tasks, issues, ...) """
        return self.action_view_task_rating()
