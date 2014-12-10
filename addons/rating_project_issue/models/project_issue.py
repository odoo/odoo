# -*- coding: utf-8 -*-
from openerp import models, fields, api


class ProjectIssue(models.Model):
    _name = "project.issue"
    _inherit = ['project.issue', 'rating.mixin']

    @api.multi
    def write(self, vals):
        if 'stage_id' in vals:
            template = self.env['project.task.type'].browse(
                vals.get('stage_id')).template_id
            if template.id:
                self.rating_send_request(
                    template, self.stage_id.id, self.partner_id, self.user_id)
        return super(ProjectIssue, self).write(vals)


class Project(models.Model):
    _inherit = "project.project"

    @api.multi
    @api.depends('percentage_satisfaction_task', 'percentage_satisfaction_issue')
    def _compute_percentage_satisfaction_project(self):
        super(Project, self)._compute_percentage_satisfaction_project()
        rating_obj = self.env['rating.rating']
        for record in self:
            # get the number of rated tasks and issues
            nbr_rated_task = rating_obj.search_count([('res_model', '=', 'project.task'), ('res_id', 'in', record.tasks.ids),('rating', '>=', 0)])
            nbr_rated_issue = rating_obj.search_count([('res_model', '=', 'project.issue'), ('res_id', 'in', record.issue_ids.ids),('rating', '>=', 0)])
            nbr_project_rating = nbr_rated_issue + nbr_rated_task
            # compute the weighted arithmetic average
            ratio_task = float(nbr_rated_task) / float(nbr_project_rating) if nbr_project_rating else 0
            ratio_issue = float(nbr_rated_issue) / float(nbr_project_rating) if nbr_project_rating else 0
            record.percentage_satisfaction_project = round((ratio_task*record.percentage_satisfaction_task)+(ratio_issue*record.percentage_satisfaction_issue)) if nbr_project_rating else -1

    @api.multi
    def action_view_rating(self):
        action = super(Project, self).action_view_rating()
        issues = self.env['project.issue'].search([('project_id', 'in', self.ids)])
        issue_domain = ['&', ('res_id', 'in', issues.ids), ('res_model', '=', 'project.issue')]
        if self.use_issues and self.use_tasks and not self.env.context.get('res_model',False):
            return dict(action, domain=['|'] + issue_domain + ['&', ('res_id', 'in', self.tasks.ids), ('res_model', '=', 'project.task')])
        if self.use_issues and not self.use_tasks or self.env.context.get('res_model',False) == 'project.issue':
            return dict(action, domain=issue_domain)
        return action

    @api.multi
    def _compute_percentage_satisfaction_issue(self):
        for record in self:
            project_issue = self.env['project.issue'].search(
                [('project_id', '=', record.id)])
            activity = project_issue.rating_get_repartition_per_grade()
            record.percentage_satisfaction_issue = activity[
                'great'] * 100 / sum(activity.values()) if sum(activity.values()) else 0

    @api.multi
    def _display_happy_customer(self):
        for record in self:
            record.is_visible_happy_customer = record.use_tasks if record.use_tasks else record.use_issues

    percentage_satisfaction_issue = fields.Integer(
        compute='_compute_percentage_satisfaction_issue', string='% Happy')
