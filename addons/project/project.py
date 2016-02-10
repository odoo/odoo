# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, date
import time

from lxml import etree

from odoo import api, fields, models, tools, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError


class ProjectTaskType(models.Model):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence'

    def _get_mail_template_id_domain(self):
        return [('model', '=', 'project.task')]

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence', default=1)
    project_ids = fields.Many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', string='Projects', default=_get_default_project_ids)
    legend_priority = fields.Char(
        string='Priority Management Explanation', translate=True,
        help='Explanation text to help users using the star and priority mechanism on stages or issues that are in this stage.')
    legend_blocked = fields.Char(
        string='Kanban Blocked Explanation', translate=True,
        help='Override the default value displayed for the blocked state for kanban selection, when the task or issue is in that stage.')
    legend_done = fields.Char(
        string='Kanban Valid Explanation', translate=True,
        help='Override the default value displayed for the done state for kanban selection, when the task or issue is in that stage.')
    legend_normal = fields.Char(
        string='Kanban Ongoing Explanation', translate=True,
        help='Override the default value displayed for the normal state for kanban selection, when the task or issue is in that stage.')
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=lambda self: self._get_mail_template_id_domain(),
        help="If set an email will be sent to the customer when the task or issue reaches this step.")
    fold = fields.Boolean(string='Folded in Tasks Pipeline',
                           help='This stage is folded in the kanban view when '
                           'there are no records in that stage to display.')


class Project(models.Model):
    _name = "project.project"
    _description = "Project"
    _inherit = ['mail.alias.mixin', 'mail.thread', 'ir.needaction_mixin']
    _inherits = {'account.analytic.account': "analytic_account_id"}
    _order = "sequence, name, id"
    _period_number = 5

    def get_alias_model_name(self, vals):
        return vals.get('alias_model', 'project.task')

    def get_alias_values(self):
        values = super(Project, self).get_alias_values()
        values['alias_defaults'] = {'project_id': self.id}
        return values

    @api.model
    def _get_alias_models(self):
        """ Overriden in project_issue to offer more options """
        return [('project.task', "Tasks")]

    def _get_visibility_selection(self):
        """ Overriden in portal_project to offer more options """
        return [('portal', _('Customer Project: visible in portal if the customer is a follower')),
                ('employees', _('All Employees Project: all employees can access')),
                ('followers', _('Private Project: followers only'))]

    # Lambda indirection method to avoid passing a copy of the overridable method when declaring the field
    _alias_models = lambda self, *args, **kwargs: self._get_alias_models(*args, **kwargs)
    _visibility_selection = lambda self, *args, **kwargs: self._get_visibility_selection(*args, **kwargs)

    active = fields.Boolean(default=True, help="If the active field is set to False, it will allow you to hide the project without removing it.")
    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of Projects.")
    analytic_account_id = fields.Many2one(
        'account.analytic.account', string='Contract/Analytic',
        help="Link this project to an analytic account if you need financial management on projects. "
             "It enables you to connect projects with budgets, planning, cost and revenue analysis, timesheets on projects, etc.",
        ondelete="cascade", required=True, auto_join=True)
    label_tasks = fields.Char('Use Tasks as', default='Tasks', help="Gives label to tasks on project's kanban view.")
    tasks = fields.One2many('project.task', 'project_id', "Task Activities")
    resource_calendar_id = fields.Many2one('resource.calendar', 'Working Time', help="Timetable working hours to adjust the gantt diagram report", states={'close':[('readonly',True)]})
    type_ids = fields.Many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', 'Tasks Stages', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]})
    task_count = fields.Integer(compute='_compute_task_count', string="Tasks")
    task_needaction_count = fields.Integer(compute='_compute_task_needaction_count', string="Tasks")
    task_ids = fields.One2many('project.task', 'project_id',
                                domain=['|', ('stage_id.fold', '=', False), ('stage_id', '=', False)])
    color = fields.Integer('Color Index')
    user_id = fields.Many2one('res.users', 'Project Manager', default=lambda self: self.env.user)
    alias_id = fields.Many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
                                help="Internal email associated with this project. Incoming emails are automatically synchronized "
                                     "with Tasks (or optionally Issues if the Issue Tracker module is installed).")
    alias_model = fields.Selection(_alias_models, "Alias Model", index=True, required=True, default='project.task',
                                    help="The kind of document created when an email is received on this project's email alias")
    privacy_visibility = fields.Selection(_visibility_selection, 'Privacy / Visibility', required=True, default='employees',
        help="Holds visibility of the tasks or issues that belong to the current project:\n"
                "- Portal : employees see everything;\n"
                "   if portal is activated, portal users see the tasks or issues followed by\n"
                "   them or by someone of their company\n"
                "- Employees Only: employees see all tasks or issues\n"
                "- Followers Only: employees see only the followed tasks or issues; if portal\n"
                "   is activated, portal users see the followed tasks or issues.")
    state = fields.Selection([('draft','New'),
                              ('open','In Progress'),
                              ('cancelled', 'Cancelled'),
                              ('pending','Pending'),
                              ('close','Closed')],
                              'Status', required=True, copy=False, default='open')
    doc_count = fields.Integer(compute='_compute_get_attached_docs', string="Number of documents attached")
    date_start = fields.Date('Start Date')
    date = fields.Date('Expiration Date', index=True, track_visibility='onchange')
    use_tasks = fields.Boolean(related='analytic_account_id.use_tasks', default=True)

    def _compute_get_attached_docs(self):
        Attachment = self.env['ir.attachment']
        for project in self:
            project_attachments = Attachment.search_count([('res_model', '=', 'project.project'), ('res_id', '=', project.id)])
            task_attachments = Attachment.search_count([('res_model', '=', 'project.task'), ('res_id', 'in', project.tasks.ids)])
            project.doc_count = project_attachments + task_attachments

    def _compute_task_count(self):
        for project in self:
            project.task_count = len(project.task_ids)

    def _compute_task_needaction_count(self):
        projects = self.env['project.task'].read_group([('project_id', 'in', self.ids), ('message_needaction', '=', True)], ['project_id'], ['project_id'])
        mapped_data = {project['project_id'][0]: int(project['project_id_count']) for project in projects}
        for project in self:
            project.task_needaction_count = mapped_data.get(project.id)

    @api.constrains('date_start', 'date')
    def _check_dates(self):
        for project in self:
            if project.date_start and project.date and project.date_start > project.date:
                raise UserError(_('Error! project start-date must be lower than project end-date.'))

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if 'pricelist_id' in self.fields_get():
            self.pricelist_id = self.partner_id.property_product_pricelist

    @api.model
    def create(self, vals):
        ir_values = self.env['ir.values'].get_default('project.config.settings', 'generate_project_alias')
        if ir_values:
            vals['alias_name'] = vals.get('alias_name') or vals.get('name')
        create_context = dict(self.env.context,
                              project_creation_in_progress=True,
                              mail_create_nosubscribe=True)
        return super(Project, self.with_context(create_context)).create(vals)

    @api.multi
    def write(self, vals):
        # if alias_model has been changed, update alias_model_id accordingly
        if vals.get('alias_model'):
            models = self.env['ir.model'].search([('model', '=', vals.get('alias_model', 'project.task'))], limit=1)
            vals.update(alias_model_id=models.id)
        res = super(Project, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a project does it on its tasks, too
            tasks = self.with_context(active_test=False).mapped('tasks')
            tasks.write({'active': vals['active']})
        return res

    @api.multi
    def copy(self, default=None):
        if default is None:
            default = {}
        context = dict(self.env.context)
        context['active_test'] = False
        if not default.get('name'):
            default.update(name=_("%s (copy)") % (self.name))
        project = super(Project, self).copy(default)
        self.with_context(active_test=False).map_tasks(project)
        return project

    @api.multi
    def unlink(self):
        AnalyticAccount = self.env['account.analytic.account']
        for proj in self:
            if proj.tasks:
                raise UserError(_('You cannot delete a project containing tasks. You can either delete all the project\'s tasks and then delete the project or simply deactivate the project.'))
            if proj.analytic_account_id and not proj.analytic_account_id.line_ids:
                AnalyticAccount += proj.analytic_account_id
        res = super(Project, self).unlink()
        AnalyticAccount.unlink()
        return res

    @api.multi
    def set_template(self):
        return self.setActive(value=False)

    @api.multi
    def reset_project(self):
        return self.setActive(value=True)

    def map_tasks(self, project):
        """ copy and map tasks from old to new project """
        self.ensure_one()
        map_task_id = {}
        Tasks = self.env['project.task']
        for task in self.tasks:
            # preserve task name and stage, normally altered during copy
            defaults = {'stage_id': task.stage_id.id,
                        'name': task.name}
            map_task_id[task.id] =  task.copy(defaults).id
        project.write({'tasks':[(6, 0, map_task_id.values())]})
        Tasks.duplicate_task(map_task_id)

    @api.multi
    def duplicate_template(self):
        context = dict(self.env.context)
        result = []
        for proj in self:
            context.update({'analytic_project_copy': True})
            new_date_start = time.strftime('%Y-%m-%d')
            new_date_end = False
            if proj.date_start and proj.date:
                start_date = date(*time.strptime(proj.date_start,'%Y-%m-%d')[:3])
                end_date = date(*time.strptime(proj.date,'%Y-%m-%d')[:3])
                new_date_end = (datetime(*time.strptime(new_date_start,'%Y-%m-%d')[:3])+(end_date-start_date)).strftime('%Y-%m-%d')
            context.update({'copy':True})
            new_id = proj.copy(default = {
                                    'name':_("%s (copy)") % (proj.name),
                                    'state':'open',
                                    'date_start':new_date_start,
                                    'date':new_date_end}).id
            result.append(new_id)

        if result and len(result):
            res_id = result[0]
            form = self.env.ref('project.edit_project')
            form_view_id = form.id
            form_view = form.res_id
            tree = self.env.ref('project.view_project')
            tree_view_id = tree.id
            tree_view = tree.res_id
            search = self.env.ref('project.view_project_project_filter')
            search_view_id = search.id
            search_view = search.res_id
            return {
                'name': _('Projects'),
                'view_type': 'form',
                'view_mode': 'form, tree',
                'res_model': 'project.project',
                'view_id': False,
                'res_id': res_id,
                'views': [(form_view['res_id'], 'form'),(tree_view['res_id'], 'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view['res_id'],
            }

    @api.multi
    def setActive(self, value=True):
        """ Set a project as active/inactive, and its tasks as well. """
        self.write({'active': value})

    @api.multi
    def attachment_tree_view(self):
        self.ensure_one()
        tasks = self.env['project.task'].search([('project_id', 'in', self.ids)])
        domain = [
             '|',
             '&', ('res_model', '=', 'project.project'), ('res_id', 'in', self.ids),
             '&', ('res_model', '=', 'project.task'), ('res_id', 'in', tasks.ids)]
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
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }


class Task(models.Model):
    _name = "project.task"
    _description = "Task"
    _date_name = "date_start"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = "priority desc, sequence, date_start, name, id"
    _mail_post_access = 'read'

    def _get_default_partner(self):
        context = dict(self.env.context)
        if 'default_project_id' in context:
            return self.env['project.project'].browse(context['default_project_id']).partner_id

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        return self.stage_find(self.env.context.get('default_project_id'), [('fold', '=', False)])

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        ProjectTaskType = self.env['project.task.type']
        order = ProjectTaskType._order
        access_rights_uid = access_rights_uid or self.env.user.id
        if read_group_order == 'stage_id desc':
            order = '%s desc' % order
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id']), ('id', 'in', self.ids)]
        else:
            search_domain = [('id', 'in', self.ids)]
        stage_ids = ProjectTaskType._search(search_domain, order=order, access_rights_uid=access_rights_uid)
        stages = ProjectTaskType.sudo(access_rights_uid).browse(stage_ids)
        result = stages.sudo(access_rights_uid).name_get()
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stages:
            fold[stage.id] = stage.fold
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids,
    }

    active = fields.Boolean(default=True)
    name = fields.Char('Task Title', track_visibility='onchange', required=True, index=True)
    description = fields.Html()
    priority = fields.Selection([('0','Normal'), ('1','High')], index=True, default=0)
    sequence = fields.Integer(index=True, default=10, help="Gives the sequence order when displaying a list of tasks.")
    stage_id = fields.Many2one('project.task.type', string='Stage', track_visibility='onchange', index=True,
                    domain="[('project_ids', '=', project_id)]", copy=False, default=_get_default_stage_id)
    tag_ids = fields.Many2many('project.tags', string='Tags', oldname='categ_ids')
    kanban_state = fields.Selection([('normal', 'In Progress'),('done', 'Ready for next stage'),('blocked', 'Blocked')], 'Kanban State',
                                     track_visibility='onchange',
                                     help="A task's kanban state indicates special situations affecting it:\n"
                                          " * Normal is the default situation\n"
                                          " * Blocked indicates something is preventing the progress of this task\n"
                                          " * Ready for next stage indicates the task is ready to be pulled to the next stage",
                                     required=True, copy=False, default='normal')

    create_date = fields.Datetime('Create Date', readonly=True, index=True)
    write_date = fields.Datetime('Last Modification Date', readonly=True, index=True) #not displayed in the view but it might be useful with base_action_rule module (and it needs to be defined first for that)
    date_start = fields.Datetime('Starting Date', index=True, copy=False, default=fields.Datetime.now)
    date_end = fields.Datetime('Ending Date', index=True, copy=False)
    date_assign = fields.Datetime('Assigning Date', index=True, copy=False, readonly=True)
    date_deadline = fields.Date('Deadline', index=True, copy=False)
    date_last_stage_update = fields.Datetime('Last Stage Update', index=True, copy=False, readonly=True, default=fields.Datetime.now)
    project_id = fields.Many2one('project.project', string='Project', ondelete='set null', index=True, track_visibility='onchange', change_default=True)
    parent_ids = fields.Many2many('project.task', 'project_task_parent_rel', 'task_id', 'parent_id', string='Parent Tasks')
    child_ids = fields.Many2many('project.task', 'project_task_parent_rel', 'parent_id', 'task_id', string='Delegated Tasks')
    notes = fields.Text()
    planned_hours = fields.Float('Initially Planned Hours', help='Estimated time to do the task, usually set by the project manager when the task is in draft state.')
    remaining_hours = fields.Float('Remaining Hours', digits=(16,2), help="Total remaining time, can be re-estimated periodically by the assignee of the task.")
    user_id = fields.Many2one('res.users', 'Assigned to', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', 'Customer', default=_get_default_partner)
    manager_id = fields.Many2one('res.users', related='project_id.user_id', string='Project Manager')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    color = fields.Integer('Color Index')
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=lambda self: [('res_model', '=', self._name)], auto_join=True, string='Attachments')
    # In the domain of displayed_image_id, we couln't use attachment_ids because a one2many is represented as a list of commands so we used res_model & res_id
    displayed_image_id = fields.Many2one('ir.attachment', domain="[('res_model', '=', 'project.task'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]", string='Displayed Image')
    legend_blocked = fields.Char(related="stage_id.legend_blocked", string='Kanban Blocked Explanation')
    legend_done = fields.Char(related="stage_id.legend_done", string='Kanban Valid Explanation')
    legend_normal = fields.Char(related="stage_id.legend_normal", string='Kanban Ongoing Explanation')

    @api.constrains('parent_ids', 'child_ids')
    def _check_recursion(self):
        for task in self:
            visited_branch = set()
            visited_node = set()
            res = task._check_cycle(visited_branch, visited_node)
            if not res:
                raise UserError(_("Error ! You cannot create recursive tasks."))

    def _check_cycle(self, visited_branch, visited_node):
        self.ensure_one()
        if self.id in visited_branch: #Cycle
            return False

        if self.id in visited_node: #Already tested don't work one more time for nothing
            return True

        visited_branch.add(self.id)
        visited_node.add(self.id)

        #visit child using DFS
        for child in self.child_ids:
            res = child._check_cycle(visited_branch, visited_node)
            if not res:
                return False

        visited_branch.remove(self.id)
        return True

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for task in self:
            if task.date_start and task.date_end and task.date_start > task.date_end:
                raise UserError(_("Error ! Task starting date must be lower than its ending date."))

    @api.multi
    def onchange_remaining(self, remaining=0.0, planned=0.0):
        if remaining and not planned:
            return {'value': {'planned_hours': remaining}}
        return {}

    @api.multi
    def onchange_planned(self, planned=0.0, effective=0.0):
        return {'value': {'remaining_hours': planned - effective}}

    @api.multi
    def onchange_project(self, project_id):
        if project_id:
            project = self.env['project.project'].browse(project_id)
            return {'value': {'partner_id': project.partner_id.id}}
        return {}

    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.user_id:
            self.date_start = fields.Datetime.now()

    # ------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------

    @api.model
    def create(self, vals):
        context = dict(self.env.context)
        # for default stage
        if vals.get('project_id') and not context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        # user_id change: update date_assign
        if vals.get('user_id'):
            vals['date_assign'] = fields.Datetime.now()

        # context: no_log, because subtype already handle this
        context['mail_create_nolog'] = True
        task = super(Task, self.with_context(context)).create(vals)
        task._store_history()
        return task

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
        # user_id change: update date_assign
        if vals.get('user_id'):
            vals['date_assign'] = fields.Datetime.now()
        # reset kanban state when changing stage
        if 'stage_id' in vals:
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'

        result = super(Task, self).write(vals)

        if any(item in vals for item in ['stage_id', 'remaining_hours', 'user_id', 'kanban_state']):
            self._store_history()
        return result

    @api.multi
    def unlink(self):
        self._check_child_task()
        return super(Task, self).unlink()

    @api.multi
    def copy_data(self, default=None, context=None):
        self.ensure_one()
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)") % self.name
        if 'remaining_hours' not in default:
            default['remaining_hours'] = self.planned_hours

        return super(Task, self).copy_data(default)[0]

    # Override view according to the company definition
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # read uom as admin to avoid access rights issues, e.g. for portal/share users,
        # this should be safe (no context passed to avoid side-effects)
        product_uom = self.env.user.company_id.project_time_mode_id
        res = super(Task, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        # read uom as admin to avoid access rights issues, e.g. for portal/share users,
        # this should be safe (no context passed to avoid side-effects)
        uom_hour = self.env.ref('product.product_uom_hour', raise_if_not_found=False)
        if not product_uom or not uom_hour or product_uom.id == uom_hour.id:
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
        for project_field in res['fields']:
            # TODO this NOT work in different language than english
            # the field 'Initially Planned Hours' should be replaced by 'Initially Planned Days'
            # but string 'Initially Planned Days' is not available in translation
            if 'Hours' in res['fields'][project_field]['string']:
                res['fields'][project_field]['string'] = res['fields'][project_field]['string'].replace('Hours', product_uom.name)
        return res

    @api.model
    def get_empty_list_help(self, help):
        context = dict(self.env.context)
        context['empty_list_help_id'] = context.get('default_project_id')
        context['empty_list_help_model'] = 'project.project'
        context['empty_list_help_document_name'] = _("tasks")
        return super(Task, self.with_context(context)).get_empty_list_help(help)

    # ----------------------------------------
    # Case management
    # ----------------------------------------

    def stage_find(self, section_id, domain=None, order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        if domain is None:
            domain = []
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        for task in self:
            if task.project_id:
                section_ids.append(task.project_id.id)
        search_domain = []
        if section_ids:
            search_domain = [('|')] * (len(section_ids) - 1)
            for section_id in section_ids:
                search_domain.append(('project_ids', '=', section_id))
        search_domain += list(domain)
        # perform search, return the first found
        stage = self.env['project.task.type'].search(search_domain, order=order, limit=1)
        return stage.id

    def _check_child_task(self):
        for task in self:
            for child in task.child_ids:
                if child.stage_id and not child.stage_id.fold:
                    raise UserError(_("Child task still open.\nPlease cancel or complete child task first."))
        return True

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

    def _get_total_hours(self):
        return self.remaining_hours

    @api.v7
    def _generate_task(self, cr, uid, tasks, ident=4, context=None):
        return tasks._generate_task(ident=ident)

    @api.v8
    def _generate_task(self, ident=4):
        result = ""
        ident = ' '*ident
        company = self.env.user.company_id
        duration_uom = {
            'day(s)': 'd', 'days': 'd', 'day': 'd', 'd': 'd',
            'month(s)': 'm', 'months': 'm', 'month': 'month', 'm': 'm',
            'week(s)': 'w', 'weeks': 'w', 'week': 'w', 'w': 'w',
            'hour(s)': 'H', 'hours': 'H', 'hour': 'H', 'h': 'H',
        }.get(company.project_time_mode_id.name.lower(), "hour(s)")
        for task in self:
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

    @api.multi
    def _track_template(self, tracking):
        res = super(Task, self)._track_template(tracking)
        test_task = self[0]
        changes, tracking_value_ids = tracking[test_task.id]
        if 'stage_id' in changes and test_task.stage_id.mail_template_id:
            res['stage_id'] = (test_task.stage_id.mail_template_id, {'composition_mode': 'mass_mail'})
        return res

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'kanban_state' in init_values and self.kanban_state == 'blocked':
            return 'project.mt_task_blocked'
        elif 'kanban_state' in init_values and self.kanban_state == 'done':
            return 'project.mt_task_ready'
        elif 'user_id' in init_values and self.user_id:  # assigned -> new
            return 'project.mt_task_new'
        elif 'stage_id' in init_values and self.stage_id and self.stage_id.sequence <= 1:  # start stage -> new
            return 'project.mt_task_new'
        elif 'stage_id' in init_values:
            return 'project.mt_task_stage'
        return super(Task, self)._track_subtype(init_values)

    @api.multi
    def _notification_group_recipients(self, message, recipients, done_ids, group_data):
        """ Override the mail.thread method to handle project users and officers
        recipients. Indeed those will have specific action in their notification
        emails: creating tasks, assigning it. """
        group_project_user = self.env.ref('project.group_project_user', raise_if_not_found=False)
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and group_project_user.id in recipient.user_ids[0].groups_id.ids:
                group_data['group_project_user'] |= recipient
                done_ids.add(recipient.id)
        return super(Task, self)._notification_group_recipients(message, recipients, done_ids, group_data)

    @api.multi
    def _notification_get_recipient_groups(self, message, recipients):
        self.ensure_one()
        recipient_group = super(Task, self)._notification_get_recipient_groups(message, recipients)
        take_action = self._notification_link_helper('assign')
        template = self.env.ref('project.action_view_task', raise_if_not_found=False)
        new_action = self._notification_link_helper('new', action_id=template.id)
        actions = []
        if not self.user_id:
            actions.append({'url': take_action, 'title': _('I take it')})
        else:
            actions.append({'url': new_action, 'title': _('New Task')})
        recipient_group['group_project_user'] = {
            'actions': actions
        }
        return recipient_group

    @api.model
    def message_get_reply_to(self, ids, default=None):
        """ Override to get the reply_to of the parent project. """
        tasks = self.sudo().browse(ids)
        project_ids = set([task.project_id.id for task in tasks if task.project_id])
        aliases = self.env['project.project'].message_get_reply_to(list(project_ids), default=default)
        return dict((task.id, aliases.get(task.project_id and task.project_id.id or 0, False)) for task in tasks)

    @api.multi
    def email_split(self, msg):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        aliases = [task.project_id.alias_name for task in self if task.project_id]
        return filter(lambda x: x.split('@')[0] not in aliases, email_list)

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Override to updates the document according to the email. """
        if custom_values is None:
            custom_values = {}
        defaults = {
            'name': msg.get('subject'),
            'planned_hours': 0.0,
            'partner_id': msg.get('author_id', False)
        }
        defaults.update(custom_values)

        task_id = super(Task, self).message_new(msg, custom_values=defaults)
        task = self.browse(task_id)
        email_list = task.email_split(msg)
        partner_ids = filter(None, task._find_partner_from_emails(email_list, force_create=False))
        task.message_subscribe(partner_ids)
        return task_id

    @api.multi
    def message_update(self, msg, update_vals=None):
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

        email_list = self.email_split(msg)
        partner_ids = filter(None, self._find_partner_from_emails(email_list, force_create=False))
        self.message_subscribe(partner_ids)
        return super(Task, self).message_update(msg, update_vals=update_vals)

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(Task, self).message_get_suggested_recipients()
        for task in self:
            if task.partner_id:
                reason = _('Customer Email') if task.partner_id.email else _('Customer')
                task._message_add_suggested_recipient(recipients, partner=task.partner_id, reason=reason)
        return recipients

    @api.multi
    def message_get_email_values(self, notif_mail=None):
        self.ensure_one()
        res = super(Task, self).message_get_email_values(notif_mail=notif_mail)
        headers = {}
        if res.get('headers'):
            try:
                headers.update(eval(res['headers']))
            except Exception:
                pass
        if self.project_id:
            current_objects = filter(None, headers.get('X-Odoo-Objects', '').split(','))
            current_objects.insert(0, 'project.project-%s, ' % self.project_id.id)
            headers['X-Odoo-Objects'] = ','.join(current_objects)
        if self.tag_ids:
            headers['X-Odoo-Tags'] = ','.join([tag.name for tag in self.tag_ids])
        res['headers'] = repr(headers)
        return res

    @api.model
    def duplicate_task(self, map_ids):
        mapper = lambda t: map_ids.get(t.id, t.id)
        for task in self.browse(map_ids.values()):
            new_child_ids = set(map(mapper, task.child_ids))
            new_parent_ids = set(map(mapper, task.parent_ids))
            if new_child_ids or new_parent_ids:
                task.write({'parent_ids': [(6, 0, list(new_parent_ids))],
                            'child_ids':  [(6, 0, list(new_child_ids))]})


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    _description = 'Analytic Account'

    use_tasks = fields.Boolean(string='Tasks', help="Check this box to manage internal activities through this project")
    company_uom_id = fields.Many2one(relation='product.uom', related='company_id.project_time_mode_id', string='Company UOM')
    project_ids = fields.One2many('project.project', 'analytic_account_id', string='Projects')
    project_count = fields.Integer(compute='_compute_project_count', string='Project Count')

    def _compute_project_count(self):
        for account in self:
            account.project_count = len(account.project_ids)

    @api.multi
    def on_change_template(self, template_id, date_start=False):
        res = super(AccountAnalyticAccount, self).on_change_template(template_id, date_start=date_start)
        if template_id and 'value' in res:
            template = self.browse(template_id)
            res['value']['use_tasks'] = template.use_tasks
        return res

    @api.model
    def create(self, vals):
        if vals.get('child_ids') and self.env.context.get('analytic_project_copy'):
            vals['child_ids'] = []
        analytic_account = super(AccountAnalyticAccount, self).create(vals)
        analytic_account.project_create(vals)
        return analytic_account

    @api.multi
    def write(self, vals):
        vals_for_project = vals.copy()
        for analytic in self:
            if not vals.get('name'):
                vals_for_project['name'] = analytic.name
            analytic.project_create(vals_for_project)
        return super(AccountAnalyticAccount, self).write(vals)

    @api.multi
    def unlink(self):
        tasks_count = self.env['project.task'].search_count([('project_id.analytic_account_id', 'in', self.ids)])
        if tasks_count:
            raise UserError(_('Please remove existing tasks in the project linked to the accounts you want to delete.'))
        return super(AccountAnalyticAccount, self).unlink()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        if self.env.context.get('current_model') == 'project.project':
            analytic_accounts = self.search(args + [('name', operator, name)], limit=limit)
            return analytic_accounts.name_get()

        return super(AccountAnalyticAccount, self).name_search(name, args=args, operator=operator, limit=limit)

    @api.model
    def _trigger_project_creation(self, vals):
        '''
        This function is used to decide if a project needs to be automatically created or not when an analytic account is created. It returns True if it needs to be so, False otherwise.
        '''
        return vals.get('use_tasks') and not 'project_creation_in_progress' in self.env.context

    @api.multi
    def project_create(self, vals):
        '''
        This function is called at the time of analytic account creation and is used to create a project automatically linked to it if the conditions are meet.
        '''
        self.ensure_one()
        Project = self.env['project.project']
        project = Project.search([('analytic_account_id', '=', self.id)], limit=1)
        if not project and self._trigger_project_creation(vals):
            project_values = {
                'name': vals.get('name'),
                'analytic_account_id': self.id,
                'use_tasks': True,
            }
            return Project.create(project_values)

    @api.multi
    def projects_action(self):
        self.ensure_one()
        project_ids = self.project_ids.ids
        result = {
            "type": "ir.actions.act_window",
            "res_model": "project.project",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [["id", "in", project_ids]],
            "context": {"create": False},
            "name": "Projects",
        }
        if len(project_ids) == 1:
            result['views'] = [(False, "form")]
            result['res_id'] = project_ids[0]
        else:
            result = {'type': 'ir.actions.act_window_close'}
        return result


class ProjectTaskHistory(models.Model):
    """
    Tasks History, used for cumulative flow charts (Lean/Agile)
    """
    _name = 'project.task.history'
    _description = 'History of Tasks'
    _rec_name = 'task_id'
    _log_access = False

    task_id = fields.Many2one('project.task', 'Task', ondelete='cascade', required=True, index=True)
    type_id = fields.Many2one('project.task.type', 'Stage')
    kanban_state = fields.Selection([('normal', 'Normal'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')], 'Kanban State')
    date = fields.Date('Date', index=True, default=fields.Date.context_today)
    end_date = fields.Date(compute='_compute_get_date', string='End Date', store=True)
    remaining_hours = fields.Float('Remaining Time', digits=(16, 2))
    planned_hours = fields.Float('Planned Time', digits=(16, 2))
    user_id = fields.Many2one('res.users', 'Responsible')

    @api.depends('task_id')
    def _compute_get_date(self):
        for history in self:
            if history.type_id.fold:
                history.end_date = history.date
                continue
            self.env.cr.execute('''select
                    date
                from
                    project_task_history
                where
                    task_id=%s and
                    id>%s
                order by id limit 1''', (history.task_id.id, history.id))
            res = self.env.cr.fetchone()
            history.end_date = res and res[0] or False

    @api.multi
    def _get_related_date(self):
        result = []
        for history in self:
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


class ProjectTaskHistoryCumulative(models.Model):
    _name = 'project.task.history.cumulative'
    _table = 'project_task_history_cumulative'
    _inherit = 'project.task.history'
    _auto = False

    end_date = fields.Date('End Date')
    nbr_tasks = fields.Integer('# of Tasks', readonly=True)
    project_id = fields.Many2one('project.project', 'Project')

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


class ProjectTags(models.Model):
    """ Tags of project's tasks (or issues) """
    _name = "project.tags"
    _description = "Tags of project's tasks, issues..."

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
