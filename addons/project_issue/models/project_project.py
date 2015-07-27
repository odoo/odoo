# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp import api


class project_project(osv.Model):
    _inherit = 'project.project'

    def _get_alias_models(self, cr, uid, context=None):
        res = super(project, self)._get_alias_models(cr, uid, context=context)
        res.append(("project.issue", "Issues"))
        return res


    def _issue_count(self, cr, uid, ids, field_name, arg, context=None):
        Issue = self.pool['project.issue']
        return {
            project_id: Issue.search_count(cr,uid, [('project_id', '=', project_id), '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)], context=context)
            for project_id in ids
        }

    def _issue_needaction_count(self, cr, uid, ids, field_name, arg, context=None):
        Issue = self.pool['project.issue']
        res = dict.fromkeys(ids, 0)
        projects = Issue.read_group(cr, uid, [('project_id', 'in', ids), ('message_needaction', '=', True)], ['project_id'], ['project_id'], context=context)
        res.update({project['project_id'][0]: int(project['project_id_count']) for project in projects})
        return res

    _columns = {
        'issue_count': fields.function(_issue_count, type='integer', string="Issues",),
        'issue_ids': fields.one2many('project.issue', 'project_id', string="Issues",
                                    domain=['|', ('stage_id.fold', '=', False), ('stage_id', '=', False)]),
        'issue_needaction_count': fields.function(_issue_needaction_count, type='integer', string="Issues",),
        'label_issues': fields.char('Use Issues as', help="Customize the issues label, for example to call them cases."),
    }

    _defaults = {
        'use_issues': True,
        'label_issues': 'Issues',
    }

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

    @api.multi
    def write(self, vals):
        self._check_create_write_values(vals)
        res = super(project_project, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a project does it on its issues, too
            issues = self.with_context(active_test=False).mapped('issue_ids')
            issues.write({'active': vals['active']})
        return res
