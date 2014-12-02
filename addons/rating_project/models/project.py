# -*- coding: utf-8 -*-
from openerp import api, fields, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    template_id = fields.Many2one('email.template', string='Email Template',
                                  help="Select an email template. An email will be sent to the customer when the task reach this step.")


class Task(models.Model):
    _name = 'project.task'
    _inherit = ['project.task', 'rating.mixin']

    @api.multi
    def write(self, vals):
        if 'stage_id' in vals:
            template = self.env['project.task.type'].browse(
                vals.get('stage_id')).template_id
            if template:
                self.rating_send_request(
                    template, self.stage_id.id, self.partner_id, self.user_id)
        return super(Task, self).write(vals)


class Project(models.Model):
    _inherit = "project.project"

    @api.multi
    def action_view_rating(self):
        action = self.env['ir.actions.act_window'].for_xml_id(
            'rating', 'action_view_rating')
        return dict(action, domain=[('res_id', 'in', self.tasks.ids), ('res_model', '=', 'project.task')])

    @api.multi
    @api.depends('percentage_satisfaction_task')
    def _compute_percentage_satisfaction_project(self):
        for record in self:
            nbr_rated_task = self.env['rating.rating'].search_count([('res_model', '=', 'project.task'), ('res_id', 'in', record.tasks.ids), ('rating', '>=', 0)])
            record.percentage_satisfaction_project = record.percentage_satisfaction_task if nbr_rated_task else -1

    @api.multi
    def _compute_percentage_satisfaction_task(self):
        for record in self:
            activity = record.tasks.rating_get_repartition_per_grade()
            record.percentage_satisfaction_task = activity['great'] * 100 / sum(activity.values()) if sum(activity.values()) else 0

    @api.multi
    def _display_happy_customer(self):
        for record in self:
            record.is_visible_happy_customer = record.use_tasks

    percentage_satisfaction_task = fields.Integer(
        compute='_compute_percentage_satisfaction_task', string='% Happy')
    percentage_satisfaction_project = fields.Integer(
        compute="_compute_percentage_satisfaction_project", string="% Happy")
    is_visible_happy_customer = fields.Boolean(
        compute="_display_happy_customer", string="Is Visible")
