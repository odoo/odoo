# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Project(models.Model):
    _inherit = 'project.project'

    issue_count = fields.Integer(compute='_compute_issue_count', string="Issues")
    issue_ids = fields.One2many('project.issue', 'project_id', string="Issues", domain=['|', ('stage_id.fold', '=', False), ('stage_id', '=', False)])
    label_issues = fields.Char(string='Use Issues as', help="Customize the issues label, for example to call them cases.", default='Issues')
    use_issues = fields.Boolean(related="analytic_account_id.use_issues", default=True)
    issue_needaction_count = fields.Integer(compute="_issue_needaction_count", string="Issues")

    @api.model
    def _get_alias_models(self):
        res = super(Project, self)._get_alias_models()
        res.append(("project.issue", "Issues"))
        return res

    @api.multi
    def _compute_issue_count(self):
        for project in self:
            project.issue_count = self.env['project.issue'].search_count([('project_id', '=', project.id), '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)])

    def _issue_needaction_count(self):
        issue_data = self.env['project.issue'].read_group([('project_id', 'in', self.ids), ('message_needaction', '=', True)], ['project_id'], ['project_id'])
        result = dict((data['project_id'][0], data['project_id_count']) for data in issue_data)
        for project in self:
            project.issue_needaction_count = int(result.get(project.id, 0))

    @api.onchange('use_issues', 'use_tasks')
    def _on_change_use_tasks_or_issues(self):
        if self.use_tasks and not self.use_issues:
            self.alias_model = 'project.task'
        elif not self.use_tasks and self.use_issues:
            self.alias_model = 'project.issue'

    @api.multi
    def write(self, vals):
        res = super(Project, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a project does it on its issues, too
            issues = self.with_context(active_test=False).mapped('issue_ids')
            issues.write({'active': vals['active']})
        return res
