# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from openerp import api, fields, models, _


class ProjectIssue(models.Model):

    _name = "project.issue"
    _inherit = ['project.issue', 'rating.mixin']

    rating_latest = fields.Float(default=-1)
    rating_count = fields.Integer(compute="_compute_rating_count")

    @api.multi
    def write(self, values):
        result = super(ProjectIssue, self).write(values)
        if 'stage_id' in values and values.get('stage_id'):
            self.filtered(lambda x: x.project_id.rating_status == 'stage')._send_issue_rating_mail()
        return result

    def _send_issue_rating_mail(self):
        for issue in self:
            rating_template = issue.stage_id.rating_template_id
            if rating_template:
                partner = issue.partner_id or None
                rated_partner = issue.user_id.partner_id
                if partner and rated_partner:
                    issue.rating_send_request(rating_template, partner, rated_partner, False)

    def _compute_rating_count(self):
        for issue in self:
            issue.rating_count = len(issue.rating_ids)


class Project(models.Model):

    _inherit = "project.project"

    def _send_rating_mail(self):
        super(Project, self)._send_rating_mail()
        for project in self:
            project.issue_ids._send_issue_rating_mail()

    @api.depends('percentage_satisfaction_task', 'percentage_satisfaction_issue')
    def _compute_percentage_satisfaction_project(self):
        super(Project, self)._compute_percentage_satisfaction_project()
        for project in self:
            domain = [('create_date', '>=', fields.Datetime.to_string(datetime.today() - timedelta(days=30)))]
            activity_great, activity_sum = 0, 0
            if project.use_tasks:
                activity_task = project.tasks.rating_get_grades(domain)
                activity_great = activity_task['great']
                activity_sum = sum(activity_task.values())
            if project.use_issues:
                activity_issue = project.issue_ids.rating_get_grades(domain)
                activity_great += activity_issue['great']
                activity_sum += sum(activity_issue.values())
            project.percentage_satisfaction_project = activity_great * 100 / activity_sum if activity_sum else -1

    @api.one
    @api.depends('issue_ids.rating_ids.rating')
    def _compute_percentage_satisfaction_issue(self):
        project_issue = self.env['project.issue'].search([('project_id', '=', self.id)])
        activity = project_issue.rating_get_grades()
        self.percentage_satisfaction_issue = activity['great'] * 100 / sum(activity.values()) if sum(activity.values()) else -1

    percentage_satisfaction_issue = fields.Integer(compute='_compute_percentage_satisfaction_issue', string='% Happy', store=True, default=-1)

    @api.multi
    def action_view_issue_rating(self):
        """ return the action to see all the rating about the issues of the project """
        action = self.env['ir.actions.act_window'].for_xml_id('rating', 'action_view_rating')
        issues = self.env['project.issue'].search([('project_id', 'in', self.ids)])
        return dict(action, domain=[('res_id', 'in', issues.ids), ('res_model', '=', 'project.issue')])

    @api.multi
    def action_view_all_rating(self):
        action = super(Project, self).action_view_all_rating()
        task_domain = action['domain'][1:] # remove the (rating != -1) condition
        domain = []
        if self.use_tasks: # add task domain, if neeeded
            domain = ['&'] + task_domain
        if self.use_issues: # add issue domain if needed
            issues = self.env['project.issue'].search([('project_id', 'in', self.ids)])
            domain = domain + ['&', ('res_id', 'in', issues.ids), ('res_model', '=', 'project.issue')]
        if self.use_tasks and self.use_issues:
            domain = ['|'] + domain
        domain = [('rating', '!=', -1)] + domain # prepend the condition to avoid empty rating
        return dict(action, domain=domain)



class Rating(models.Model):

    _inherit = "rating.rating"

    @api.model
    def apply_rating(self, rate, res_model=None, res_id=None, token=None):
        """ check if the auto_validation_kanban_state is activated. If so, apply the modification of the
            kanban state according to the given rating.
        """
        rating = super(Rating, self).apply_rating(rate, res_model, res_id, token)
        if rating.res_model == 'project.issue':
            issue = self.env[rating.res_model].sudo().browse(rating.res_id)
            issue.rating_latest = rating.rating
            if issue.stage_id.auto_validation_kanban_state:
                if rating.rating > 5:
                    issue.write({'kanban_state' : 'done'})
                else:
                    issue.write({'kanban_state' : 'blocked'})
        return rating
