# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class project_project(osv.Model):
    _inherit = 'project.project'

    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        Issue = self.pool['project.issue']
        return {
            project_id: Issue.search_count(cr,uid, [('project_id', '=', project_id), ('stage_id.fold', '=', False)], context=context)
            for project_id in ids
        }

    _columns = {
        'label_issues': fields.char('Use Issues as', help="Customize the issues label, for example to call them cases."),
        'project_escalation_id': fields.many2one('project.project', 'Project Escalation',
            help='If any issue is escalated from the current Project, it will be listed under the project selected here.',
            states={'close': [('readonly', True)], 'cancelled': [('readonly', True)]}),
        'issue_count': fields.function(_issue_count, type='integer', string="Issues",),
        'issue_ids': fields.one2many('project.issue', 'project_id', string="Issues",
                                    domain=[('stage_id.fold', '=', False)]),
    }

    _defaults = {
        'use_issues': True,
        'label_issues': 'Issues',
    }

    def _check_escalation(self, cr, uid, ids, context=None):
        project_obj = self.browse(cr, uid, ids[0], context=context)
        if project_obj.project_escalation_id:
            if project_obj.project_escalation_id.id == project_obj.id:
                return False
        return True

    _constraints = [
        (_check_escalation, 'Error! You cannot assign escalation to the same project!', ['project_escalation_id'])
    ]

    def _check_create_write_values(self, cr, uid, vals, context=None):
        """ Perform some check on values given to create or write. """
        # Handle use_tasks / use_issues: if only one is checked, alias should take the same model
        if vals.get('use_tasks') and not vals.get('use_issues'):
            vals['alias_model'] = 'project.task'
        elif vals.get('use_issues') and not vals.get('use_tasks'):
            vals['alias_model'] = 'project.issue'

    def on_change_use_tasks_or_issues(self, cr, uid, ids, use_tasks, use_issues, context=None):
        values = {}
        if use_tasks and not use_issues:
            values['alias_model'] = 'project.task'
        elif not use_tasks and use_issues:
            values['alias_model'] = 'project.issue'
        return {'value': values}

    def create(self, cr, uid, vals, context=None):
        self._check_create_write_values(cr, uid, vals, context=context)
        return super(project_project, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        self._check_create_write_values(cr, uid, vals, context=context)
        return super(project_project, self).write(cr, uid, ids, vals, context=context)

    def _get_alias_models(self, cr, uid, context=None):
        return [('project.task', "Tasks"), ("project.issue", "Issues")]
