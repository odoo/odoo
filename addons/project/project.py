# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import calendar
from datetime import datetime, date
from dateutil import relativedelta
from lxml import etree
import json
import time

from openerp import tools
from openerp.addons.resource.faces import task as Task

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning
import openerp.addons.decimal_precision as dp

class project_task_type(models.Model):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence'

    def _get_default_project_ids(self):
        project = self.env['project.task']._get_default_project_id()
        if project:
            return project
        return None

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text()
    sequence = fields.Integer(default=1)
    case_default = fields.Boolean(string='Default for New Projects',
                    help="If you check this field, this stage will be proposed by default on each new project. It will not assign this stage to existing projects.")
    project_ids = fields.Many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', string='Projects', default=_get_default_project_ids)
    legend_priority = fields.Text(
        'Priority Management Explanation', translate=True,
        help='Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.')
    legend_blocked = fields.Char(
        'Kanban Blocked Explanation', translate=True,
        help='Override the default value displayed for the blocked state for kanban selection, when the task or issue is in that stage.')
    legend_done = fields.Char(
        'Kanban Valid Explanation', translate=True,
        help='Override the default value displayed for the done state for kanban selection, when the task or issue is in that stage.')
    legend_normal = fields.Char(
        'Kanban Ongoing Explanation', translate=True,
        help='Override the default value displayed for the normal state for kanban selection, when the task or issue is in that stage.')
    fold = fields.Boolean(string='Folded in Kanban View',
                           help='This stage is folded in the kanban view when'
                           'there are no records in that stage to display.')

class project(models.Model):
    _name = "project.project"
    _description = "Project"
    _inherits = {'account.analytic.account': "analytic_account_id",
                 "mail.alias": "alias_id"}
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _period_number = 5

    @api.v7
    def _auto_init(self, cr, context=None):
        """ Installation hook: aliases, project.project """
        # create aliases for all projects and avoid constraint errors
        alias_context = dict(context, alias_model_name='project.task')
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(project, self)._auto_init,
            'project.task', self._columns['alias_id'], 'id', alias_prefix='project+', alias_defaults={'project_id':'id'}, context=alias_context)

    @api.onchange('partner_id')
    def onchange_partner_id(self, part=False):
        partner_obj = self.env['res.partner']
        val = {}
        if not part:
            return {'value': val}
        if 'pricelist_id' in self.fields_get():
            pricelist = partner_obj.read(part, ['property_product_pricelist'])
            pricelist_id = pricelist.get('property_product_pricelist') and pricelist.get('property_product_pricelist')[0]
            val['pricelist_id'] = pricelist_id
        return {'value': val}

    @api.multi
    def unlink(self):
        alias_ids = []
        analytic_account_to_delete = []
        for proj in self:
            if proj.tasks:
                raise Warning(_('Invalid Action!'),
                                     _('You cannot delete a project containing tasks. You can either delete all the project\'s tasks and then delete the project or simply deactivate the project.'))
            elif proj.alias_id:
                alias_ids.append(proj.alias_id)
            if proj.analytic_account_id and not proj.analytic_account_id.line_ids:
                analytic_account_to_delete.append(proj.analytic_account_id)
        res = super(project, self).unlink()
        [alias_id.unlink() for alias_id in alias_ids]
        [analytic_account_delete.unlink() for analytic_account_delete in analytic_account_to_delete]
        return res

    def _get_attached_docs(self):
        attachment = self.env['ir.attachment']
        task = self.env['project.task']
        for rec in self:
            project_attachments = attachment.search_count([('res_model', '=', 'project.project'), ('res_id', '=', rec.id)])
            task_ids = task.search([('project_id', '=', rec.id)])
            task_attachments = attachment.search_count([('res_model', '=', 'project.task'), ('res_id', 'in', task_ids.ids)])
            rec.doc_count = project_attachments + task_attachments

    def _task_count(self):
        for tasks in self:
            tasks.task_count = len(tasks.task_ids)

    @api.model
    def _get_alias_models(self):
        """ Overriden in project_issue to offer more options """
        return [('project.task', "Tasks")]

    @api.model
    def _get_visibility_selection(self):
        """ Overriden in portal_project to offer more options """
        return [('public', _('Public project')),
                ('employees', _('Internal project: all employees can access')),
                ('followers', _('Private project: followers Only'))]

    @api.multi
    def attachment_tree_view(self):
        task_ids = self.env['project.task'].search([('project_id', 'in', self.ids)])
        domain = [
             '|',
             '&', ('res_model', '=', 'project.project'), ('res_id', 'in', self.ids),
             '&', ('res_model', '=', 'project.task'), ('res_id', 'in', task_ids.ids)]
        res_id = self.ids and self.ids[0]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, res_id)
        }

    @api.model
    def __get_bar_values(self, obj, domain, read_fields, value_field, groupby_field):
        """ Generic method to generate data for bar chart values using SparklineBarWidget.
            This method performs obj.read_group(cr, uid, domain, read_fields, groupby_field).

            :param obj: the target model (i.e. crm_lead)
            :param domain: the domain applied to the read_group
            :param list read_fields: the list of fields to read in the read_group
            :param str value_field: the field used to compute the value of the bar slice
            :param str groupby_field: the fields used to group

            :return list section_result: a list of dicts: [
                                                {   'value': (int) bar_column_value,
                                                    'tootip': (str) bar_column_tooltip,
                                                }
                                            ]
        """
        month_begin = date.today().replace(day=1)
        section_result = [{
                          'value': 0,
                          'tooltip': (month_begin + relativedelta.relativedelta(months=-i)).strftime('%B'),
                          } for i in range(self._period_number - 1, -1, -1)]
        group_obj = obj.read_group(domain, read_fields, groupby_field)
        pattern = tools.DEFAULT_SERVER_DATE_FORMAT if obj.fields_get(groupby_field)[groupby_field]['type'] == 'date' else tools.DEFAULT_SERVER_DATETIME_FORMAT
        for group in group_obj:
            group_begin_date = datetime.strptime(group['__domain'][0][2], pattern)
            month_delta = relativedelta.relativedelta(month_begin, group_begin_date)
            section_result[self._period_number - (month_delta.months + 1)] = {'value': group.get(value_field, 0), 'tooltip': group.get(groupby_field, 0)}
        return section_result

    def _get_project_task_data(self):
        obj = self.env['project.task']
        month_begin = date.today().replace(day=1)
        date_begin = (month_begin - relativedelta.relativedelta(months=self._period_number - 1)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        date_end = month_begin.replace(day=calendar.monthrange(month_begin.year, month_begin.month)[1]).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        for rec in self:
            created_domain = [('project_id', '=', rec.id), ('create_date', '>=', date_begin), ('create_date', '<=', date_end), ('stage_id.fold', '=', False)]
            rec.monthly_tasks = json.dumps(self.__get_bar_values(obj, created_domain, ['create_date'], 'create_date_count', 'create_date'))

    def _get_type_common(self):
        return self.env['project.task.type'].search([('case_default', '=', True)])

    # Lambda indirection method to avoid passing a copy of the overridable method when declaring the field
    _alias_models = lambda self, *args, **kwargs: self._get_alias_models(*args, **kwargs)
    _visibility_selection = lambda self, *args, **kwargs: self._get_visibility_selection(*args, **kwargs)

    active = fields.Boolean(help="If the active field is set to False, it will allow you to hide the project without removing it.", default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of Projects.", default=10)
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Contract/Analytic',
        help="Link this project to an analytic account if you need financial management on projects. "
             "It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc.",
        ondelete="cascade", required=True, auto_join=True)
    label_tasks = fields.Char('Use Tasks as', help="Gives label to tasks on project's kanaban view.", default='Tasks')
    members = fields.Many2many('res.users', 'project_user_rel', 'project_id', 'uid', string='Project Members',
        help="Project's members are users who can have an access to the tasks related to this project.", states={'close': [('readonly', True)], 'cancelled': [('readonly', True)]})
    tasks = fields.One2many('project.task', 'project_id', string="Task Activities")
    resource_calendar_id = fields.Many2one('resource.calendar', string='Working Time', help="Timetable working hours to adjust the gantt diagram report", states={'close': [('readonly', True)]})
    type_ids = fields.Many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', string='Tasks Stages', states={'close': [('readonly', True)], 'cancelled': [('readonly', True)]}, default=_get_type_common)
    task_count = fields.Integer(compute='_task_count', string="Tasks",)
    task_ids = fields.One2many('project.task', 'project_id',
                                domain=[('stage_id.fold', '=', False)])
    color = fields.Integer(string='Color Index')
    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True,
                                help="Internal email associated with this project. Incoming emails are automatically synchronized"
                                     "with Tasks (or optionally Issues if the Issue Tracker module is installed).")
    alias_model = fields.Selection(_alias_models, string="Alias Model", index=True, required=True,
                                    help="The kind of document created when an email is received on this project's email alias", default='project.task')
    privacy_visibility = fields.Selection(_visibility_selection, string='Privacy / Visibility', required=True,
        help="Holds visibility of the tasks or issues that belong to the current project:\n"
                "- Public: everybody sees everything; if portal is activated, portal users\n"
                "   see all tasks or issues; if anonymous portal is activated, visitors\n"
                "   see all tasks or issues\n"
                "- Portal (only available if Portal is installed): employees see everything;\n"
                "   if portal is activated, portal users see the tasks or issues followed by\n"
                "   them or by someone of their company\n"
                "- Employees Only: employees see all tasks or issues\n"
                "- Followers Only: employees see only the followed tasks or issues; if portal\n"
                "   is activated, portal users see the followed tasks or issues.", default='employees')
    state = fields.Selection([('template', 'Template'),
                               ('draft','New'),
                               ('open','In Progress'),
                               ('cancelled', 'Cancelled'),
                               ('pending','Pending'),
                               ('done','Done')],
                              string='Status', required=True, copy=False, default='open')
    monthly_tasks = fields.Char(compute='_get_project_task_data', readonly=True,
                                         string='Project Task By Month')
    doc_count = fields.Integer(compute='_get_attached_docs', string="Number of documents attached")

    _order = "sequence, id"

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(project, self).message_get_suggested_recipients()
        for data in self:
            if data.partner_id:
                reason = _('Customer Email') if data.partner_id.email else _('Customer')
                self._message_add_suggested_recipient(recipients, data, partner=data.partner_id, reason='%s' % reason)
        return recipients

    # TODO: Why not using a SQL contraints ?
    @api.constrains('date_start', 'date')
    def _check_dates(self):
        for leave in self.read(['date_start', 'date']):
            if leave['date_start'] and leave['date']:
                if leave['date_start'] > leave['date']:
                    raise Warning(_('Error!'), _('project start-date must be lower then project end-date.'))

    @api.multi
    def set_template(self):
        return self.setActive(value=False)

    @api.multi
    def reset_project(self):
        return self.setActive(value=True)

    @api.model
    def map_tasks(self, old_project_id):
        """ copy and map tasks from old to new project """
        map_task_id = {}
        task_obj = self.env['project.task']
        proj = self.browse(old_project_id)
        for task in proj.tasks:
            # preserve task name and stage, normally altered during copy
            defaults = {'stage_id': task.stage_id.id,
                        'name': task.name + (_(' (copy)'))}
            map_task_id[task.id] = task.copy(defaults).id
        self.write({'tasks': [(6, 0, map_task_id.values())]})
        task_obj.duplicate_task(map_task_id)
        return True

    @api.one
    def copy(self, default=None):
        if default is None:
            default = {}
        default.update({'name': self.name + _(' (copy)')})
        res = super(project, self).copy(default)
        res.map_tasks(self.id)
        return res

    @api.multi
    def duplicate_template(self):
        data_obj = self.env['ir.model.data']
        result = []
        for proj in self:
            parent_id = self._context.get('parent_id')
            self.with_context(analytic_project_copy=True)
            new_date_start = time.strftime('%Y-%m-%d')
            new_date_end = False
            if proj.date_start and proj.date:
                start_date = date(*time.strptime(proj.date_start, '%Y-%m-%d')[:3])
                end_date = date(*time.strptime(proj.date, '%Y-%m-%d')[:3])
                new_date_end = (datetime(*time.strptime(new_date_start, '%Y-%m-%d')[:3])+(end_date-start_date)).strftime('%Y-%m-%d')
            self.with_context(copy=True)
            new_id = proj.copy(default={
                                    'name':_("%s (copy)") % (proj.name),
                                    'state':'open',
                                    'date_start':new_date_start,
                                    'date':new_date_end,
                                    'parent_id':parent_id})
            result.append(new_id)

            child_ids = self.search([('parent_id', '=', proj.analytic_account_id.id)])
            parent_id = new_id.read(['analytic_account_id'])['analytic_account_id'][0]
            if child_ids:
                self.with_context(parent_id=parent_id)
                child_ids.duplicate_template()

        if result and len(result):
            res_id = result[0]
            form_view_id = data_obj._get_id('project', 'edit_project')
            form_view = form_view_id.read(['res_id'])
            tree_view_id = data_obj._get_id('project', 'view_project')
            tree_view = tree_view_id.read(['res_id'])
            search_view_id = data_obj._get_id('project', 'view_project_project_filter')
            search_view = search_view_id.read(['res_id'])
            return {
                'name': _('Projects'),
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_model': 'project.project',
                'view_id': False,
                'res_id': res_id,
                'views': [(form_view['res_id'], 'form'), (tree_view['res_id'], 'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view['res_id'],
                'nodestroy': True
            }

    # set active value for a project, its sub projects and its tasks
    @api.multi
    def setActive(self, value=True):
        task_obj = self.env['project.task']
        for proj in self:
            proj.write({'state': value and 'open' or 'template'})
            val = (False if value else True)
            tasks_id = task_obj.search([('project_id', '=', proj.id), ('active', '=', val)])
            if tasks_id:
                tasks_id.write({'active': value})
            child_ids = self.search([('parent_id', '=', proj.analytic_account_id.id)])
            if child_ids:
                child_ids.setActive(value)
        return True

    @api.model
    def _schedule_header(self, ids, force_members=True):
        if type(ids) in (long, int,):
            ids = [ids]
        projects = self.browse(ids)

        for project in projects:
            if (not project.members) and force_members:
                raise Warning(_('Warning!'), _("You must assign members on the project '%s'!") % (project.name,))

        resource_pool = self.env['resource.resource']

        result = "from openerp.addons.resource.faces import *\n"
        result += "import datetime\n"
        for project in self.browse(ids):
            u_ids = [i.id for i in project.members]
            if project.user_id and (project.user_id.id not in u_ids):
                u_ids.append(project.user_id.id)
            for task in project.tasks:
                if task.user_id and (task.user_id.id not in u_ids):
                    u_ids.append(task.user_id.id)
            calendar_id = project.resource_calendar_id and project.resource_calendar_id.id or False
            resource_objs = resource_pool.generate_resources(u_ids, calendar_id)
            for key, vals in resource_objs.items():
                result += '''
class User_%s(Resource):
    efficiency = %s
''' % (key,  vals.get('efficiency'))

        result += '''
def Project():
        '''
        return result

    @api.model
    def _schedule_project(self, project):
        resource_pool = self.env['resource.resource']
        calendar_id = project.resource_calendar_id and project.resource_calendar_id.id
        working_days = resource_pool.compute_working_calendar(calendar_id)
        # TODO: check if we need working_..., default values are ok.
        puids = [x.id for x in project.members]
        if project.user_id:
            puids.append(project.user_id.id)
        result = """
  def Project_%d():
    start = \'%s\'
    working_days = %s
    resource = %s
""" % (
            project.id,
            project.date_start or time.strftime('%Y-%m-%d'), working_days,
            '|'.join(['User_'+str(x) for x in puids]) or 'None'
        )
        vacation = calendar_id and tuple(resource_pool.compute_vacation(calendar_id))
        if vacation:
            result += """
    vacation = %s
""" % (vacation, )
        return result

    #TODO: DO Resource allocation and compute availability
    @api.v7
    def compute_allocation(self, rc, uid, ids, start_date, end_date, context=None):
        if context ==  None:
            context = {}
        allocation = {}
        return allocation

    @api.model
    def schedule_tasks(self, ids):
        if type(ids) in (long, int,):
            ids = [ids]
        projects = self.browse(ids)
        result = self._schedule_header(ids, False)
        for project in projects:
            result += self._schedule_project(project)
            result += self.env['project.task']._generate_task(project.tasks, ident=4)

        local_dict = {}
        exec result in local_dict
        projects_gantt = Task.BalancedProject(local_dict['Project'])

        for project in projects:
            project_gantt = getattr(projects_gantt, 'Project_%d' % (project.id,))
            for task in project.tasks:
                if task.stage_id and task.stage_id.fold:
                    continue

                p = getattr(project_gantt, 'Task_%d' % (task.id,))

                task.write({
                    'date_start': p.start.strftime('%Y-%m-%d %H:%M:%S'),
                    'date_end': p.end.strftime('%Y-%m-%d %H:%M:%S')
                })
                if (not task.user_id) and (p.booked_resource):
                    task.write({
                        'user_id': int(p.booked_resource[0].name[5:]),
                    })
        return True

    @api.v7
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        # Prevent double project creation when 'use_tasks' is checked + alias management
        create_context = dict(context, project_creation_in_progress=True,
                              alias_model_name=vals.get('alias_model', 'project.task'),
                              alias_parent_model_name=self._name)

        if vals.get('type') not in ('template', 'contract'):
            vals['type'] = 'contract'

        ir_values = self.pool.get('ir.values').get_default(cr, uid, 'project.config.settings', 'generate_project_alias')
        if ir_values:
            vals['alias_name'] = vals.get('alias_name') or vals.get('name')
        project_id = super(project, self).create(cr, uid, vals, context=create_context)
        project_rec = self.browse(cr, uid, project_id, context=context)
        values = {'alias_parent_thread_id': project_id, 'alias_defaults': {'project_id': project_id}}
        self.pool.get('mail.alias').write(cr, uid, [project_rec.alias_id.id], values, context=context)
        return project_id

    @api.multi
    def write(self, vals):
        # if alias_model has been changed, update alias_model_id accordingly
        if vals.get('alias_model'):
            model_ids = self.env['ir.model'].search([('model', '=', vals.get('alias_model', 'project.task'))])
            vals.update(alias_model_id=model_ids[0])
        return super(project, self).write(vals)

class task(models.Model):
    _name = "project.task"
    _description = "Task"
    _date_name = "date_start"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _mail_post_access = 'read'
    _track = {
        'stage_id': {
            # this is only an heuristics; depending on your particular stage configuration it may not match all 'new' stages
            'project.mt_task_new': lambda self, cr, uid, obj, ctx=None: obj.stage_id and obj.stage_id.sequence <= 1,
            'project.mt_task_stage': lambda self, cr, uid, obj, ctx=None: obj.stage_id.sequence > 1,
        },
        'user_id': {
            'project.mt_task_assigned': lambda self, cr, uid, obj, ctx=None: obj.user_id and obj.user_id.id,
        },
        'kanban_state': {
            'project.mt_task_blocked': lambda self, cr, uid, obj, ctx=None: obj.kanban_state == 'blocked',
            'project.mt_task_ready': lambda self, cr, uid, obj, ctx=None: obj.kanban_state == 'done',
        },
    }

    def _get_default_partner(self):
        project_id = self._get_default_project_id()
        if project_id:
            project = self.env['project.project'].browse(project_id)
            if project and project.partner_id:
                return project.partner_id.id
        return False

    def _get_default_project_id(self):
        """ Gives default section by checking if present in the context """
        return (self._context.get('default_project_id'))

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        project_id = self._get_default_project_id()
        return self.stage_find([], project_id, [('fold', '=', False)])

    @api.v7
    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        stage_obj = self.pool.get('project.task.type')
        order = stage_obj._order
        access_rights_uid = access_rights_uid or uid
        if read_group_order == 'stage_id desc':
            order = '%s desc' % order
        search_domain = []
        project_id = context.get('default_project_id')
        if project_id:
            search_domain += ['|', ('project_ids', '=', project_id), ('id', 'in', ids)]
        else:
            search_domain += ['|', ('id', 'in', ids), ('case_default', '=', True)]
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold
        return result, fold

    @api.v7
    def _read_group_user_id(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        res_users = self.pool.get('res.users')
        project_id = context.get('default_project_id')
        access_rights_uid = access_rights_uid or uid
        if project_id:
            ids += self.pool.get('project.project').read(cr, access_rights_uid, project_id, ['members'], context=context)['members']
            order = res_users._order
            # lame way to allow reverting search, should just work in the trivial case
            if read_group_order == 'user_id desc':
                order = '%s desc' % order
            # de-duplicate and apply search order
            ids = res_users._search(cr, uid, [('id', 'in', ids)], order=order, access_rights_uid=access_rights_uid, context=context)
        result = res_users.name_get(cr, access_rights_uid, ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(ids.index(x[0]), ids.index(y[0])))
        return result, {}

    _group_by_full = {
        'stage_id': _read_group_stage_ids,
        'user_id': _read_group_user_id,
    }

    @api.onchange('remaining_hours', 'planned_hours')
    def onchange_remaining(self):
        if self.remaining_hours and not self.planned_hours:
            return {'value': {'planned_hours': self.remaining_hours}}
        return {}

    @api.onchange('planned_hours')
    def onchange_planned(self):
        planned = self['planned_hours'] or 0.0
        if 'effective_hours' in dir(self):
            effective = self['effective_hours']
        else:
            effective = 0.0
        return {'value': {'remaining_hours': planned - effective}}

    @api.onchange('project_id')
    def onchange_project(self):
        if self.project_id:
            project = self.env['project.project'].browse(self.project_id.id)
            if project and project.partner_id:
                return {'value': {'partner_id': project.partner_id.id}}
        return {}

    @api.onchange('user_id')
    def onchange_user_id(self):
        vals = {}
        if self.user_id:
            vals['date_start'] = fields.datetime.now()
        return {'value': vals}

    @api.model
    def duplicate_task(self, map_ids):
        mapper = lambda t: map_ids.get(t.id, t.id)
        for task in self.browse(map_ids.values()):
            new_child_ids = set(map(mapper, task.child_ids))
            new_parent_ids = set(map(mapper, task.parent_ids))
            if new_child_ids or new_parent_ids:
                task.write({'parent_ids': [(6, 0, list(new_parent_ids))],
                            'child_ids':  [(6, 0, list(new_child_ids))]})

    @api.one
    def copy_data(self, default=None):
        if not default.get('name'):
            default['name'] = _("%s (copy)") % self.name
        return super(task, self).copy_data(default)

    def _is_template(self):
        for task in self:
            task.active = True
            if task.project_id:
                if task.project_id.active is False or task.project_id.state == 'template':
                    task.active = False

    active = fields.Boolean(compute='_is_template', store=True, string='Not a Template Task', help="This field is computed automatically and have the same behavior than the boolean 'active' field: if the task is linked to a template or unactivated project, it will be hidden unless specifically asked.", default=True)
    name = fields.Char(string='Task Summary', track_visibility='onchange', required=True, index=True)
    description = fields.Html()
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], index=True, default='0')
    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of tasks.", default=10)
    stage_id = fields.Many2one('project.task.type', string='Stage', track_visibility='onchange', index=True,
                    domain="[('project_ids', '=', project_id)]", copy=False, default=_get_default_stage_id)
    tag_ids = fields.Many2many('project.tags', string='Tags')
    kanban_state = fields.Selection([('normal', 'In Progress'),('done', 'Ready for next stage'),('blocked', 'Blocked')], string='Kanban State',
                                     track_visibility='onchange',
                                     help="A task's kanban state indicates special situations affecting it:\n"
                                          " * Normal is the default situation\n"
                                          " * Blocked indicates something is preventing the progress of this task\n"
                                          " * Ready for next stage indicates the task is ready to be pulled to the next stage",
                                     required=False, copy=False, default='normal')
    create_date = fields.Datetime(string='Create Date', readonly=True, index=True)
    write_date = fields.Datetime(string='Last Modification Date', readonly=True, index=True)#not displayed in the view but it might be useful with base_action_rule module (and it needs to be defined first for that)
    date_start = fields.Datetime(string='Starting Date', index=True, copy=False, default=fields.Datetime.now)
    date_end = fields.Datetime(string='Ending Date', index=True, copy=False)
    date_deadline = fields.Date(string='Deadline', index=True, copy=False)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', index=True, copy=False, default=fields.Datetime.now)
    project_id = fields.Many2one('project.project', string='Project', ondelete='set null', index=True, track_visibility='onchange', change_default=True, default=_get_default_project_id)
    parent_ids = fields.Many2many('project.task', 'project_task_parent_rel', 'task_id', 'parent_id', string='Parent Tasks')
    child_ids = fields.Many2many('project.task', 'project_task_parent_rel', 'parent_id', 'task_id', string='Delegated Tasks')
    notes = fields.Text()
    planned_hours = fields.Float(string='Initially Planned Hours', help='Estimated time to do the task, usually set by the project manager when the task is in draft state.')
    remaining_hours = fields.Float(string='Remaining Hours', digits_compute=dp.get_precision('Product Price'), help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    user_id = fields.Many2one('res.users', string='Assigned to', index=True, track_visibility='onchange', default=lambda self: self._uid)
    delegated_user_id = fields.Many2one(related='child_ids.user_id', comodel_name='res.users', string='Delegated To')
    partner_id = fields.Many2one('res.partner', string='Customer', default=lambda self: self._get_default_partner())
    manager_id = fields.Many2one(related='project_id.analytic_account_id.user_id', comodel_name='res.users', string='Project Manager')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('project.task'))
    id = fields.Integer(string='ID', readonly=True)
    color = fields.Integer(string='Color Index')
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True)

    _order = "priority desc, sequence, date_start, name, id"

    @api.constrains('parent_ids')
    def _check_recursion(self):
        for id in self:
            visited_branch = set()
            visited_node = set()
            res = self._check_cycle(id, visited_branch, visited_node)
            if not res:
                raise Warning(_('Error ! \n  You cannot create recursive tasks'))

    @api.model
    def _check_cycle(self, id, visited_branch, visited_node):
        if id.id in visited_branch: #Cycle
            return False
        if id.id in visited_node: #Already tested don't work one more time for nothing
            return True

        visited_branch.add(id.id)
        visited_node.add(id.id)

        #visit child using DFS
        task = self.browse(id.id)
        for child in task.child_ids:
            res = self._check_cycle(child.id, visited_branch, visited_node)
            if not res:
                return False

        visited_branch.remove(id.id)
        return True

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        obj_task = self
        start = obj_task.date_start
        end = obj_task.date_end
        if start and end:
            if start > end:
                raise Warning(_('Error ! \n Task end-date must be greater then task start-date'))

    # Override view according to the company definition
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # read uom as admin to avoid access rights issues, e.g. for portal/share users,
        # this should be safe (no context passed to avoid side-effects)
        obj_tm = self.env['res.users'].sudo().browse(self._uid).company_id.project_time_mode_id
        tm = obj_tm and obj_tm.name or 'Hours'
        res = super(task, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if tm in ['Hours', 'Hour']:
            return res

        eview = etree.fromstring(res['arch'])

        def _check_rec(eview):
            if eview.attrib.get('widget', '') == 'float_time':
                eview.set('widget', 'float')
            for child in eview:
                _check_rec(child)
            return True

        _check_rec(eview)

        res['arch'] = etree.tostring(eview)

        for f in res['fields']:
            if 'Hours' in res['fields'][f]['string']:
                res['fields'][f]['string'] = res['fields'][f]['string'].replace('Hours', tm)
        return res

    @api.model
    def get_empty_list_help(self, help):
        context = dict(self._context or {})
        context['empty_list_help_id'] = context.get('default_project_id')
        context['empty_list_help_model'] = 'project.project'
        context['empty_list_help_document_name'] = _("tasks")
        self.with_context(context)
        return super(task, self).get_empty_list_help(help)

    # ----------------------------------------
    # Case management
    # ----------------------------------------

    @api.model
    def stage_find(self, cases, section_id, domain=[], order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        if isinstance(cases, (int, long)):
            cases = self
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
        stage_ids = self.env['project.task.type'].search(search_domain, order=order)
        if stage_ids:
            return stage_ids[0]
        return False

    @api.multi
    def _check_child_task(self):
        tasks = self
        for task in tasks:
            if task.child_ids:
                for child in task.child_ids:
                    if child.stage_id and not child.stage_id.fold:
                        raise Warning(_("Warning!"), _("Child task still open.\nPlease cancel or complete child task first."))
        return True

    @api.multi
    def _delegate_task_attachments(self, delegated_task_id):
        attachment = self.env['ir.attachment']
        attachment_ids = attachment.search([('res_model', '=', self._name), ('res_id', '=', self.id)])
        new_attachment_ids = []
        for attachment_id in attachment_ids:
            new_attachment_ids.append(attachment.copy(attachment_id, default={'res_id': delegated_task_id}))
        return new_attachment_ids

    @api.returns('self')
    def _get_effective_hours(self):
        # this method is override in project_timesheet modules.
        return 0.0

    @api.multi
    def do_delegate(self, delegate_data=None):
        """
        Delegate Task to another users.
        """
        if delegate_data is None:
            delegate_data = {}
        assert delegate_data['user_id'], _("Delegated User should be specified")
        delegated_tasks = {}
        for task in self:
            delegated_task_id = task.copy({
                'name': delegate_data['name'],
                'project_id': delegate_data['project_id'] and delegate_data['project_id'][0],
                'stage_id': delegate_data.get('stage_id') and delegate_data.get('stage_id')[0],
                'user_id': delegate_data['user_id'] and delegate_data['user_id'][0],
                'planned_hours': delegate_data['planned_hours'] or 0.0,
                'parent_ids': [(6, 0, [task.id])],
                'description': delegate_data['new_task_description'] or '',
                'child_ids': [],
            })
            task._delegate_task_attachments(delegated_task_id)
            newname = delegate_data['prefix'] or ''
            task.write({
                'remaining_hours': delegate_data['planned_hours_me'],
                'planned_hours': delegate_data['planned_hours_me'] + task._get_effective_hours(),
                'name': newname,
            })
            delegated_tasks[task.id] = delegated_task_id
        return delegated_tasks

    @api.multi
    def _store_history(self):
        for task in self:
            self.env['project.task.history'].create({
                'task_id': task.id,
                'remaining_hours': task.remaining_hours,
                'planned_hours': task.planned_hours,
                'kanban_state': task.kanban_state,
                'type_id': task.stage_id.id,
                'user_id': task.user_id.id

            })
        return True

    # ------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------
    @api.model
    def create(self, vals):
        # for default stage
        if type(vals) == list:
            vals = vals[0][0]
        if vals.get('project_id') and not self._context.get('default_project_id'):
            self.with_context(default_project_id=vals.get('project_id'))
        # user_id change: update date_start
        if vals.get('user_id') and not vals.get('date_start'):
            vals['date_start'] = fields.datetime.now()

        # context: no_log, because subtype already handle this
        self.with_context(mail_create_nolog=True)
        task_id = super(task, self).create(vals)
        task_id._store_history()
        return task_id

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.datetime.now()
        # user_id change: update date_start
        if vals.get('user_id') and 'date_start' not in vals:
            vals['date_start'] = fields.datetime.now()

        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the task changes.
        if vals and not 'kanban_state' in vals and 'stage_id' in vals:
            new_stage = vals.get('stage_id')
            vals_reset_kstate = dict(vals, kanban_state='normal')
            for t in self:
                write_vals = vals_reset_kstate if t.stage_id.id != new_stage else vals
                super(task, self).write(write_vals)
            result = True
        else:
            result = super(task, self).write(vals)

        if any(item in vals for item in ['stage_id', 'remaining_hours', 'user_id', 'kanban_state']):
            self._store_history()
        return result

    @api.multi
    def unlink(self):
        self._check_child_task()
        res = super(task, self).unlink()
        return res

    @api.returns('self')
    def _get_total_hours(self):
        return self._get_effective_hours() + self.remaining_hours

    @api.model
    def _generate_task(self, tasks, ident=4):
        result = ""
        ident = ' '*ident
        for task in tasks:
            if task.stage_id and task.stage_id.fold:
                continue
            result += '''
%sdef Task_%s():
%s  todo = \"%.2fH\"
%s  effort = \"%.2fH\"''' % (ident, task.id, ident, task.remaining_hours, ident, task._get_total_hours())
            start = []
            for t2 in task.parent_ids:
                start.append("up.Task_%s.end" % (t2.id,))
            if start:
                result += '''
%s  start = max(%s)
''' % (ident, ', '.join(start))

            if task.user_id:
                result += '''
%s  resource = %s
''' % (ident, 'User_'+str(task.user_id.id))

        result += "\n"
        return result

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    @api.multi
    def message_get_reply_to(self):
        """ Override to get the reply_to of the parent project. """
        tasks = self
        project_ids = set([task.project_id.id for task in tasks if task.project_id])
        aliases = project_ids.message_get_reply_to()
        return dict((task.id, aliases.get(task.project_id and task.project_id.id or 0)) for task in tasks)

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Override to updates the document according to the email. """
        if custom_values is None:
            custom_values = {}
        defaults = {
            'name': msg.get('subject'),
            'planned_hours': 0.0,
        }
        defaults.update(custom_values)
        res = super(task, self).message_new(msg, custom_values=defaults)
        email_list = tools.email_split(msg.get('to', '') + ',' + msg.get('cc', ''))
        new_task = res.browse()
        if new_task.project_id and new_task.project_id.alias_name:  # check left-part is not already an alias
            email_list = filter(lambda x: x.split('@')[0] != new_task.project_id.alias_name, email_list)
        partner_ids = filter(lambda x: x, self._find_partner_from_emails(None, email_list, check_followers=False))
        res.message_subscribe(partner_ids)
        return res

    @api.model
    def message_update(self, ids, msg, update_vals=None):
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
        return super(task, self).message_update(ids, msg, update_vals=update_vals)

class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    use_tasks = fields.Boolean(string='Tasks', help="If checked, this contract will be available in the project menu and you will be able to manage tasks or track issues", default=True)
    company_uom_id = fields.Many2one(related='company_id.project_time_mode_id', string="Company UOM", comodel_name='product.uom')

    @api.onchange('template_id')
    def on_change_template(self, template_id, date_start=False):
        res = super(account_analytic_account, self).on_change_template(template_id, date_start=date_start)
        if template_id and 'value' in res:
            template = self.browse(template_id)
            res['value']['use_tasks'] = template.use_tasks
        return res

    @api.model
    def _trigger_project_creation(self, vals):
        '''
        This function is used to decide if a project needs to be automatically created or not when an analytic account is created. It returns True if it needs to be so, False otherwise.
        '''
        return vals.get('use_tasks') and not 'project_creation_in_progress' in self._context

    @api.model
    def project_create(self, analytic_account_id, vals):
        '''
        This function is called at the time of analytic account creation and is used to create a project automatically linked to it if the conditions are meet.
        '''
        project_pool = self.env['project.project']
        project_id = project_pool.search([('analytic_account_id', '=', analytic_account_id if isinstance(analytic_account_id, (int)) else analytic_account_id.id)])
        if not project_id and self._trigger_project_creation(vals):
            project_values = {
                'name': vals.get('name'),
                'analytic_account_id': analytic_account_id,
                'type': vals.get('type', 'contract'),
            }
            return project_pool.create(project_values)
        return False

    @api.model
    def create(self, vals):
        if vals.get('child_ids') and self._context.get('analytic_project_copy'):
            vals['child_ids'] = []
        analytic_account_id = super(account_analytic_account, self).create(vals)
        self.project_create(analytic_account_id, vals)
        return analytic_account_id

    @api.multi
    def write(self, vals):
        vals_for_project = vals.copy()
        for account in self:
            if not vals.get('name'):
                vals_for_project['name'] = account.name
            if not vals.get('type'):
                vals_for_project['type'] = account.type
            self.project_create(account.id, vals_for_project)
        return super(account_analytic_account, self).write(vals)

    @api.multi
    def unlink(self):
        proj_ids = self.env['project.project'].search([('analytic_account_id', 'in', self.ids)])
        if proj_ids:
            has_tasks = self.evn['project.task'].search([('project_id', 'in', [ids for ids in proj_ids])], count=True)
            if has_tasks:
                raise Warning(_('Warning!'), _('Please remove existing tasks in the project linked to the accounts you want to delete.'))
        return super(account_analytic_account, self).unlink()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if self._context.get('current_model') == 'project.project':
            project_ids = self.search(args + [('name', operator, name)], limit=limit)
            return project_ids.name_get()
        return super(account_analytic_account, self).name_search(name, args=args, operator=operator, limit=limit)

class project_task_history(models.Model):
    """
    Tasks History, used for cumulative flow charts (Lean/Agile)
    """
    _name = 'project.task.history'
    _description = 'History of Tasks'
    _rec_name = 'task_id'
    _log_access = False

    @api.one
    @api.depends('task_id')
    def _get_date(self):
        res = False
        if self.type_id and self.type_id.fold:
            self.end_date = self.date
        if self.task_id:
            self.env.cr.execute('''select
                date
                from
                    project_task_history
                where
                    task_id=%s and
                    id>%s
                order by id limit 1''', (self.task_id.id, self.id))
            res = self.env.cr.fetchone()
        self.end_date = res and res[0]

    task_id = fields.Many2one('project.task', string='Task', ondelete='cascade', required=True, index=True)
    type_id = fields.Many2one('project.task.type', string='Stage')
    kanban_state = fields.Selection([('normal', 'Normal'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')], string='Kanban State', required=False)
    date = fields.Date(index=True, default=date.today())
    end_date = fields.Date(string='End Date', compute="_get_date", store=True)
    remaining_hours = fields.Float(string='Remaining Time', digits_compute=dp.get_precision('Product Price'))
    planned_hours = fields.Float(string='Planned Time', digits_compute=dp.get_precision('Product Price'))
    user_id = fields.Many2one('res.users', string='Responsible')

class project_task_history_cumulative(models.Model):
    _name = 'project.task.history.cumulative'
    _table = 'project_task_history_cumulative'
    _inherit = 'project.task.history'
    _auto = False

    end_date = fields.Date(string='End Date')
    nbr_tasks = fields.Integer(string='# of Tasks', readonly=True)
    project_id = fields.Many2one('project.project', string='Project')

    @api.v7
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

class project_tags(models.Model):
    """ Category of project's task (or issue) """
    _name = "project.tags"
    _description = "Category of project's task, issue, ..."

    name = fields.Char(required=True, translate=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
