# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
from lxml import etree
import time

from openerp import api
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class project_task_type(osv.osv):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence'
    _columns = {
        'name': fields.char('Stage Name', required=True, translate=True),
        'description': fields.text('Description', translate=True),
        'sequence': fields.integer('Sequence'),
        'project_ids': fields.many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', 'Projects'),
        'legend_priority': fields.char(
            'Priority Management Explanation', translate=True,
            help='Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.'),
        'legend_blocked': fields.char(
            'Kanban Blocked Explanation', translate=True,
            help='Override the default value displayed for the blocked state for kanban selection, when the task or issue is in that stage.'),
        'legend_done': fields.char(
            'Kanban Valid Explanation', translate=True,
            help='Override the default value displayed for the done state for kanban selection, when the task or issue is in that stage.'),
        'legend_normal': fields.char(
            'Kanban Ongoing Explanation', translate=True,
            help='Override the default value displayed for the normal state for kanban selection, when the task or issue is in that stage.'),
        'fold': fields.boolean('Folded in Tasks Pipeline',
                               help='This stage is folded in the kanban view when '
                               'there are no records in that stage to display.'),
    }

    def _get_default_project_ids(self, cr, uid, ctx=None):
        if ctx is None:
            ctx = {}
        default_project_id = ctx.get('default_project_id')
        return [default_project_id] if default_project_id else None

    _defaults = {
        'sequence': 1,
        'project_ids': _get_default_project_ids,
    }
    _order = 'sequence'


class project(osv.osv):
    _name = "project.project"
    _description = "Project"
    _inherits = {'account.analytic.account': "analytic_account_id",
                 "mail.alias": "alias_id"}
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _period_number = 5

    def _auto_init(self, cr, context=None):
        """ Installation hook: aliases, project.project """
        # create aliases for all projects and avoid constraint errors
        alias_context = dict(context, alias_model_name='project.task')
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(project, self)._auto_init,
            'project.task', self._columns['alias_id'], 'id', alias_prefix='project+', alias_defaults={'project_id':'id'}, context=alias_context)

    def onchange_partner_id(self, cr, uid, ids, part=False, context=None):
        partner_obj = self.pool.get('res.partner')
        val = {}
        if not part:
            return {'value': val}
        if 'pricelist_id' in self.fields_get(cr, uid, context=context):
            pricelist = partner_obj.read(cr, uid, part, ['property_product_pricelist'], context=context)
            pricelist_id = pricelist.get('property_product_pricelist', False) and pricelist.get('property_product_pricelist')[0] or False
            val['pricelist_id'] = pricelist_id
        return {'value': val}

    def unlink(self, cr, uid, ids, context=None):
        alias_ids = []
        mail_alias = self.pool.get('mail.alias')
        analytic_account_to_delete = set()
        for proj in self.browse(cr, uid, ids, context=context):
            if proj.tasks:
                raise UserError(_('You cannot delete a project containing tasks. You can either delete all the project\'s tasks and then delete the project or simply deactivate the project.'))
            elif proj.alias_id:
                alias_ids.append(proj.alias_id.id)
            if proj.analytic_account_id and not proj.analytic_account_id.line_ids:
                analytic_account_to_delete.add(proj.analytic_account_id.id)
        res = super(project, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        self.pool['account.analytic.account'].unlink(cr, uid, list(analytic_account_to_delete), context=context)
        return res

    def _get_attached_docs(self, cr, uid, ids, field_name, arg, context):
        res = {}
        attachment = self.pool.get('ir.attachment')
        task = self.pool.get('project.task')
        for id in ids:
            project_attachments = attachment.search(cr, uid, [('res_model', '=', 'project.project'), ('res_id', '=', id)], context=context, count=True)
            task_ids = task.search(cr, uid, [('project_id', '=', id)], context=context)
            task_attachments = attachment.search(cr, uid, [('res_model', '=', 'project.task'), ('res_id', 'in', task_ids)], context=context, count=True)
            res[id] = (project_attachments or 0) + (task_attachments or 0)
        return res
    def _task_count(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res={}
        for project in self.browse(cr, uid, ids, context=context):
            res[project.id] = len(project.task_ids)
        return res
    def _get_alias_models(self, cr, uid, context=None):
        """ Overriden in project_issue to offer more options """
        return [('project.task', "Tasks")]

    def _get_visibility_selection(self, cr, uid, context=None):
        """ Overriden in portal_project to offer more options """
        return [('portal', _('Customer Project: visible in portal if the customer is a follower')),
                ('employees', _('All Employees Project: all employees can access')),
                ('followers', _('Private Project: followers only'))]

    def attachment_tree_view(self, cr, uid, ids, context):
        task_ids = self.pool.get('project.task').search(cr, uid, [('project_id', 'in', ids)])
        domain = [
             '|',
             '&', ('res_model', '=', 'project.project'), ('res_id', 'in', ids),
             '&', ('res_model', '=', 'project.task'), ('res_id', 'in', task_ids)]
        res_id = ids and ids[0] or False
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                        Documents are attached to the tasks and issues of your project.</p><p>
                        Send messages or log internal notes with attachments to link
                        documents to your project.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, res_id)
        }

    # Lambda indirection method to avoid passing a copy of the overridable method when declaring the field
    _alias_models = lambda self, *args, **kwargs: self._get_alias_models(*args, **kwargs)
    _visibility_selection = lambda self, *args, **kwargs: self._get_visibility_selection(*args, **kwargs)

    _columns = {
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the project without removing it."),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of Projects."),
        'analytic_account_id': fields.many2one(
            'account.analytic.account', 'Contract/Analytic',
            help="Link this project to an analytic account if you need financial management on projects. "
                 "It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc.",
            ondelete="cascade", required=True, auto_join=True),
        'label_tasks': fields.char('Use Tasks as', help="Gives label to tasks on project's kanban view."),
        'tasks': fields.one2many('project.task', 'project_id', "Task Activities"),
        'resource_calendar_id': fields.many2one('resource.calendar', 'Working Time', help="Timetable working hours to adjust the gantt diagram report", states={'close':[('readonly',True)]} ),
        'type_ids': fields.many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', 'Tasks Stages', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]}),
        'task_count': fields.function(_task_count, type='integer', string="Tasks",),
        'task_ids': fields.one2many('project.task', 'project_id',
                                    domain=['|', ('stage_id.fold', '=', False), ('stage_id', '=', False)]),
        'color': fields.integer('Color Index'),
        'user_id': fields.many2one('res.users', 'Project Manager'),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
                                    help="Internal email associated with this project. Incoming emails are automatically synchronized "
                                         "with Tasks (or optionally Issues if the Issue Tracker module is installed)."),
        'alias_model': fields.selection(_alias_models, "Alias Model", select=True, required=True,
                                        help="The kind of document created when an email is received on this project's email alias"),
        'privacy_visibility': fields.selection(_visibility_selection, 'Privacy / Visibility', required=True,
            help="Holds visibility of the tasks or issues that belong to the current project:\n"
                    "- Portal : employees see everything;\n"
                    "   if portal is activated, portal users see the tasks or issues followed by\n"
                    "   them or by someone of their company\n"
                    "- Employees Only: employees see all tasks or issues\n"
                    "- Followers Only: employees see only the followed tasks or issues; if portal\n"
                    "   is activated, portal users see the followed tasks or issues."),
        'state': fields.selection([('draft','New'),
                                   ('open','In Progress'),
                                   ('cancelled', 'Cancelled'),
                                   ('pending','Pending'),
                                   ('close','Closed')],
                                  'Status', required=True, copy=False),
        'doc_count': fields.function(
            _get_attached_docs, string="Number of documents attached", type='integer'
        ),
        'date_start': fields.date('Start Date'),
        'date': fields.date('Expiration Date', select=True, track_visibility='onchange'),
     }

    _order = "sequence, name, id"
    _defaults = {
        'active': True,
        'type': 'contract',
        'label_tasks': 'Tasks',
        'state': 'open',
        'sequence': 10,
        'user_id': lambda self,cr,uid,ctx: uid,
        'alias_model': 'project.task',
        'privacy_visibility': 'employees',
    }

    # TODO: Why not using a SQL contraints ?
    def _check_dates(self, cr, uid, ids, context=None):
        for leave in self.read(cr, uid, ids, ['date_start', 'date'], context=context):
            if leave['date_start'] and leave['date']:
                if leave['date_start'] > leave['date']:
                    return False
        return True

    _constraints = [
        (_check_dates, 'Error! project start-date must be lower than project end-date.', ['date_start', 'date'])
    ]

    def set_template(self, cr, uid, ids, context=None):
        return self.setActive(cr, uid, ids, value=False, context=context)

    def reset_project(self, cr, uid, ids, context=None):
        return self.setActive(cr, uid, ids, value=True, context=context)

    def map_tasks(self, cr, uid, old_project_id, new_project_id, context=None):
        """ copy and map tasks from old to new project """
        if context is None:
            context = {}
        map_task_id = {}
        task_obj = self.pool.get('project.task')
        proj = self.browse(cr, uid, old_project_id, context=context)
        for task in proj.tasks:
            # preserve task name and stage, normally altered during copy
            defaults = {'stage_id': task.stage_id.id,
                        'name': task.name}
            map_task_id[task.id] =  task_obj.copy(cr, uid, task.id, defaults, context=context)
        self.write(cr, uid, [new_project_id], {'tasks':[(6,0, map_task_id.values())]})
        task_obj.duplicate_task(cr, uid, map_task_id, context=context)
        return True

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        context = dict(context or {})
        context['active_test'] = False
        proj = self.browse(cr, uid, id, context=context)
        if not default.get('name'):
            default.update(name=_("%s (copy)") % (proj.name))
        res = super(project, self).copy(cr, uid, id, default, context)
        self.map_tasks(cr, uid, id, res, context=context)
        return res

    def duplicate_template(self, cr, uid, ids, context=None):
        context = dict(context or {})
        data_obj = self.pool.get('ir.model.data')
        result = []
        for proj in self.browse(cr, uid, ids, context=context):
            context.update({'analytic_project_copy': True})
            new_date_start = time.strftime('%Y-%m-%d')
            new_date_end = False
            if proj.date_start and proj.date:
                start_date = date(*time.strptime(proj.date_start,'%Y-%m-%d')[:3])
                end_date = date(*time.strptime(proj.date,'%Y-%m-%d')[:3])
                new_date_end = (datetime(*time.strptime(new_date_start,'%Y-%m-%d')[:3])+(end_date-start_date)).strftime('%Y-%m-%d')
            context.update({'copy':True})
            new_id = self.copy(cr, uid, proj.id, default = {
                                    'name':_("%s (copy)") % (proj.name),
                                    'state':'open',
                                    'date_start':new_date_start,
                                    'date':new_date_end}, context=context)
            result.append(new_id)

        if result and len(result):
            res_id = result[0]
            form_view_id = data_obj._get_id(cr, uid, 'project', 'edit_project')
            form_view = data_obj.read(cr, uid, form_view_id, ['res_id'])
            tree_view_id = data_obj._get_id(cr, uid, 'project', 'view_project')
            tree_view = data_obj.read(cr, uid, tree_view_id, ['res_id'])
            search_view_id = data_obj._get_id(cr, uid, 'project', 'view_project_project_filter')
            search_view = data_obj.read(cr, uid, search_view_id, ['res_id'])
            return {
                'name': _('Projects'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'project.project',
                'view_id': False,
                'res_id': res_id,
                'views': [(form_view['res_id'],'form'),(tree_view['res_id'],'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view['res_id'],
            }

    @api.multi
    def setActive(self, value=True):
        """ Set a project as active/inactive, and its tasks as well. """
        self.write({'active': value})

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        # Prevent double project creation when 'use_tasks' is checked + alias management
        create_context = dict(context, project_creation_in_progress=True,
                              alias_model_name=vals.get('alias_model', 'project.task'),
                              alias_parent_model_name=self._name,
                              mail_create_nosubscribe=True)

        ir_values = self.pool.get('ir.values').get_default(cr, uid, 'project.config.settings', 'generate_project_alias')
        if ir_values:
            vals['alias_name'] = vals.get('alias_name') or vals.get('name')
        project_id = super(project, self).create(cr, uid, vals, context=create_context)
        project_rec = self.browse(cr, uid, project_id, context=context)
        values = {'alias_parent_thread_id': project_id, 'alias_defaults': {'project_id': project_id}}
        self.pool.get('mail.alias').write(cr, uid, [project_rec.alias_id.id], values, context=context)
        return project_id

    def write(self, cr, uid, ids, vals, context=None):
        # if alias_model has been changed, update alias_model_id accordingly
        if vals.get('alias_model'):
            model_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', vals.get('alias_model', 'project.task'))])
            vals.update(alias_model_id=model_ids[0])
        res = super(project, self).write(cr, uid, ids, vals, context=context)
        if 'active' in vals:
            # archiving/unarchiving a project does it on its tasks, too
            projects = self.browse(cr, uid, ids, context)
            tasks = projects.with_context(active_test=False).mapped('tasks')
            tasks.write({'active': vals['active']})
        return res


class task(osv.osv):
    _name = "project.task"
    _description = "Task"
    _date_name = "date_start"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _mail_post_access = 'read'

    def _get_default_partner(self, cr, uid, context=None):
        if context is None:
            context = {}
        if 'default_project_id' in context:
            project = self.pool.get('project.project').browse(cr, uid, context['default_project_id'], context=context)
            if project and project.partner_id:
                return project.partner_id.id
        return False

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        if context is None:
            context = {}
        return self.stage_find(cr, uid, [], context.get('default_project_id'), [('fold', '=', False)], context=context)

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        if context is None:
            context = {}
        stage_obj = self.pool.get('project.task.type')
        order = stage_obj._order
        access_rights_uid = access_rights_uid or uid
        if read_group_order == 'stage_id desc':
            order = '%s desc' % order
        if 'default_project_id' in context:
            search_domain = ['|', ('project_ids', '=', context['default_project_id']), ('id', 'in', ids)]
        else:
            search_domain = [('id', 'in', ids)]
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids,
    }

    def onchange_remaining(self, cr, uid, ids, remaining=0.0, planned=0.0):
        if remaining and not planned:
            return {'value': {'planned_hours': remaining}}
        return {}

    def onchange_planned(self, cr, uid, ids, planned=0.0, effective=0.0):
        return {'value': {'remaining_hours': planned - effective}}

    def onchange_project(self, cr, uid, id, project_id, context=None):
        if project_id:
            project = self.pool.get('project.project').browse(cr, uid, project_id, context=context)
            if project and project.partner_id:
                return {'value': {'partner_id': project.partner_id.id}}
        return {'value': {'partner_id': False}}

    def onchange_user_id(self, cr, uid, ids, user_id, context=None):
        vals = {}
        if user_id:
            vals['date_start'] = fields.datetime.now()
        return {'value': vals}

    def duplicate_task(self, cr, uid, map_ids, context=None):
        mapper = lambda t: map_ids.get(t.id, t.id)
        for task in self.browse(cr, uid, map_ids.values(), context):
            new_child_ids = set(map(mapper, task.child_ids))
            new_parent_ids = set(map(mapper, task.parent_ids))
            if new_child_ids or new_parent_ids:
                task.write({'parent_ids': [(6,0,list(new_parent_ids))],
                            'child_ids':  [(6,0,list(new_child_ids))]})

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        current = self.browse(cr, uid, id, context=context)
        if not default.get('name'):
            default['name'] = _("%s (copy)") % current.name
        if 'remaining_hours' not in default:
            default['remaining_hours'] = current.planned_hours

        return super(task, self).copy_data(cr, uid, id, default, context)

    _columns = {
        'active': fields.boolean('Active'),
        'name': fields.char('Task Title', track_visibility='onchange', size=128, required=True, select=True),
        'description': fields.html('Description'),
        'priority': fields.selection([('0','Normal'), ('1','High')], 'Priority', select=True),
        'sequence': fields.integer('Sequence', select=True, help="Gives the sequence order when displaying a list of tasks."),
        'stage_id': fields.many2one('project.task.type', 'Stage', track_visibility='onchange', select=True,
                        domain="[('project_ids', '=', project_id)]", copy=False),
        'tag_ids': fields.many2many('project.tags', string='Tags', oldname='categ_ids'),
        'kanban_state': fields.selection([('normal', 'In Progress'),('done', 'Ready for next stage'),('blocked', 'Blocked')], 'Kanban State',
                                         track_visibility='onchange',
                                         help="A task's kanban state indicates special situations affecting it:\n"
                                              " * Normal is the default situation\n"
                                              " * Blocked indicates something is preventing the progress of this task\n"
                                              " * Ready for next stage indicates the task is ready to be pulled to the next stage",
                                         required=True, copy=False),
        'create_date': fields.datetime('Create Date', readonly=True, select=True),
        'write_date': fields.datetime('Last Modification Date', readonly=True, select=True), #not displayed in the view but it might be useful with base_action_rule module (and it needs to be defined first for that)
        'date_start': fields.datetime('Starting Date', select=True, copy=False),
        'date_end': fields.datetime('Ending Date', select=True, copy=False),
        'date_assign': fields.datetime('Assigning Date', select=True, copy=False, readonly=True),
        'date_deadline': fields.date('Deadline', select=True, copy=False),
        'date_last_stage_update': fields.datetime('Last Stage Update', select=True, copy=False, readonly=True),
        'project_id': fields.many2one('project.project', 'Project', ondelete='set null', select=True, track_visibility='onchange', change_default=True),
        'parent_ids': fields.many2many('project.task', 'project_task_parent_rel', 'task_id', 'parent_id', 'Parent Tasks'),
        'child_ids': fields.many2many('project.task', 'project_task_parent_rel', 'parent_id', 'task_id', 'Delegated Tasks'),
        'notes': fields.text('Notes'),
        'planned_hours': fields.float('Initially Planned Hours', help='Estimated time to do the task, usually set by the project manager when the task is in draft state.'),
        'remaining_hours': fields.float('Remaining Hours', digits=(16,2), help="Total remaining time, can be re-estimated periodically by the assignee of the task."),
        'user_id': fields.many2one('res.users', 'Assigned to', select=True, track_visibility='onchange'),
        'partner_id': fields.many2one('res.partner', 'Customer'),
        'manager_id': fields.related('project_id', 'analytic_account_id', 'user_id', type='many2one', relation='res.users', string='Project Manager'),
        'company_id': fields.many2one('res.company', 'Company'),
        'id': fields.integer('ID', readonly=True),
        'color': fields.integer('Color Index'),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'attachment_ids': fields.one2many('ir.attachment', 'res_id', domain=lambda self: [('res_model', '=', self._name)], auto_join=True, string='Attachments'),
        # In the domain of displayed_image_id, we couln't use attachment_ids because a one2many is represented as a list of commands so we used res_model & res_id
        'displayed_image_id': fields.many2one('ir.attachment', domain="[('res_model', '=', 'project.task'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]", string='Displayed Image'),
        'legend_blocked': fields.related("stage_id", "legend_blocked", type="char", string='Kanban Blocked Explanation'),
        'legend_done': fields.related("stage_id", "legend_done", type="char", string='Kanban Valid Explanation'),
        'legend_normal': fields.related("stage_id", "legend_normal", type="char", string='Kanban Ongoing Explanation'),
        }
    _defaults = {
        'stage_id': _get_default_stage_id,
        'project_id': lambda self, cr, uid, ctx=None: ctx.get('default_project_id') if ctx is not None else False,
        'date_last_stage_update': fields.datetime.now,
        'kanban_state': 'normal',
        'priority': '0',
        'sequence': 10,
        'active': True,
        'user_id': lambda obj, cr, uid, ctx=None: uid,
        'company_id': lambda self, cr, uid, ctx=None: self.pool.get('res.company')._company_default_get(cr, uid, 'project.task', context=ctx),
        'partner_id': lambda self, cr, uid, ctx=None: self._get_default_partner(cr, uid, context=ctx),
        'date_start': fields.datetime.now,
    }
    _order = "priority desc, sequence, date_start, name, id"

    def _check_recursion(self, cr, uid, ids, context=None):
        for id in ids:
            visited_branch = set()
            visited_node = set()
            res = self._check_cycle(cr, uid, id, visited_branch, visited_node, context=context)
            if not res:
                return False

        return True

    def _check_cycle(self, cr, uid, id, visited_branch, visited_node, context=None):
        if id in visited_branch: #Cycle
            return False

        if id in visited_node: #Already tested don't work one more time for nothing
            return True

        visited_branch.add(id)
        visited_node.add(id)

        #visit child using DFS
        task = self.browse(cr, uid, id, context=context)
        for child in task.child_ids:
            res = self._check_cycle(cr, uid, child.id, visited_branch, visited_node, context=context)
            if not res:
                return False

        visited_branch.remove(id)
        return True

    def _check_dates(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        obj_task = self.browse(cr, uid, ids[0], context=context)
        start = obj_task.date_start or False
        end = obj_task.date_end or False
        if start and end :
            if start > end:
                return False
        return True

    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive tasks.', ['parent_ids']),
        (_check_dates, 'Error ! Task starting date must be lower than its ending date.', ['date_start','date_end'])
    ]

    # Override view according to the company definition
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        users_obj = self.pool.get('res.users')
        if context is None: context = {}
        # read uom as admin to avoid access rights issues, e.g. for portal/share users,
        # this should be safe (no context passed to avoid side-effects)
        obj_tm = users_obj.browse(cr, SUPERUSER_ID, uid, context=context).company_id.project_time_mode_id
        tm = obj_tm and obj_tm.name or 'Hours'

        res = super(task, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

        # read uom as admin to avoid access rights issues, e.g. for portal/share users,
        # this should be safe (no context passed to avoid side-effects)
        obj_tm = users_obj.browse(cr, SUPERUSER_ID, uid, context=context).company_id.project_time_mode_id
        try:
            # using get_object to get translation value
            uom_hour = self.pool['ir.model.data'].get_object(cr, uid, 'product', 'product_uom_hour', context=context)
        except ValueError:
            uom_hour = False
        if not obj_tm or not uom_hour or obj_tm.id == uom_hour.id:
            return res

        eview = etree.fromstring(res['arch'])

        # if the project_time_mode_id is not in hours (so in days), display it as a float field
        def _check_rec(eview):
            if eview.attrib.get('widget','') == 'float_time':
                eview.set('widget','float')
            for child in eview:
                _check_rec(child)
            return True

        _check_rec(eview)

        res['arch'] = etree.tostring(eview)

        # replace reference of 'Hours' to 'Day(s)'
        for f in res['fields']:
            # TODO this NOT work in different language than english
            # the field 'Initially Planned Hours' should be replaced by 'Initially Planned Days'
            # but string 'Initially Planned Days' is not available in translation
            if 'Hours' in res['fields'][f]['string']:
                res['fields'][f]['string'] = res['fields'][f]['string'].replace('Hours', obj_tm.name)
        return res

    def get_empty_list_help(self, cr, uid, help, context=None):
        context = dict(context or {})
        context['empty_list_help_id'] = context.get('default_project_id')
        context['empty_list_help_model'] = 'project.project'
        context['empty_list_help_document_name'] = _("tasks")
        return super(task, self).get_empty_list_help(cr, uid, help, context=context)

    # ----------------------------------------
    # Case management
    # ----------------------------------------

    def stage_find(self, cr, uid, cases, section_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # collect all section_ids
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        for task in cases:
            if task.project_id:
                section_ids.append(task.project_id.id)
        search_domain = []
        if section_ids:
            search_domain = [('|')] * (len(section_ids) - 1)
            for section_id in section_ids:
                search_domain.append(('project_ids', '=', section_id))
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool.get('project.task.type').search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def _check_child_task(self, cr, uid, ids, context=None):
        if context == None:
            context = {}
        tasks = self.browse(cr, uid, ids, context=context)
        for task in tasks:
            if task.child_ids:
                for child in task.child_ids:
                    if child.stage_id and not child.stage_id.fold:
                        raise UserError(_("Child task still open.\nPlease cancel or complete child task first."))
        return True


    def _store_history(self, cr, uid, ids, context=None):
        for task in self.browse(cr, uid, ids, context=context):
            self.pool.get('project.task.history').create(cr, uid, {
                'task_id': task.id,
                'remaining_hours': task.remaining_hours,
                'planned_hours': task.planned_hours,
                'kanban_state': task.kanban_state,
                'type_id': task.stage_id.id,
                'user_id': task.user_id.id

            }, context=context)
        return True

    # ------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------

    def create(self, cr, uid, vals, context=None):
        context = dict(context or {})

        # for default stage
        if vals.get('project_id') and not context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        # user_id change: update date_assign
        if vals.get('user_id'):
            vals['date_assign'] = fields.datetime.now()
        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        task_id = super(task, self).create(cr, uid, vals, context=create_context)
        self._store_history(cr, uid, [task_id], context=context)
        return task_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]

        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.datetime.now()
        # user_id change: update date_assign
        if vals.get('user_id'):
            vals['date_assign'] = fields.datetime.now()

        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the task changes.
        if vals and not 'kanban_state' in vals and 'stage_id' in vals:
            new_stage = vals.get('stage_id')
            vals_reset_kstate = dict(vals, kanban_state='normal')
            for t in self.browse(cr, uid, ids, context=context):
                write_vals = vals_reset_kstate if t.stage_id.id != new_stage else vals
                super(task, self).write(cr, uid, [t.id], write_vals, context=context)
            result = True
        else:
            result = super(task, self).write(cr, uid, ids, vals, context=context)

        if any(item in vals for item in ['stage_id', 'remaining_hours', 'user_id', 'kanban_state']):
            self._store_history(cr, uid, ids, context=context)
        return result

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        self._check_child_task(cr, uid, ids, context=context)
        res = super(task, self).unlink(cr, uid, ids, context)
        return res

    def _get_total_hours(self):
        return self.remaining_hours

    def _generate_task(self, cr, uid, tasks, ident=4, context=None):
        context = context or {}
        result = ""
        ident = ' '*ident
        company = self.pool["res.users"].browse(cr, uid, uid, context=context).company_id
        duration_uom = {
            'day(s)': 'd', 'days': 'd', 'day': 'd', 'd': 'd',
            'month(s)': 'm', 'months': 'm', 'month': 'month', 'm': 'm',
            'week(s)': 'w', 'weeks': 'w', 'week': 'w', 'w': 'w',
            'hour(s)': 'H', 'hours': 'H', 'hour': 'H', 'h': 'H',
        }.get(company.project_time_mode_id.name.lower(), "hour(s)")
        for task in tasks:
            if task.stage_id and task.stage_id.fold:
                continue
            result += '''
%sdef Task_%s():
%s  todo = \"%.2f%s\"
%s  effort = \"%.2f%s\"''' % (ident, task.id, ident, task.remaining_hours, duration_uom, ident, task._get_total_hours(), duration_uom)
            start = []
            for t2 in task.parent_ids:
                start.append("up.Task_%s.end" % (t2.id,))
            if start:
                result += '''
%s  start = max(%s)
''' % (ident,','.join(start))

            if task.user_id:
                result += '''
%s  resource = %s
''' % (ident, 'User_'+str(task.user_id.id))

        result += "\n"
        return result

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'kanban_state' in init_values and record.kanban_state == 'blocked':
            return 'project.mt_task_blocked'
        elif 'kanban_state' in init_values and record.kanban_state == 'done':
            return 'project.mt_task_ready'
        elif 'user_id' in init_values and record.user_id:  # assigned -> new
            return 'project.mt_task_new'
        elif 'stage_id' in init_values and record.stage_id and record.stage_id.sequence <= 1:  # start stage -> new
            return 'project.mt_task_new'
        elif 'stage_id' in init_values:
            return 'project.mt_task_stage'
        return super(task, self)._track_subtype(cr, uid, ids, init_values, context=context)

    def _notification_group_recipients(self, cr, uid, ids, message, recipients, done_ids, group_data, context=None):
        """ Override the mail.thread method to handle project users and officers
        recipients. Indeed those will have specific action in their notification
        emails: creating tasks, assigning it. """
        group_project_user = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'project.group_project_user')
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and group_project_user in recipient.user_ids[0].groups_id.ids:
                group_data['group_project_user'] |= recipient
                done_ids.add(recipient.id)
        return super(task, self)._notification_group_recipients(cr, uid, ids, message, recipients, done_ids, group_data, context=context)

    def _notification_get_recipient_groups(self, cr, uid, ids, message, recipients, context=None):
        res = super(task, self)._notification_get_recipient_groups(cr, uid, ids, message, recipients, context=context)

        take_action = self._notification_link_helper(cr, uid, ids, 'assign', context=context)
        new_action_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'project.action_view_task')
        new_action = self._notification_link_helper(cr, uid, ids, 'new', context=context, action_id=new_action_id)

        task_record = self.browse(cr, uid, ids[0], context=context)
        actions = []
        if not task_record.user_id:
            actions.append({'url': take_action, 'title': _('I take it')})
        else:
            actions.append({'url': new_action, 'title': _('New Task')})

        res['group_project_user'] = {
            'actions': actions
        }
        return res

    @api.cr_uid_context
    def message_get_reply_to(self, cr, uid, ids, default=None, context=None):
        """ Override to get the reply_to of the parent project. """
        tasks = self.browse(cr, SUPERUSER_ID, ids, context=context)
        project_ids = set([task.project_id.id for task in tasks if task.project_id])
        aliases = self.pool['project.project'].message_get_reply_to(cr, uid, list(project_ids), default=default, context=context)
        return dict((task.id, aliases.get(task.project_id and task.project_id.id or 0, False)) for task in tasks)

    def email_split(self, cr, uid, ids, msg, context=None):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        task_ids = self.browse(cr, uid, ids, context=context)
        aliases = [task.project_id.alias_name for task in task_ids if task.project_id]
        return filter(lambda x: x.split('@')[0] not in aliases, email_list)

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Override to updates the document according to the email. """
        if custom_values is None:
            custom_values = {}
        defaults = {
            'name': msg.get('subject'),
            'planned_hours': 0.0,
            'partner_id': msg.get('author_id', False)
        }
        defaults.update(custom_values)

        res = super(task, self).message_new(cr, uid, msg, custom_values=defaults, context=context)
        email_list = self.email_split(cr, uid, [res], msg, context=context)
        partner_ids = self._find_partner_from_emails(cr, uid, [res], email_list, force_create=True, context=context)
        self.message_subscribe(cr, uid, [res], partner_ids, context=context)
        return res

    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        """ Override to update the task according to the email. """
        if update_vals is None:
            update_vals = {}
        maps = {
            'cost': 'planned_hours',
        }
        for line in msg['body'].split('\n'):
            line = line.strip()
            res = tools.command_re.match(line)
            if res:
                match = res.group(1).lower()
                field = maps.get(match)
                if field:
                    try:
                        update_vals[field] = float(res.group(2).lower())
                    except (ValueError, TypeError):
                        pass

        email_list = self.email_split(cr, uid, ids, msg, context=context)
        partner_ids = self._find_partner_from_emails(cr, uid, ids, email_list, force_create=True, context=context)
        self.message_subscribe(cr, uid, ids, partner_ids, context=context)
        return super(task, self).message_update(cr, uid, ids, msg, update_vals=update_vals, context=context)

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        recipients = super(task, self).message_get_suggested_recipients(cr, uid, ids, context=context)
        for data in self.browse(cr, uid, ids, context=context):
            if data.partner_id:
                reason = _('Customer Email') if data.partner_id.email else _('Customer')
                data._message_add_suggested_recipient(recipients, partner=data.partner_id, reason=reason)
        return recipients


class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'
    _columns = {
        'use_tasks': fields.boolean('Tasks', help="Check this box to manage internal activities through this project"),
        'company_uom_id': fields.related('company_id', 'project_time_mode_id', string="Company UOM", type='many2one', relation='product.uom'),
    }

    def on_change_template(self, cr, uid, ids, template_id, date_start=False, context=None):
        res = super(account_analytic_account, self).on_change_template(cr, uid, ids, template_id, date_start=date_start, context=context)
        if template_id and 'value' in res:
            template = self.browse(cr, uid, template_id, context=context)
            res['value']['use_tasks'] = template.use_tasks
        return res

    def _trigger_project_creation(self, cr, uid, vals, context=None):
        '''
        This function is used to decide if a project needs to be automatically created or not when an analytic account is created. It returns True if it needs to be so, False otherwise.
        '''
        if context is None: context = {}
        return vals.get('use_tasks') and not 'project_creation_in_progress' in context

    @api.cr_uid_id_context
    def project_create(self, cr, uid, analytic_account_id, vals, context=None):
        '''
        This function is called at the time of analytic account creation and is used to create a project automatically linked to it if the conditions are meet.
        '''
        project_pool = self.pool.get('project.project')
        project_id = project_pool.search(cr, uid, [('analytic_account_id','=', analytic_account_id)])
        if not project_id and self._trigger_project_creation(cr, uid, vals, context=context):
            project_values = {
                'name': vals.get('name'),
                'analytic_account_id': analytic_account_id,
                'use_tasks': True,
            }
            return project_pool.create(cr, uid, project_values, context=context)
        return False

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if vals.get('child_ids', False) and context.get('analytic_project_copy', False):
            vals['child_ids'] = []
        analytic_account_id = super(account_analytic_account, self).create(cr, uid, vals, context=context)
        self.project_create(cr, uid, analytic_account_id, vals, context=context)
        return analytic_account_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        vals_for_project = vals.copy()
        for account in self.browse(cr, uid, ids, context=context):
            if not vals.get('name'):
                vals_for_project['name'] = account.name
            self.project_create(cr, uid, account.id, vals_for_project, context=context)
        return super(account_analytic_account, self).write(cr, uid, ids, vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        proj_ids = self.pool['project.project'].search(cr, uid, [('analytic_account_id', 'in', ids)])
        has_tasks = self.pool['project.task'].search(cr, uid, [('project_id', 'in', proj_ids)], count=True, context=context)
        if has_tasks:
            raise UserError(_('Please remove existing tasks in the project linked to the accounts you want to delete.'))
        return super(account_analytic_account, self).unlink(cr, uid, ids, context=context)

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if args is None:
            args = []
        if context is None:
            context={}
        if context.get('current_model') == 'project.project':
            project_ids = self.search(cr, uid, args + [('name', operator, name)], limit=limit, context=context)
            return self.name_get(cr, uid, project_ids, context=context)

        return super(account_analytic_account, self).name_search(cr, uid, name, args=args, operator=operator, context=context, limit=limit)


class project_project(osv.osv):
    _inherit = 'project.project'
    _defaults = {
        'use_tasks': True
    }

class project_task_history(osv.osv):
    """
    Tasks History, used for cumulative flow charts (Lean/Agile)
    """
    _name = 'project.task.history'
    _description = 'History of Tasks'
    _rec_name = 'task_id'
    _log_access = False

    def _get_date(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for history in self.browse(cr, uid, ids, context=context):
            if history.type_id and history.type_id.fold:
                result[history.id] = history.date
                continue
            cr.execute('''select
                    date
                from
                    project_task_history
                where
                    task_id=%s and
                    id>%s
                order by id limit 1''', (history.task_id.id, history.id))
            res = cr.fetchone()
            result[history.id] = res and res[0] or False
        return result

    def _get_related_date(self, cr, uid, ids, context=None):
        result = []
        for history in self.browse(cr, uid, ids, context=context):
            cr.execute('''select
                    id
                from
                    project_task_history
                where
                    task_id=%s and
                    id<%s
                order by id desc limit 1''', (history.task_id.id, history.id))
            res = cr.fetchone()
            if res:
                result.append(res[0])
        return result

    _columns = {
        'task_id': fields.many2one('project.task', 'Task', ondelete='cascade', required=True, select=True),
        'type_id': fields.many2one('project.task.type', 'Stage'),
        'kanban_state': fields.selection([('normal', 'Normal'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')], 'Kanban State', required=False),
        'date': fields.date('Date', select=True),
        'end_date': fields.function(_get_date, string='End Date', type="date", store={
            'project.task.history': (_get_related_date, None, 20)
        }),
        'remaining_hours': fields.float('Remaining Time', digits=(16, 2)),
        'planned_hours': fields.float('Planned Time', digits=(16, 2)),
        'user_id': fields.many2one('res.users', 'Responsible'),
    }
    _defaults = {
        'date': fields.date.context_today,
    }

class project_task_history_cumulative(osv.osv):
    _name = 'project.task.history.cumulative'
    _table = 'project_task_history_cumulative'
    _inherit = 'project.task.history'
    _auto = False

    _columns = {
        'end_date': fields.date('End Date'),
        'nbr_tasks': fields.integer('# of Tasks', readonly=True),
        'project_id': fields.many2one('project.project', 'Project'),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'project_task_history_cumulative')

        cr.execute(""" CREATE VIEW project_task_history_cumulative AS (
            SELECT
                history.date::varchar||'-'||history.history_id::varchar AS id,
                history.date AS end_date,
                *
            FROM (
                SELECT
                    h.id AS history_id,
                    h.date+generate_series(0, CAST((coalesce(h.end_date, DATE 'tomorrow')::date - h.date) AS integer)-1) AS date,
                    h.task_id, h.type_id, h.user_id, h.kanban_state,
                    count(h.task_id) as nbr_tasks,
                    greatest(h.remaining_hours, 1) AS remaining_hours, greatest(h.planned_hours, 1) AS planned_hours,
                    t.project_id
                FROM
                    project_task_history AS h
                    JOIN project_task AS t ON (h.task_id = t.id)
                GROUP BY
                  h.id,
                  h.task_id,
                  t.project_id

            ) AS history
        )
        """)

class project_tags(osv.Model):
    """ Tags of project's tasks (or issues) """
    _name = "project.tags"
    _description = "Tags of project's tasks, issues..."
    _columns = {
        'name': fields.char('Name', required=True),
        'color': fields.integer('Color Index'),
    }
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
