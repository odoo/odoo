# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
from openerp.exceptions import UserError
from openerp.tools.translate import _


class ProjectProject(models.Model):
    _inherit = 'project.project'

    label_issues = fields.Char('Use Issues as', help="Customize the issues label, for example to call them cases.", default="Issues")
    project_escalation_id = fields.Many2one('project.project', 'Project Escalation',
                                            help='If any issue is escalated from the current Project, it will be listed under the project selected here.',
                                            states={'close': [('readonly', True)], 'cancelled': [('readonly', True)]})
    issue_ids = fields.One2many('project.issue', 'project_id', string="Issues",
                                domain=[('stage_id.fold', '=', False)])
    use_issues = fields.Boolean(default=True)
    issue_count = fields.Integer(compute='_issue_count', string="Issues")

    @api.multi
    def _issue_count(self):
        for project in self:
            project.issue_count = len(project.issue_ids)

    @api.constrains('project_escalation_id')
    def _check_escalation(self):
        if self.project_escalation_id and self.project_escalation_id.id == self.id:
            raise UserError(_("Error! You cannot assign escalation to the same project!"))
        return True

    def _check_create_write_values(self, vals):
        """ Perform some check on values given to create or write. """
        # Handle use_tasks / use_issues: if only one is checked, alias should take the same model
        if vals.get('use_tasks') and not vals.get('use_issues'):
            vals['alias_model'] = 'project.task'
        elif vals.get('use_issues') and not vals.get('use_tasks'):
            vals['alias_model'] = 'project.issue'

    @api.onchange('use_issues', 'use_tasks')
    def on_change_use_tasks_or_issues(self):
        if self.use_tasks and not self.use_issues:
            self.alias_model = 'project.task'
        elif not self.use_tasks and self.use_issues:
            self.alias_model = 'project.issue'

    @api.model
    def create(self, vals):
        self._check_create_write_values(vals)
        return super(ProjectProject, self).create(vals)

    @api.multi
    def write(self, vals):
        self._check_create_write_values(vals)
        return super(ProjectProject, self).write(vals)

    @api.v7
    def _get_alias_models(self, cr, uid, context=None):
        return [('project.task', "Tasks"), ("project.issue", "Issues")]

    @api.v8
    def _get_alias_models(self):
        return [('project.task', "Tasks"), ("project.issue", "Issues")]
