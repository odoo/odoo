# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval


class ProjectTaskType(models.Model):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence, id'

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=1)
    project_ids = fields.Many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', string='Projects',
        default=_get_default_project_ids)
    legend_priority = fields.Char(
        string='Starred Explanation', translate=True,
        help='Explanation text to help users using the star on tasks or issues in this stage.')
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda s: _('Blocked'), translate=True, required=True,
        help='Override the default value displayed for the blocked state for kanban selection, when the task or issue is in that stage.')
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda s: _('Ready for Next Stage'), translate=True, required=True,
        help='Override the default value displayed for the done state for kanban selection, when the task or issue is in that stage.')
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda s: _('In Progress'), translate=True, required=True,
        help='Override the default value displayed for the normal state for kanban selection, when the task or issue is in that stage.')
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'project.task')],
        help="If set an email will be sent to the customer when the task or issue reaches this step.")
    fold = fields.Boolean(string='Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    rating_template_id = fields.Many2one(
        'mail.template',
        string='Rating Email Template',
        domain=[('model', '=', 'project.task')],
        help="If set and if the project's rating configuration is 'Rating when changing stage', then an email will be sent to the customer when the task reaches this step.")
    auto_validation_kanban_state = fields.Boolean('Automatic kanban status', default=False,
        help="Automatically modify the kanban state when the customer replies to the feedback for this stage.\n"
            " * A good feedback from the customer will update the kanban state to 'ready for the new stage' (green bullet).\n"
            " * A medium or a bad feedback will set the kanban state to 'blocked' (red bullet).\n")

    @api.multi
    def unlink(self):
        stages = self
        default_project_id = self.env.context.get('default_project_id')
        if default_project_id:
            shared_stages = self.filtered(lambda x: len(x.project_ids) > 1 and default_project_id in x.project_ids.ids)
            tasks = self.env['project.task'].with_context(active_test=False).search([('project_id', '=', default_project_id), ('stage_id', 'in', self.ids)])
            if shared_stages and not tasks:
                shared_stages.write({'project_ids': [(3, default_project_id)]})
                stages = self.filtered(lambda x: x not in shared_stages)
        return super(ProjectTaskType, stages).unlink()


class Project(models.Model):
    _name = "project.project"
    _description = "Project"
    _inherit = ['portal.mixin', 'mail.alias.mixin', 'mail.thread']
    _order = "sequence, name, id"
    _period_number = 5

    def get_alias_model_name(self, vals):
        return vals.get('alias_model', 'project.task')

    def get_alias_values(self):
        values = super(Project, self).get_alias_values()
        values['alias_defaults'] = {'project_id': self.id}
        return values

    @api.multi
    def unlink(self):
        for project in self:
            if project.tasks:
                raise UserError(_('You cannot delete a project containing tasks. You can either archive it or first delete all of its tasks.'))
        return super(Project, self).unlink()

    def _compute_attached_docs_count(self):
        Attachment = self.env['ir.attachment']
        for project in self:
            project.doc_count = Attachment.search_count([
                '|',
                '&',
                ('res_model', '=', 'project.project'), ('res_id', '=', project.id),
                '&',
                ('res_model', '=', 'project.task'), ('res_id', 'in', project.task_ids.ids)
            ])

    def _compute_task_count(self):
        task_data = self.env['project.task'].read_group([('project_id', 'in', self.ids), '|', ('stage_id.fold', '=', False), ('stage_id', '=', False)], ['project_id'], ['project_id'])
        result = dict((data['project_id'][0], data['project_id_count']) for data in task_data)
        for project in self:
            project.task_count = result.get(project.id, 0)

    @api.multi
    def attachment_tree_view(self):
        self.ensure_one()
        domain = [
            '|',
            '&', ('res_model', '=', 'project.project'), ('res_id', 'in', self.ids),
            '&', ('res_model', '=', 'project.task'), ('res_id', 'in', self.task_ids.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="o_view_nocontent_smiling_face">
                        Documents are attached to the tasks and issues of your project.</p><p>
                        Send messages or log internal notes with attachments to link
                        documents to your project.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    @api.model
    def activate_sample_project(self):
        """ Unarchives the sample project 'project.project_project_data' and
            reloads the project dashboard """
        # Unarchive sample project
        project = self.env.ref('project.project_project_data', False)
        if project:
            project.write({'active': True})

        cover_image = self.env.ref('project.msg_task_data_14_attach', False)
        cover_task = self.env.ref('project.project_task_data_14', False)
        if cover_image and cover_task:
            cover_task.write({'displayed_image_id': cover_image.id})

        # Change the help message on the action (no more activate project)
        action = self.env.ref('project.open_view_project_all', False)
        action_data = None
        if action:
            action.sudo().write({
                "help": _('''<p class="o_view_nocontent_smiling_face">
                    Create a new project</p>''')
            })
            action_data = action.read()[0]
        # Reload the dashboard
        return action_data

    def _compute_is_favorite(self):
        for project in self:
            project.is_favorite = self.env.user in project.favorite_user_ids

    def _inverse_is_favorite(self):
        favorite_projects = not_fav_projects = self.env['project.project'].sudo()
        for project in self:
            if self.env.user in project.favorite_user_ids:
                favorite_projects |= project
            else:
                not_fav_projects |= project

        # Project User has no write access for project.
        not_fav_projects.write({'favorite_user_ids': [(4, self.env.uid)]})
        favorite_projects.write({'favorite_user_ids': [(3, self.env.uid)]})

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    name = fields.Char("Name", index=True, required=True, track_visibility='onchange')
    active = fields.Boolean(default=True,
        help="If the active field is set to False, it will allow you to hide the project without removing it.")
    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of Projects.")
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True, track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)

    favorite_user_ids = fields.Many2many(
        'res.users', 'project_favorite_user_rel', 'project_id', 'user_id',
        default=_get_default_favorite_user_ids,
        string='Members')
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite', string='Show Project on dashboard',
        help="Whether this project should be displayed on the dashboard or not")
    label_tasks = fields.Char(string='Use Tasks as', default=lambda s: _('Tasks'), translate=True,
        help="Gives label to tasks on project's kanban view.")
    tasks = fields.One2many('project.task', 'project_id', string="Task Activities")
    resource_calendar_id = fields.Many2one(
        'resource.calendar', string='Working Time',
        default=lambda self: self.env.user.company_id.resource_calendar_id.id,
        help="Timetable working hours to adjust the gantt diagram report")
    type_ids = fields.Many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', string='Tasks Stages')
    task_count = fields.Integer(compute='_compute_task_count', string="Task Count")
    task_ids = fields.One2many('project.task', 'project_id', string='Tasks',
                               domain=['|', ('stage_id.fold', '=', False), ('stage_id', '=', False)])
    color = fields.Integer(string='Color Index')
    user_id = fields.Many2one('res.users', string='Project Manager', default=lambda self: self.env.user, track_visibility="onchange")
    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True,
        help="Internal email associated with this project. Incoming emails are automatically synchronized "
             "with Tasks (or optionally Issues if the Issue Tracker module is installed).")
    privacy_visibility = fields.Selection([
            ('followers', 'On invitation only'),
            ('employees', 'Visible by all employees'),
            ('portal', 'Visible by following customers'),
        ],
        string='Privacy', required=True,
        default='portal',
        help="Holds visibility of the tasks or issues that belong to the current project:\n"
                "- On invitation only: Employees may only see the followed project, tasks or issues\n"
                "- Visible by all employees: Employees may see all project, tasks or issues\n"
                "- Visible by following customers: employees see everything;\n"
                "   if website is activated, portal users may see project, tasks or issues followed by\n"
                "   them or by someone of their company\n")
    doc_count = fields.Integer(compute='_compute_attached_docs_count', string="Number of documents attached")
    date_start = fields.Date(string='Start Date')
    date = fields.Date(string='Expiration Date', index=True, track_visibility='onchange')
    subtask_project_id = fields.Many2one('project.project', string='Sub-task Project', ondelete="restrict",
        help="Choosing a sub-tasks project will both enable sub-tasks and set their default project (possibly the project itself)")

    # rating fields
    percentage_satisfaction_task = fields.Integer(
        compute='_compute_percentage_satisfaction_task', string="Happy % on Task", store=True, default=-1)
    percentage_satisfaction_project = fields.Integer(
        compute="_compute_percentage_satisfaction_project", string="Happy % on Project", store=True, default=-1)
    rating_request_deadline = fields.Datetime(compute='_compute_rating_request_deadline', store=True)
    rating_status = fields.Selection([('stage', 'Rating when changing stage'), ('periodic', 'Periodical Rating'), ('no','No rating')], 'Customer(s) Ratings', help="How to get the customer's feedbacks?\n"
                    "- Rating when changing stage: Email will be sent when a task/issue is pulled in another stage\n"
                    "- Periodical Rating: Email will be sent periodically\n\n"
                    "Don't forget to set up the mail templates on the stages for which you want to get the customer's feedbacks.", default="no", required=True)
    rating_status_period = fields.Selection([
        ('daily', 'Daily'), ('weekly', 'Weekly'), ('bimonthly', 'Twice a Month'),
        ('monthly', 'Once a Month'), ('quarterly', 'Quarterly'), ('yearly', 'Yearly')
    ], 'Rating Frequency')

    portal_show_rating = fields.Boolean('Rating visible publicly', copy=False, oldname='website_published')

    _sql_constraints = [
        ('project_date_greater', 'check(date >= date_start)', 'Error! project start-date must be lower than project end-date.')
    ]

    def _compute_access_url(self):
        super(Project, self)._compute_access_url()
        for project in self:
            project.access_url = '/my/project/%s' % project.id

    def _compute_access_warning(self):
        super(Project, self)._compute_access_warning()
        for project in self.filtered(lambda x: x.privacy_visibility != 'portal'):
            project.access_warning = _(
                "The project cannot be shared with the recipient(s) because the privacy of the project is too restricted. Set the privacy to 'Visible by following customers' in order to make it accessible by the recipient(s).")

    @api.depends('tasks.rating_ids.rating', 'tasks.rating_ids.parent_res_id')
    def _compute_percentage_satisfaction_project(self):
        res = self.env['project.task']._compute_parent_rating_percentage_satisfaction(self, rating_satisfaction_days=30)
        for project in self:
            project.percentage_satisfaction_project = res[project.id]

    #TODO JEM: Only one field can be kept since project only contains task
    @api.depends('tasks.rating_ids.rating', 'tasks.rating_ids.parent_res_id')
    def _compute_percentage_satisfaction_task(self):
        res = self.env['project.task']._compute_parent_rating_percentage_satisfaction(self)
        for project in self:
            project.percentage_satisfaction_task = res[project.id]

    @api.depends('rating_status', 'rating_status_period')
    def _compute_rating_request_deadline(self):
        periods = {'daily': 1, 'weekly': 7, 'bimonthly': 15, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        for project in self:
            project.rating_request_deadline = fields.datetime.now() + timedelta(days=periods.get(project.rating_status_period, 0))

    @api.model
    def _map_tasks_default_valeus(self, task):
        """ get the default value for the copied task on project duplication """
        return {
            'stage_id': task.stage_id.id,
            'name': task.name,
        }

    @api.multi
    def map_tasks(self, new_project_id):
        """ copy and map tasks from old to new project """
        tasks = self.env['project.task']
        # We want to copy archived task, but do not propagate an active_test context key
        task_ids = self.env['project.task'].with_context(active_test=False).search([('project_id', '=', self.id)]).ids
        for task in self.env['project.task'].browse(task_ids):
            # preserve task name and stage, normally altered during copy
            defaults = self._map_tasks_default_valeus(task)
            tasks += task.copy(defaults)
        return self.browse(new_project_id).write({'tasks': [(6, 0, tasks.ids)]})

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)") % (self.name)
        project = super(Project, self).copy(default)
        for follower in self.message_follower_ids:
            project.message_subscribe(partner_ids=follower.partner_id.ids, subtype_ids=follower.subtype_ids.ids)
        if 'tasks' not in default:
            self.map_tasks(project.id)
        return project

    @api.model
    def create(self, vals):
        # Prevent double project creation
        self = self.with_context(mail_create_nosubscribe=True)
        project = super(Project, self).create(vals)
        if not vals.get('subtask_project_id'):
            project.subtask_project_id = project.id
        if project.privacy_visibility == 'portal' and project.partner_id:
            project.message_subscribe(project.partner_id.ids)
        return project

    @api.multi
    def write(self, vals):
        # directly compute is_favorite to dodge allow write access right
        if 'is_favorite' in vals:
            vals.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)
        res = super(Project, self).write(vals) if vals else True
        if 'active' in vals:
            # archiving/unarchiving a project does it on its tasks, too
            self.with_context(active_test=False).mapped('tasks').write({'active': vals['active']})
        if vals.get('partner_id') or vals.get('privacy_visibility'):
            for project in self.filtered(lambda project: project.privacy_visibility == 'portal'):
                project.message_subscribe(project.partner_id.ids)
        return res

    @api.multi
    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        """ Subscribe to all existing active tasks when subscribing to a project """
        res = super(Project, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
        project_subtypes = self.env['mail.message.subtype'].browse(subtype_ids) if subtype_ids else None
        task_subtypes = project_subtypes.mapped('parent_id').ids if project_subtypes else None
        if not subtype_ids or task_subtypes:
            self.mapped('tasks').message_subscribe(
                partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=task_subtypes)
        return res

    @api.multi
    def message_unsubscribe(self, partner_ids=None, channel_ids=None):
        """ Unsubscribe from all tasks when unsubscribing from a project """
        self.mapped('tasks').message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)
        return super(Project, self).message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)

    # ---------------------------------------------------
    #  Actions
    # ---------------------------------------------------

    @api.multi
    def toggle_favorite(self):
        favorite_projects = not_fav_projects = self.env['project.project'].sudo()
        for project in self:
            if self.env.user in project.favorite_user_ids:
                favorite_projects |= project
            else:
                not_fav_projects |= project

        # Project User has no write access for project.
        not_fav_projects.write({'favorite_user_ids': [(4, self.env.uid)]})
        favorite_projects.write({'favorite_user_ids': [(3, self.env.uid)]})

    @api.multi
    def open_tasks(self):
        ctx = dict(self._context)
        ctx.update({'search_default_project_id': self.id})
        action = self.env['ir.actions.act_window'].for_xml_id('project', 'act_project_project_2_project_task_all')
        return dict(action, context=ctx)

    @api.multi
    def action_view_all_rating(self):
        """ return the action to see all the rating of the project, and activate default filters """
        if self.portal_show_rating:
            return {
                'type': 'ir.actions.act_url',
                'name': "Redirect to the Website Projcet Rating Page",
                'target': 'self',
                'url': "/project/rating/%s" % (self.id,)
            }
        action = self.env['ir.actions.act_window'].for_xml_id('project', 'rating_rating_action_view_project_rating')
        action['name'] = _('Ratings of %s') % (self.name,)
        action_context = safe_eval(action['context']) if action['context'] else {}
        action_context.update(self._context)
        action_context['search_default_parent_res_name'] = self.name
        action_context.pop('group_by', None)
        return dict(action, context=action_context)

    # ---------------------------------------------------
    # Rating business
    # ---------------------------------------------------

    # This method should be called once a day by the scheduler
    @api.model
    def _send_rating_all(self):
        projects = self.search([('rating_status', '=', 'periodic'), ('rating_request_deadline', '<=', fields.Datetime.now())])
        projects.mapped('task_ids')._send_task_rating_mail()
        projects._compute_rating_request_deadline()


class Task(models.Model):
    _name = "project.task"
    _description = "Task"
    _date_name = "date_start"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'rating.mixin']
    _mail_post_access = 'read'
    _order = "priority desc, sequence, id desc"

    @api.model
    def default_get(self, fields_list):
        result = super(Task, self).default_get(fields_list)
        # force some parent values, if needed
        if 'parent_id' in result and result['parent_id']:
            result.update(self._subtask_values_from_parent(result['parent_id']))
        return result

    @api.model
    def _get_default_partner(self):
        if 'default_project_id' in self.env.context:
            default_project_id = self.env['project.project'].browse(self.env.context['default_project_id'])
            return default_project_id.exists().partner_id

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        return self.stage_find(project_id, [('fold', '=', False)])

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = [('id', 'in', stages.ids)]
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain

        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    active = fields.Boolean(default=True)
    name = fields.Char(string='Title', track_visibility='always', required=True, index=True)
    description = fields.Html(string='Description')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ], default='0', index=True, string="Priority")
    sequence = fields.Integer(string='Sequence', index=True, default=10,
        help="Gives the sequence order when displaying a list of tasks.")
    stage_id = fields.Many2one('project.task.type', string='Stage', ondelete='restrict', track_visibility='onchange', index=True,
        default=_get_default_stage_id, group_expand='_read_group_stage_ids',
        domain="[('project_ids', '=', project_id)]", copy=False)
    tag_ids = fields.Many2many('project.tags', string='Tags', oldname='categ_ids')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True)
    kanban_state_label = fields.Char(compute='_compute_kanban_state_label', string='Kanban State Label', track_visibility='onchange')
    create_date = fields.Datetime("Created On", readonly=True, index=True)
    write_date = fields.Datetime("Last Updated On", readonly=True, index=True)
    date_start = fields.Datetime(string='Starting Date',
    default=fields.Datetime.now,
    index=True, copy=False)
    date_end = fields.Datetime(string='Ending Date', index=True, copy=False)
    date_assign = fields.Datetime(string='Assigning Date', index=True, copy=False, readonly=True)
    date_deadline = fields.Date(string='Deadline', index=True, copy=False, track_visibility='onchange')
    date_last_stage_update = fields.Datetime(string='Last Stage Update',
        default=fields.Datetime.now,
        index=True,
        copy=False,
        readonly=True)
    project_id = fields.Many2one('project.project',
        string='Project',
        default=lambda self: self.env.context.get('default_project_id'),
        index=True,
        track_visibility='onchange',
        change_default=True)
    notes = fields.Text(string='Notes')
    planned_hours = fields.Float("Planned Hours", help='It is the time planned to achieve the task. If this document has sub-tasks, it means the time needed to achieve this tasks and its childs.',track_visibility='onchange')
    subtask_planned_hours = fields.Float("Subtasks", compute='_compute_subtask_planned_hours', help="Computed using sum of hours planned of all subtasks created from main task. Usually these hours are less or equal to the Planned Hours (of main task).")
    user_id = fields.Many2one('res.users',
        string='Assigned to',
        default=lambda self: self.env.uid,
        index=True, track_visibility='always')
    partner_id = fields.Many2one('res.partner',
        string='Customer',
        default=lambda self: self._get_default_partner())
    manager_id = fields.Many2one('res.users', string='Project Manager', related='project_id.user_id', readonly=True, related_sudo=False)
    company_id = fields.Many2one('res.company',
        string='Company',
        default=lambda self: self.env['res.company']._company_default_get())
    color = fields.Integer(string='Color Index')
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True, related_sudo=False)
    attachment_ids = fields.One2many('ir.attachment', compute='_compute_attachment_ids', string="Main Attachments",
        help="Attachment that don't come from message.")
    # In the domain of displayed_image_id, we couln't use attachment_ids because a one2many is represented as a list of commands so we used res_model & res_id
    displayed_image_id = fields.Many2one('ir.attachment', domain="[('res_model', '=', 'project.task'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]", string='Cover Image')
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked Explanation', readonly=True, related_sudo=False)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid Explanation', readonly=True, related_sudo=False)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing Explanation', readonly=True, related_sudo=False)
    parent_id = fields.Many2one('project.task', string='Parent Task', index=True)
    child_ids = fields.One2many('project.task', 'parent_id', string="Sub-tasks", context={'active_test': False})
    subtask_project_id = fields.Many2one('project.project', related="project_id.subtask_project_id", string='Sub-task Project', readonly=True)
    subtask_count = fields.Integer("Sub-task count", compute='_compute_subtask_count')
    email_from = fields.Char(string='Email', help="These people will receive email.", index=True)
    email_cc = fields.Char(string='Watchers Emails', help="""These email addresses will be added to the CC field of all inbound
        and outbound emails for this record before being sent. Separate multiple email addresses with a comma""")
    # Computed field about working time elapsed between record creation and assignation/closing.
    working_hours_open = fields.Float(compute='_compute_elapsed', string='Working hours to assign', store=True, group_operator="avg")
    working_hours_close = fields.Float(compute='_compute_elapsed', string='Working hours to close', store=True, group_operator="avg")
    working_days_open = fields.Float(compute='_compute_elapsed', string='Working days to assign', store=True, group_operator="avg")
    working_days_close = fields.Float(compute='_compute_elapsed', string='Working days to close', store=True, group_operator="avg")
    # customer portal: include comment and incoming emails in communication history
    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', 'in', ['email', 'comment'])])

    _constraints = [(models.BaseModel._check_recursion, 'Circular references are not permitted between tasks and sub-tasks', ['parent_id'])]

    def _compute_attachment_ids(self):
        for task in self:
            attachment_ids = self.env['ir.attachment'].search([('res_id', '=', task.id), ('res_model', '=', 'project.task')]).ids
            message_attachment_ids = task.mapped('message_ids.attachment_ids').ids  # from mail_thread
            task.attachment_ids = list(set(attachment_ids) - set(message_attachment_ids))

    @api.multi
    @api.depends('create_date', 'date_end', 'date_assign')
    def _compute_elapsed(self):
        task_linked_to_calendar = self.filtered(
            lambda task: task.project_id.resource_calendar_id and task.create_date
        )
        for task in task_linked_to_calendar:
            dt_create_date = fields.Datetime.from_string(task.create_date)

            if task.date_assign:
                dt_date_assign = fields.Datetime.from_string(task.date_assign)
                task.working_hours_open = task.project_id.resource_calendar_id.get_work_hours_count(
                        dt_create_date, dt_date_assign, compute_leaves=True)
                task.working_days_open = task.working_hours_open / 24.0

            if task.date_end:
                dt_date_end = fields.Datetime.from_string(task.date_end)
                task.working_hours_close = task.project_id.resource_calendar_id.get_work_hours_count(
                    dt_create_date, dt_date_end, compute_leaves=True)
                task.working_days_close = task.working_hours_close / 24.0

        (self - task_linked_to_calendar).update(dict.fromkeys(
            ['working_hours_open', 'working_hours_close', 'working_days_open', 'working_days_close'], 0.0))

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for task in self:
            if task.kanban_state == 'normal':
                task.kanban_state_label = task.legend_normal
            elif task.kanban_state == 'blocked':
                task.kanban_state_label = task.legend_blocked
            else:
                task.kanban_state_label = task.legend_done

    def _compute_access_url(self):
        super(Task, self)._compute_access_url()
        for task in self:
            task.access_url = '/my/task/%s' % task.id

    def _compute_access_warning(self):
        super(Task, self)._compute_access_warning()
        for task in self.filtered(lambda x: x.project_id.privacy_visibility != 'portal'):
            task.access_warning = _(
                "The task cannot be shared with the recipient(s) because the privacy of the project is too restricted. Set the privacy of the project to 'Visible by following customers' in order to make it accessible by the recipient(s).")

    @api.depends('child_ids.planned_hours')
    def _compute_subtask_planned_hours(self):
        for task in self:
            task.subtask_planned_hours = sum(task.child_ids.mapped('planned_hours'))

    @api.depends('child_ids')
    def _compute_subtask_count(self):
        """ Note: since we accept only one level subtask, we can use a read_group here """
        task_data = self.env['project.task'].read_group([('parent_id', 'in', self.ids)], ['parent_id'], ['parent_id'])
        mapping = dict((data['parent_id'][0], data['parent_id_count']) for data in task_data)
        for task in self:
            task.subtask_count = mapping.get(task.id, 0)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.email_from = self.partner_id.email

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        if self.parent_id:
            for field_name in self._subtask_implied_fields():
                self[field_name] = self.parent_id[field_name]

    @api.onchange('project_id')
    def _onchange_project(self):
        if self.project_id:
            if not self.parent_id and self.project_id.partner_id:
                self.partner_id = self.project_id.partner_id
            if self.project_id not in self.stage_id.project_ids:
                self.stage_id = self.stage_find(self.project_id.id, [('fold', '=', False)])
        else:
            self.stage_id = False

    @api.onchange('user_id')
    def _onchange_user(self):
        if self.user_id:
            self.date_start = fields.Datetime.now()

    @api.constrains('parent_id', 'child_ids')
    def _check_subtask_level(self):
        for task in self:
            if task.parent_id and task.child_ids:
                raise ValidationError(_('Task %s cannot have several subtask levels.' % (task.name,)))

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)") % self.name
        return super(Task, self).copy(default)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for task in self:
            if not task._check_recursion():
                raise ValidationError(_('Error! You cannot create recursive hierarchy of task(s).'))

    @api.model
    def get_empty_list_help(self, help):
        tname = _("task")
        project_id = self.env.context.get('default_project_id', False)
        if project_id:
            name = self.env['project.project'].browse(project_id).label_tasks
            if name: tname = name.lower()

        self = self.with_context(
            empty_list_help_id=self.env.context.get('default_project_id'),
            empty_list_help_model='project.project',
            empty_list_help_document_name=tname,
        )
        return super(Task, self).get_empty_list_help(help)

    # ----------------------------------------
    # Case management
    # ----------------------------------------

    def stage_find(self, section_id, domain=[], order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        # collect all section_ids
        section_ids = []
        if section_id:
            section_ids.append(section_id)
        section_ids.extend(self.mapped('project_id').ids)
        search_domain = []
        if section_ids:
            search_domain = [('|')] * (len(section_ids) - 1)
            for section_id in section_ids:
                search_domain.append(('project_ids', '=', section_id))
        search_domain += list(domain)
        # perform search, return the first found
        return self.env['project.task.type'].search(search_domain, order=order, limit=1).id

    # ------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------

    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        context = dict(self.env.context, mail_create_nolog=True)
        # force some parent values, if needed
        if 'parent_id' in vals and vals['parent_id']:
            vals.update(self._subtask_values_from_parent(vals['parent_id']))
        # for default stage
        if vals.get('project_id') and not context.get('default_project_id'):
            context['default_project_id'] = vals.get('project_id')
        # user_id change: update date_assign
        if vals.get('user_id'):
            vals['date_assign'] = fields.Datetime.now()
        # Stage change: Update date_end if folded stage
        if vals.get('stage_id'):
            vals.update(self.update_date_end(vals['stage_id']))
        task = super(Task, self.with_context(context)).create(vals)
        return task

    @api.multi
    def write(self, vals):
        now = fields.Datetime.now()
        # subtask: force some parent values, if needed
        if 'parent_id' in vals and vals['parent_id']:
            vals.update(self._subtask_values_from_parent(vals['parent_id']))
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals.update(self.update_date_end(vals['stage_id']))
            vals['date_last_stage_update'] = now
            # reset kanban state when changing stage
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
        # user_id change: update date_assign
        if vals.get('user_id') and 'date_assign' not in vals:
            vals['date_assign'] = now

        result = super(Task, self).write(vals)
        # rating on stage
        if 'stage_id' in vals and vals.get('stage_id'):
            self.filtered(lambda x: x.project_id.rating_status == 'stage')._send_task_rating_mail(force_send=True)
        # subtask: update subtask according to parent values
        subtask_values_to_write = self._subtask_write_values(vals)
        if subtask_values_to_write:
            subtasks = self.filtered(lambda task: not task.parent_id).mapped('child_ids')
            if subtasks:
                subtasks.write(subtask_values_to_write)
        return result

    def update_date_end(self, stage_id):
        project_task_type = self.env['project.task.type'].browse(stage_id)
        if project_task_type.fold:
            return {'date_end': fields.Datetime.now()}
        return {'date_end': False}

    # ---------------------------------------------------
    # Subtasks
    # ---------------------------------------------------

    @api.model
    def _subtask_implied_fields(self):
        """ Return the list of field name to apply on subtask when changing parent_id or when updating parent task. """
        return ['partner_id', 'email_from']

    @api.multi
    def _subtask_write_values(self, values):
        """ Return the values to write on subtask when `values` is written on parent tasks
            :param values: dict of values to write on parent
        """
        result = {}
        for field_name in self._subtask_implied_fields():
            if field_name in values:
                result[field_name] = values[field_name]
        return result

    def _subtask_values_from_parent(self, parent_id):
        """ Get values for substask implied field of the given"""
        result = {}
        parent_task = self.env['project.task'].browse(parent_id)
        for field_name in self._subtask_implied_fields():
            result[field_name] = parent_task[field_name]
        return self._convert_to_write(result)

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    @api.multi
    def _track_template(self, tracking):
        res = super(Task, self)._track_template(tracking)
        test_task = self[0]
        changes, tracking_value_ids = tracking[test_task.id]
        if 'stage_id' in changes and test_task.stage_id.mail_template_id:
            res['stage_id'] = (test_task.stage_id.mail_template_id, {
                'auto_delete_message': True,
                'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
                'notif_layout': 'mail.mail_notification_light'
            })
        return res

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'kanban_state_label' in init_values and self.kanban_state == 'blocked':
            return 'project.mt_task_blocked'
        elif 'kanban_state_label' in init_values and self.kanban_state == 'done':
            return 'project.mt_task_ready'
        elif 'stage_id' in init_values and self.stage_id and self.stage_id.sequence <= 1:  # start stage -> new
            return 'project.mt_task_new'
        elif 'stage_id' in init_values:
            return 'project.mt_task_stage'
        return super(Task, self)._track_subtype(init_values)

    @api.multi
    def _notify_get_groups(self, message, groups):
        """ Handle project users and managers recipients that can assign
        tasks and create new one directly from notification emails. Also give
        access button to portal users and portal customers. If they are notified
        they should probably have access to the document. """
        groups = super(Task, self)._notify_get_groups(message, groups)

        self.ensure_one()

        project_user_group_id = self.env.ref('project.group_project_user').id
        new_group = (
            'group_project_user',
            lambda pdata: pdata['type'] == 'user' and project_user_group_id in pdata['groups'],
            {},
        )

        if not self.user_id and not self.stage_id.fold:
            take_action = self._notify_get_action_link('assign')
            project_actions = [{'url': take_action, 'title': _('I take it')}]
            new_group[2]['actions'] = project_actions

        groups = [new_group] + groups

        for group_name, group_method, group_data in groups:
            if group_name == 'customer':
                continue
            group_data['has_button_access'] = True

        return groups

    @api.multi
    def _notify_get_reply_to(self, default=None, records=None, company=None, doc_names=None):
        """ Override to set alias of tasks to their project if any. """
        aliases = self.sudo().mapped('project_id')._notify_get_reply_to(default=default, records=None, company=company, doc_names=None)
        res = {task.id: aliases.get(task.project_id.id) for task in self}
        leftover = self.filtered(lambda rec: not rec.project_id)
        if leftover:
            res.update(super(Task, leftover)._notify_get_reply_to(default=default, records=None, company=company, doc_names=doc_names))
        return res

    @api.multi
    def email_split(self, msg):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        aliases = self.mapped('project_id.alias_name')
        return [x for x in email_list if x.split('@')[0] not in aliases]

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(self.env.context or {})
        create_context['default_user_id'] = False
        if custom_values is None:
            custom_values = {}
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'planned_hours': 0.0,
            'partner_id': msg.get('author_id')
        }
        defaults.update(custom_values)

        task = super(Task, self.with_context(create_context)).message_new(msg, custom_values=defaults)
        email_list = task.email_split(msg)
        partner_ids = [p for p in task._find_partner_from_emails(email_list, force_create=False) if p]
        task.message_subscribe(partner_ids)
        return task

    @api.multi
    def message_update(self, msg, update_vals=None):
        """ Override to update the task according to the email. """
        email_list = self.email_split(msg)
        partner_ids = [p for p in self._find_partner_from_emails(email_list, force_create=False) if p]
        self.message_subscribe(partner_ids)
        return super(Task, self).message_update(msg, update_vals=update_vals)

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(Task, self).message_get_suggested_recipients()
        for task in self:
            if task.partner_id:
                reason = _('Customer Email') if task.partner_id.email else _('Customer')
                task._message_add_suggested_recipient(recipients, partner=task.partner_id, reason=reason)
            elif task.email_from:
                task._message_add_suggested_recipient(recipients, email=task.email_from, reason=_('Customer Email'))
        return recipients

    @api.multi
    def _notify_specific_email_values(self, message):
        res = super(Task, self)._notify_specific_email_values(message)
        try:
            headers = safe_eval(res.get('headers', dict()))
        except Exception:
            headers = {}
        if self.project_id:
            current_objects = [h for h in headers.get('X-Odoo-Objects', '').split(',') if h]
            current_objects.insert(0, 'project.project-%s, ' % self.project_id.id)
            headers['X-Odoo-Objects'] = ','.join(current_objects)
        if self.tag_ids:
            headers['X-Odoo-Tags'] = ','.join(self.tag_ids.mapped('name'))
        res['headers'] = repr(headers)
        return res

    def _message_post_after_hook(self, message, *args, **kwargs):
        if self.email_from and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(lambda partner: partner.email == self.email_from)
            if new_partner:
                self.search([
                    ('partner_id', '=', False),
                    ('email_from', '=', new_partner.email),
                    ('stage_id.fold', '=', False)]).write({'partner_id': new_partner.id})
        return super(Task, self)._message_post_after_hook(message, *args, **kwargs)

    def action_assign_to_me(self):
        self.write({'user_id': self.env.user.id})

    def action_open_parent_task(self):
        return {
            'name': _('Parent Task'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.task',
            'res_id': self.parent_id.id,
            'type': 'ir.actions.act_window'
        }

    def action_subtask(self):
        action = self.env.ref('project.project_task_action_sub_task').read()[0]
        ctx = self.env.context.copy()
        ctx.update({
            'default_parent_id': self.id,
            'default_project_id': self.env.context.get('project_id', self.project_id.id),
            'default_name': self.env.context.get('name', self.name) + ':',
            'default_partner_id': self.env.context.get('partner_id', self.partner_id.id),
            'search_default_project_id': self.env.context.get('project_id', self.project_id.id),
        })
        action['context'] = ctx
        action['domain'] = [('id', 'child_of', self.id), ('id', '!=', self.id)]
        return action

    # ---------------------------------------------------
    # Rating business
    # ---------------------------------------------------

    def _send_task_rating_mail(self, force_send=False):
        for task in self:
            rating_template = task.stage_id.rating_template_id
            if rating_template:
                task.rating_send_request(rating_template, lang=task.partner_id.lang, force_send=force_send)

    def rating_get_partner_id(self):
        res = super(Task, self).rating_get_partner_id()
        if not res and self.project_id.partner_id:
            return self.project_id.partner_id
        return res

    @api.multi
    def rating_apply(self, rate, token=None, feedback=None, subtype=None):
        return super(Task, self).rating_apply(rate, token=token, feedback=feedback, subtype="project.mt_task_rating")

    def rating_get_parent(self):
        return 'project_id'


class ProjectTags(models.Model):
    """ Tags of project's tasks """
    _name = "project.tags"
    _description = "Project Tags"

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]
