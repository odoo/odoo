# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import api , fields, models, tools, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval as eval


class ProjectTaskType(models.Model):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence'

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=1)
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
    fold = fields.Boolean(string='Folded in Tasks Pipeline',
                           help='This stage is folded in the kanban view when '
                           'there are no records in that stage to display.')


class Project(models.Model):
    _name = "project.project"
    _description = "Project"
    _inherits = {'account.analytic.account': "analytic_account_id",
                 "mail.alias": "alias_id"}
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _order = "sequence, name, id"
    _period_number = 5

    def _auto_init(self, cr, context=None):
        """ Installation hook: aliases, project.project """
        # create aliases for all projects and avoid constraint errors
        alias_context = dict(context, alias_model_name='project.task')
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(Project, self)._auto_init,
            'project.task', self._columns['alias_id'], 'id', alias_prefix='project+', alias_defaults={'project_id':'id'}, context=alias_context)

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
    resource_calendar_id = fields.Many2one('resource.calendar', 'Working Time', help="Timetable working hours to adjust the gantt diagram report", states={'close':[('readonly',True)]} )
    type_ids = fields.Many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', 'Tasks Stages', states={'close':[('readonly',True)], 'cancelled':[('readonly',True)]})
    task_count = fields.Integer(compute='_compute_task_count', string="Tasks")
    task_ids = fields.One2many('project.task', 'project_id',
                                domain=[('stage_id.fold', '=', False)])
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


    def _compute_task_count(self):
        task_data = self.env['project.task'].read_group([('project_id', 'in', self.ids),'|', ('stage_id.fold', '=', False), ('stage_id', '=', None)], ['project_id'], ['project_id'])
        mapped_data = {task['project_id'][0]: task['project_id_count'] for task in task_data}
        for project in self:
            project.task_count = mapped_data.get(project.id)

    def _compute_get_attached_docs(self):
        Attachment = self.env['ir.attachment']
        for project in self:
            project_attachments = Attachment.search_count([('res_model', '=', 'project.project'), ('res_id', '=', project.id)])
            task_attachments = Attachment.search_count([('res_model', '=', 'project.task'), ('res_id', 'in', project.tasks.ids)])
            project.doc_count = project_attachments + task_attachments

    @api.constrains('date_start', 'date')
    def _check_dates(self):
        for project in self:
            if project.date_start and project.date and project.date_start > project.date:
                raise UserError(_('Error! project start-date must be lower than project end-date.'))

    def map_tasks(self, project):
        """ copy and map tasks from old to new project """
        self.ensure_one()
        map_task_id = {}
        for task in self.tasks:
            # preserve task name and stage, normally altered during copy
            defaults = {'stage_id': task.stage_id.id,
                        'name': task.name}
            map_task_id[task.id] =  task.copy(defaults).id
        project.write({'tasks':[(6,0, map_task_id.values())]})

    @api.multi
    def copy(self, default=None):
        default = default or {}
        if not default.get('name'):
            default.update(name=_("%s (copy)") % (self.name))
        project = super(Project, self).copy(default)
        self.with_context(active_test=False).map_tasks(project)
        return project

    @api.model
    def create(self, vals):
        # Prevent double project creation when 'use_tasks' is checked + alias management
        create_context = dict(self.env.context, project_creation_in_progress=True,
                              alias_model_name=vals.get('alias_model', 'project.task'),
                              alias_parent_model_name=self._name,
                              mail_create_nosubscribe=True)

        ir_values = self.env['ir.values'].get_default('project.config.settings', 'generate_project_alias')
        if ir_values:
            vals['alias_name'] = vals.get('alias_name') or vals.get('name')
        project = super(Project, self.with_context(create_context)).create(vals)
        values = {'alias_parent_thread_id': project.id, 'alias_defaults': {'project_id': project.id}}
        project.alias_id.write(values)
        return project

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
    def unlink(self):
        MailAlias = self.env['mail.alias']
        AnalyticAccount = self.env['account.analytic.account']
        for project in self:
            if project.tasks:
                raise UserError(_('You cannot delete a project containing tasks. You can either delete all the project\'s tasks and then delete the project or simply deactivate the project.'))
            elif project.alias_id:
                MailAlias += project.alias_id
            if not project.analytic_account_id.line_ids:
                AnalyticAccount += project.analytic_account_id
        res = super(Project, self).unlink()
        MailAlias.unlink()
        AnalyticAccount.unlink()
        return res

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
        context = self.env.context
        if 'default_project_id' in context:
            return self.env['project.project'].browse(context['default_project_id']).partner_id
        return False

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
    stage_id = fields.Many2one('project.task.type', 'Stage', track_visibility='onchange', index=True,
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
    project_id = fields.Many2one('project.project', 'Project', ondelete='set null', index=True, track_visibility='onchange',
        change_default=True, default=lambda self: self.env.context.get('default_project_id'))
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


    @api.constrains('date_start','date_end')
    def _check_dates(self):
        for task in self:
            if task.date_start and task.date_end and task.date_start > task.date_end:
                raise UserError(_("Error ! Task starting date must be lower than its ending date."))

    @api.onchange('remaining_hours')
    def onchange_remaining(self):
        if not self.planned_hours:
            self.planned_hours = self.remaining_hours

    @api.onchange('planned_hours')
    def onchange_planned(self):
        self.remaining_hours = self.planned_hours

    @api.multi
    def onchange_project(self, project_id):
        if project_id:
            project = self.env['project.project'].browse(project_id)
            return {'value': {'partner_id': project.partner_id.id}}
        return {'value': {'partner_id': False}}

    @api.onchange('user_id')
    def onchange_user_id(self):
        if self.user_id:
            self.date_start = fields.Datetime.now()

    def _store_history(self):
        self.env['project.task.history'].create({
            'task_id': self.id,
            'remaining_hours': self.remaining_hours,
            'planned_hours': self.planned_hours,
            'kanban_state': self.kanban_state,
            'type_id': self.stage_id.id,
            'user_id': self.user_id.id
        })
        return True

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

        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the task changes.
        if vals and not 'kanban_state' in vals and 'stage_id' in vals:
            new_stage = vals.get('stage_id')
            vals_reset_kstate = dict(vals, kanban_state='normal')
            for task in self:
                write_vals = vals_reset_kstate if task.stage_id.id != new_stage else vals
                super(Task, self).write(write_vals)
            result = True
        else:
            result = super(Task, self).write(vals)

        if any(item in vals for item in ['stage_id', 'remaining_hours', 'user_id', 'kanban_state']):
            self._store_history()
        return result

    @api.multi
    def copy_data(self, default=None):
        self.ensure_one()
        default = default or {}
        if not default.get('name'):
            default['name'] = _("%s (copy)") % self.name
        return super(Task, self).copy_data(default)[0]

    # Override view according to the company definition
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        # read uom as admin to avoid access rights issues, e.g. for portal/share users,
        # this should be safe (no context passed to avoid side-effects)
        product_uom = self.env.user.company_id.project_time_mode_id
        project_data = super(Task, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        # read uom as admin to avoid access rights issues, e.g. for portal/share users,
        # this should be safe (no context passed to avoid side-effects)
        uom_hour = self.env.ref('product.product_uom_hour', raise_if_not_found=False)
        if not product_uom or not uom_hour or product_uom.id == uom_hour.id:
            return project_data

        eview = etree.fromstring(project_data['arch'])

        # if the project_time_mode_id is not in hours (so in days), display it as a float field
        def _check_rec(eview):
            if eview.attrib.get('widget','') == 'float_time':
                eview.set('widget','float')
            for child in eview:
                _check_rec(child)
            return True

        _check_rec(eview)

        project_data['arch'] = etree.tostring(eview)

        # replace reference of 'Hours' to 'Day(s)'
        for project_field in project_data['fields']:
            # TODO this NOT work in different language than english
            # the field 'Initially Planned Hours' should be replaced by 'Initially Planned Days'
            # but string 'Initially Planned Days' is not available in translation
            if 'Hours' in project_data['fields'][project_field]['string']:
                project_data['fields'][project_field]['string'] = project_data['fields'][project_field]['string'].replace('Hours', product_uom.name)
        return project_data

    @api.model
    def get_empty_list_help(self, help):
        context = dict(self.env.context)
        context['empty_list_help_id'] = context.get('default_project_id')
        context['empty_list_help_model'] = 'project.project'
        context['empty_list_help_document_name'] = _("tasks")
        return super(Task, self.with_context(context)).get_empty_list_help(help)

    def stage_find(self, section_id, domain=[], order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        search_domain = []
        if section_ids:
            search_domain = [('|')] * (len(section_ids) - 1)
            for section_id in section_ids:
                search_domain.append(('project_ids', '=', section_id))
        search_domain += list(domain)
        # perform search, return the first found
        stages = self.env['project.task.type'].search(search_domain, order=order, limit=1)
        return stages and stages[0] or False

    def _get_total_hours(self):
        return self.remaining_hours

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

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
    def message_get_reply_to(self, res_ids, default=None):
        """ Override to get the reply_to of the parent project. """
        tasks = self.browse(res_ids)
        aliases = self.env['project.project'].message_get_reply_to(tasks.mapped('project_id').ids, default=default)
        return dict((task.id, aliases.get(task.project_id.id or 0, False)) for task in tasks)

    def email_split(self, msg):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        aliases = self.project_id.alias_name and [self.project_id.alias_name] or []
        return filter(lambda x: x.split('@')[0] not in aliases, email_list)

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Override to updates the document according to the email. """
        custom_values = custom_values or {}
        custom_values.update({
            'name': msg.get('subject'),
            'planned_hours': 0.0,
            'partner_id': msg.get('author_id', False)
        })

        task_id = super(Task, self).message_new(msg, custom_values)
        task = self.browse(task_id)
        email_list = task.email_split(msg)
        partner_ids = task._find_partner_from_emails(email_list, force_create=True)
        task.message_subscribe(partner_ids)
        return task.id

    @api.multi
    def message_update(self, msg, update_vals=None):
        """ Override to update the task according to the email. """
        update_vals = update_vals or {}
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
        partner_ids = self._find_partner_from_emails(email_list, force_create=True)
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


class ProjectTags(models.Model):
    """ Tags of project's tasks (or issues) """
    _name = "project.tags"
    _description = "Tags of project's tasks, issues..."

    name = fields.Char(required=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
