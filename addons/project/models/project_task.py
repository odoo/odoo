# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from pytz import UTC
from collections import defaultdict
from datetime import timedelta, datetime, time

from odoo import api, Command, fields, models, tools, SUPERUSER_ID, _
from odoo.addons.rating.models import rating_data
from odoo.addons.web_editor.tools import handle_history_divergence
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.osv import expression
from odoo.tools import format_list, SQL, LazyTranslate
from odoo.addons.resource.models.utils import filter_domain_leaf
from odoo.addons.project.controllers.project_sharing_chatter import ProjectSharingChatter
from odoo.addons.mail.tools.discuss import Store

_lt = LazyTranslate(__name__)

PROJECT_TASK_READABLE_FIELDS = {
    'id',
    'active',
    'priority',
    'project_id',
    'display_in_project',
    'color',
    'allow_task_dependencies',
    'subtask_count',
    'email_from',
    'create_date',
    'write_date',
    'company_id',
    'displayed_image_id',
    'display_name',
    'portal_user_names',
    'user_ids',
    'display_parent_task_button',
    'current_user_same_company_partner',
    'allow_milestones',
    'milestone_id',
    'has_late_and_unreached_milestone',
    'date_assign',
    'dependent_ids',
    'message_is_follower',
    'recurring_task',
    'closed_subtask_count',
    'dependent_tasks_count',
    'depend_on_ids',
    'depend_on_count',
    'repeat_interval',
    'repeat_unit',
    'repeat_type',
    'repeat_until',
    'recurrence_id',
    'recurring_count',
    'duration_tracking',
    'display_follow_button',
}

PROJECT_TASK_WRITABLE_FIELDS = {
    'name',
    'description',
    'partner_id',
    'date_deadline',
    'date_last_stage_update',
    'tag_ids',
    'sequence',
    'stage_id',
    'child_ids',
    'parent_id',
    'priority',
    'state',
    'is_closed',
}

CLOSED_STATES = {
    '1_done': 'Done',
    '1_canceled': 'Cancelled',
}


class ProjectTask(models.Model):
    _name = 'project.task'
    _description = "Task"
    _date_name = "date_assign"
    _inherit = [
        'portal.mixin',
        'mail.thread.cc',
        'mail.activity.mixin',
        'rating.mixin',
        'mail.tracking.duration.mixin',
        'html.field.history.mixin',
    ]
    _mail_post_access = 'read'
    _order = "priority desc, sequence, date_deadline asc, id desc"
    _primary_email = 'email_from'
    _systray_view = 'activity'
    _track_duration_field = 'stage_id'

    def _get_versioned_fields(self):
        return [ProjectTask.description.name]

    @api.model
    def _get_default_partner_id(self, project=None, parent=None):
        if parent and parent.partner_id:
            return parent.partner_id.id
        if project and project.partner_id:
            return project.partner_id.id
        return False

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        return self.stage_find(project_id, order="fold, sequence, id")

    @api.model
    def _default_personal_stage_type_id(self):
        default_id = self.env.context.get('default_personal_stage_type_ids')
        return (default_id or self.env['project.task.type'].search([('user_id', '=', self.env.user.id)], limit=1).ids or [False])[0]

    @api.model
    def _default_user_ids(self):
        return self.env.context.keys() & {'default_personal_stage_type_ids', 'default_personal_stage_type_id'} and self.env.user

    @api.model
    def _default_company_id(self):
        if self._context.get('default_project_id'):
            return self.env['project.project'].browse(self._context['default_project_id']).company_id
        return False

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        search_domain = [('id', 'in', stages.ids)]
        if 'default_project_id' in self.env.context and not self._context.get('subtask_action'):
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain

        stage_ids = stages.sudo()._search(search_domain, order=stages._order)
        return stages.browse(stage_ids)

    @api.model
    def _read_group_personal_stage_type_ids(self, stages, domain):
        return stages.search(['|', ('id', 'in', stages.ids), ('user_id', '=', self.env.user.id)])

    active = fields.Boolean(default=True, export_string_translation=False)
    name = fields.Char(string='Title', tracking=True, required=True, index='trigram')
    description = fields.Html(string='Description', sanitize_attributes=False)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'High'),
    ], default='0', index=True, string="Priority", tracking=True)
    sequence = fields.Integer(string='Sequence', default=10, export_string_translation=False)
    stage_id = fields.Many2one('project.task.type', string='Stage', compute='_compute_stage_id',
        store=True, readonly=False, ondelete='restrict', tracking=True, index=True,
        default=_get_default_stage_id, group_expand='_read_group_stage_ids',
        domain="[('project_ids', '=', project_id)]")
    tag_ids = fields.Many2many('project.tags', string='Tags')

    state = fields.Selection([
        ('01_in_progress', 'In Progress'),
        ('02_changes_requested', 'Changes Requested'),
        ('03_approved', 'Approved'),
        *CLOSED_STATES.items(),
        ('04_waiting_normal', 'Waiting'),
    ], string='State', copy=False, default='01_in_progress', required=True, compute='_compute_state', inverse='_inverse_state', readonly=False, store=True, index=True, recursive=True, tracking=True)
    is_closed = fields.Boolean("Closed state", compute='_compute_is_closed', search='_search_is_closed')

    create_date = fields.Datetime("Created On", readonly=True, index=True)
    write_date = fields.Datetime("Last Updated On", readonly=True)
    date_end = fields.Datetime(string='Ending Date', index=True, copy=False)
    date_assign = fields.Datetime(string='Assigning Date', copy=False, readonly=True,
        help="Date on which this task was last assigned (or unassigned). Based on this, you can get statistics on the time it usually takes to assign tasks.")
    date_deadline = fields.Datetime(string='Deadline', index=True, tracking=True, copy=False)

    date_last_stage_update = fields.Datetime(string='Last Stage Update',
        index=True,
        copy=False,
        readonly=True,
        help="Date on which the state of your task has last been modified.\n"
            "Based on this information you can identify tasks that are stalling and get statistics on the time it usually takes to move tasks from one stage/state to another.")

    project_id = fields.Many2one('project.project', string='Project', domain="['|', ('company_id', '=', False), ('company_id', '=?',  company_id)]",
                                 compute="_compute_project_id", store=True, precompute=True, recursive=True, readonly=False, index=True, tracking=True, change_default=True, falsy_value_label=_lt("🔒 Private"))
    display_in_project = fields.Boolean(compute='_compute_display_in_project', store=True, export_string_translation=False)
    task_properties = fields.Properties('Properties', definition='project_id.task_properties_definition', copy=True)
    allocated_hours = fields.Float("Allocated Time", tracking=True)
    subtask_allocated_hours = fields.Float("Sub-tasks Allocated Time", compute='_compute_subtask_allocated_hours', export_string_translation=False,
        help="Sum of the hours allocated for all the sub-tasks (and their own sub-tasks) linked to this task. Usually less than or equal to the allocated hours of this task.")
    # Tracking of this field is done in the write function
    user_ids = fields.Many2many('res.users', relation='project_task_user_rel', column1='task_id', column2='user_id',
        string='Assignees', context={'active_test': False}, tracking=True, default=_default_user_ids, domain="[('share', '=', False), ('active', '=', True)]", falsy_value_label=_lt("👤 Unassigned"))
    # User names displayed in project sharing views
    portal_user_names = fields.Char(compute='_compute_portal_user_names', compute_sudo=True, search='_search_portal_user_names', export_string_translation=False)
    # Second Many2many containing the actual personal stage for the current user
    # See project_task_stage_personal.py for the model defininition
    personal_stage_type_ids = fields.Many2many('project.task.type', 'project_task_user_rel', column1='task_id', column2='stage_id',
        ondelete='restrict', group_expand='_read_group_personal_stage_type_ids', copy=False,
        domain="[('user_id', '=', uid)]", string='Personal Stages', export_string_translation=False)
    # Personal Stage computed from the user
    personal_stage_id = fields.Many2one('project.task.stage.personal', string='Personal Stage State', compute_sudo=False,
        compute='_compute_personal_stage_id', help="The current user's personal stage.")
    # This field is actually a related field on personal_stage_id.stage_id
    # However due to the fact that personal_stage_id is computed, the orm throws out errors
    # saying the field cannot be searched.
    personal_stage_type_id = fields.Many2one('project.task.type', string='Personal Stage',
        compute='_compute_personal_stage_type_id', inverse='_inverse_personal_stage_type_id', store=False,
        search='_search_personal_stage_type_id', default=_default_personal_stage_type_id,
        help="The current user's personal task stage.", domain="[('user_id', '=', uid)]")
    partner_id = fields.Many2one('res.partner',
        string='Customer', recursive=True, tracking=True, compute='_compute_partner_id', store=True, readonly=False,
        domain="['|', ('company_id', '=?', company_id), ('company_id', '=', False)]", )
    partner_phone = fields.Char(
        compute='_compute_partner_phone', inverse='_inverse_partner_phone',
        string="Contact Number", readonly=False, store=True, copy=False
    )
    email_cc = fields.Char(help='Email addresses that were in the CC of the incoming emails from this task and that are not currently linked to an existing customer.')
    company_id = fields.Many2one('res.company', string='Company', compute='_compute_company_id', store=True, readonly=False, recursive=True, copy=True, default=_default_company_id)
    color = fields.Integer(string='Color Index', export_string_translation=False)
    rating_active = fields.Boolean(string='Project Rating Status', related="project_id.rating_active")
    attachment_ids = fields.One2many(
        'ir.attachment',
        compute='_compute_attachment_ids',
        string="Attachments",
        export_string_translation=False,
        help="Attachments that don't come from a message",
    )
    # In the domain of displayed_image_id, we couln't use attachment_ids because a one2many is represented as a list of commands so we used res_model & res_id
    displayed_image_id = fields.Many2one('ir.attachment', domain="[('res_model', '=', 'project.task'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]", string='Cover Image')

    parent_id = fields.Many2one('project.task', string='Parent Task', index=True, domain="['!', ('id', 'child_of', id)]", tracking=True)
    child_ids = fields.One2many('project.task', 'parent_id', string="Sub-tasks", domain="[('recurring_task', '=', False)]", export_string_translation=False)
    subtask_count = fields.Integer("Sub-task Count", compute='_compute_subtask_count', export_string_translation=False)
    closed_subtask_count = fields.Integer("Closed Sub-tasks Count", compute='_compute_subtask_count', export_string_translation=False)
    project_privacy_visibility = fields.Selection(related='project_id.privacy_visibility', string="Project Visibility", tracking=False)
    subtask_completion_percentage = fields.Float(compute="_compute_subtask_completion_percentage", export_string_translation=False)
    # Computed field about working time elapsed between record creation and assignation/closing.
    working_hours_open = fields.Float(compute='_compute_elapsed', string='Working Hours to Assign', digits=(16, 2), store=True, aggregator="avg")
    working_hours_close = fields.Float(compute='_compute_elapsed', string='Working Hours to Close', digits=(16, 2), store=True, aggregator="avg")
    working_days_open = fields.Float(compute='_compute_elapsed', string='Working Days to Assign', store=True, aggregator="avg")
    working_days_close = fields.Float(compute='_compute_elapsed', string='Working Days to Close', store=True, aggregator="avg")
    # customer portal: include comment and (incoming/outgoing) emails in communication history
    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', 'in', ['email', 'comment', 'email_outgoing'])], export_string_translation=False)
    allow_milestones = fields.Boolean(related='project_id.allow_milestones', export_string_translation=False)
    milestone_id = fields.Many2one(
        'project.milestone',
        'Milestone',
        domain="[('project_id', '=', project_id)]",
        compute='_compute_milestone_id',
        readonly=False,
        store=True,
        tracking=True,
        index='btree_not_null',
        help="Deliver your services automatically when a milestone is reached by linking it to a sales order item."
    )
    has_late_and_unreached_milestone = fields.Boolean(
        compute='_compute_has_late_and_unreached_milestone',
        search='_search_has_late_and_unreached_milestone',
        export_string_translation=False,
    )
    # Task Dependencies fields
    allow_task_dependencies = fields.Boolean(related='project_id.allow_task_dependencies', export_string_translation=False)
    # Tracking of this field is done in the write function
    depend_on_ids = fields.Many2many('project.task', relation="task_dependencies_rel", column1="task_id",
                                     column2="depends_on_id", string="Blocked By", tracking=True, copy=False,
                                     domain="[('project_id', '!=', False), ('id', '!=', id)]")
    depend_on_count = fields.Integer(string="Depending on Tasks", compute='_compute_depend_on_count', compute_sudo=True)
    closed_depend_on_count = fields.Integer(string="Closed Depending on Tasks", compute='_compute_depend_on_count', compute_sudo=True)
    dependent_ids = fields.Many2many('project.task', relation="task_dependencies_rel", column1="depends_on_id",
                                     column2="task_id", string="Block", copy=False,
                                     domain="[('project_id', '!=', False), ('id', '!=', id)]", export_string_translation=False)
    dependent_tasks_count = fields.Integer(string="Dependent Tasks", compute='_compute_dependent_tasks_count', export_string_translation=False)

    # Project sharing fields
    display_parent_task_button = fields.Boolean(compute='_compute_display_parent_task_button', compute_sudo=True, export_string_translation=False)
    current_user_same_company_partner = fields.Boolean(compute='_compute_current_user_same_company_partner', compute_sudo=True, export_string_translation=False)
    display_follow_button = fields.Boolean(compute='_compute_display_follow_button', compute_sudo=True, export_string_translation=False)

    # recurrence fields
    recurring_task = fields.Boolean(string="Recurrent")
    recurring_count = fields.Integer(string="Tasks in Recurrence", compute='_compute_recurring_count')
    recurrence_id = fields.Many2one('project.task.recurrence', copy=False)
    repeat_interval = fields.Integer(string='Repeat Every', default=1, compute='_compute_repeat', compute_sudo=True, readonly=False)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', compute='_compute_repeat', compute_sudo=True, readonly=False)
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'Until'),
    ], default="forever", string="Until", compute='_compute_repeat', compute_sudo=True, readonly=False)
    repeat_until = fields.Date(string="End Date", compute='_compute_repeat', compute_sudo=True, readonly=False)

    # Quick creation shortcuts
    display_name = fields.Char(
        inverse='_inverse_display_name',
        help="""Use these keywords in the title to set new tasks:\n
            #tags Set tags on the task
            @user Assign the task to a user
            ! Set the task a high priority\n
            Make sure to use the right format and order e.g. Improve the configuration screen #feature #v16 @Mitchell !""",
    )
    link_preview_name = fields.Char(compute='_compute_link_preview_name', export_string_translation=False)

    _recurring_task_has_no_parent = models.Constraint(
        'CHECK (NOT (recurring_task IS TRUE AND parent_id IS NOT NULL))',
        'A subtask cannot be recurrent.',
    )
    _private_task_has_no_parent = models.Constraint(
        'CHECK (NOT (project_id IS NULL AND parent_id IS NOT NULL))',
        'A private task cannot have a parent.',
    )

    @api.constrains('company_id', 'partner_id')
    def _ensure_company_consistency_with_partner(self):
        """ Ensures that the company of the task is valid for the partner. """
        for task in self:
            if task.partner_id and task.partner_id.company_id and task.company_id and task.company_id != task.partner_id.company_id:
                raise ValidationError(_('The task and the associated partner must be linked to the same company.'))

    @api.constrains('child_ids', 'project_id')
    def _ensure_super_task_is_not_private(self):
        """ Ensures that the company of the task is valid for the partner. """
        for task in self:
            if not task.project_id and task.subtask_count:
                raise ValidationError(_('This task has sub-tasks, so it can\'t be private.'))

    @property
    def SELF_READABLE_FIELDS(self):
        return PROJECT_TASK_READABLE_FIELDS | self.SELF_WRITABLE_FIELDS

    @property
    def SELF_WRITABLE_FIELDS(self):
        return PROJECT_TASK_WRITABLE_FIELDS

    @api.depends('parent_id.project_id')
    def _compute_project_id(self):
        self.env.remove_to_compute(self._fields['display_in_project'], self)
        for task in self:
            if not task.display_in_project and task.parent_id and task.parent_id.project_id != task.project_id:
                task.project_id = task.parent_id.project_id

    @api.depends('project_id', 'parent_id')
    def _compute_display_in_project(self):
        for record in self:
            record.display_in_project = record.project_id and (
                not record.parent_id or record.project_id != record.parent_id.project_id
            )

    @api.depends('stage_id', 'depend_on_ids.state', 'project_id.allow_task_dependencies')
    def _compute_state(self):
        for task in self:
            dependent_open_tasks = []
            if task.allow_task_dependencies:
                dependent_open_tasks = [dependent_task for dependent_task in task.depend_on_ids if dependent_task.state not in CLOSED_STATES]
            # if one of the blocking task is in a blocking state
            if dependent_open_tasks:
                # here we check that the blocked task is not already in a closed state (if the task is already done we don't put it in waiting state)
                if task.state not in CLOSED_STATES:
                    task.state = '04_waiting_normal'
            # if the task as no blocking dependencies and is in waiting_normal, the task goes back to in progress
            elif task.state not in CLOSED_STATES:
                task.state = '01_in_progress'

    @api.depends('state')
    def _compute_is_closed(self):
        for task in self:
            task.is_closed = task.state in CLOSED_STATES

    def _search_is_closed(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError(_(
                "The search does not support operator %(operator)s or value %(value)s.",
                operator=operator,
                value=value,
            ))
        if (operator == '!=' and value) or (operator == '=' and not value):
            searched_states = self.OPEN_STATES
        else:
            searched_states = list(CLOSED_STATES.keys())
        domain = [
            ('state', 'in', searched_states)
        ]
        return domain


    @property
    def OPEN_STATES(self):
        """ Return a list of the technical names complementing the CLOSED_STATES, a.k.a the open states """
        return list(set(self._fields['state'].get_values(self.env)) - set(CLOSED_STATES))

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.state != '04_waiting_normal':
            self.state = '01_in_progress'

    def is_blocked_by_dependences(self):
        return any(blocking_task.state not in CLOSED_STATES for blocking_task in self.depend_on_ids)

    def _inverse_state(self):
        last_task_id_per_recurrence_id = self.recurrence_id._get_last_task_id_per_recurrence_id()
        tasks = self.filtered(lambda task: task.state in CLOSED_STATES and task.id == last_task_id_per_recurrence_id.get(task.recurrence_id.id))
        self.env['project.task.recurrence']._create_next_occurrences(tasks)

    @api.depends_context('uid')
    @api.depends('user_ids')
    def _compute_personal_stage_id(self):
        # An user may only access his own 'personal stage' and there can only be one pair (user, task_id)
        personal_stages = self.env['project.task.stage.personal'].search([('user_id', '=', self.env.uid), ('task_id', 'in', self.ids)])
        self.personal_stage_id = False
        for personal_stage in personal_stages:
            personal_stage.task_id.personal_stage_id = personal_stage

    @api.depends('personal_stage_id')
    def _compute_personal_stage_type_id(self):
        for task in self:
            task.personal_stage_type_id = task.personal_stage_id.stage_id

    def _inverse_personal_stage_type_id(self):
        for task in self:
            task.personal_stage_id.stage_id = task.personal_stage_type_id

    @api.model
    def _search_personal_stage_type_id(self, operator, value):
        return [('personal_stage_type_ids', operator, value)]

    @api.model
    def _get_default_personal_stage_create_vals(self, user_id):
        return [
            {'sequence': 1, 'name': _('Inbox'), 'user_id': user_id, 'fold': False},
            {'sequence': 2, 'name': _('Today'), 'user_id': user_id, 'fold': False},
            {'sequence': 3, 'name': _('This Week'), 'user_id': user_id, 'fold': False},
            {'sequence': 4, 'name': _('This Month'), 'user_id': user_id, 'fold': False},
            {'sequence': 5, 'name': _('Later'), 'user_id': user_id, 'fold': False},
            {'sequence': 6, 'name': _('Done'), 'user_id': user_id, 'fold': True},
            {'sequence': 7, 'name': _('Cancelled'), 'user_id': user_id, 'fold': True},
        ]

    def _populate_missing_personal_stages(self):
        # Assign the default personal stage for those that are missing
        personal_stages_without_stage = self.env['project.task.stage.personal'].sudo().search([('task_id', 'in', self.ids), ('stage_id', '=', False)])
        if personal_stages_without_stage:
            user_ids = personal_stages_without_stage.user_id
            personal_stage_by_user = defaultdict(lambda: self.env['project.task.stage.personal'])
            for personal_stage in personal_stages_without_stage:
                personal_stage_by_user[personal_stage.user_id] |= personal_stage
            for user_id in user_ids:
                stage = self.env['project.task.type'].sudo().search([('user_id', '=', user_id.id)], limit=1)
                # In the case no stages have been found, we create the default stages for the user
                if not stage:
                    stages = self.env['project.task.type'].sudo().with_context(lang=user_id.partner_id.lang, default_project_ids=False).create(
                        self.with_context(lang=user_id.partner_id.lang)._get_default_personal_stage_create_vals(user_id.id)
                    )
                    stage = stages[0]
                personal_stage_by_user[user_id].sudo().write({'stage_id': stage.id})

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # Set task notification based on project notification preference if user follow the project
        if not subtype_ids:
            project_followers = self.project_id.message_follower_ids.filtered(lambda f: f.partner_id.id in partner_ids)
            for project_follower in project_followers:
                project_subtypes = project_follower.subtype_ids
                task_subtypes = (project_subtypes.mapped('parent_id') | project_subtypes.filtered(lambda sub: sub.internal or sub.default)).ids if project_subtypes else None
                partner_ids.remove(project_follower.partner_id.id)
                super().message_subscribe(project_follower.partner_id.ids, task_subtypes)
        return super().message_subscribe(partner_ids, subtype_ids)

    @api.constrains('depend_on_ids')
    def _check_no_cyclic_dependencies(self):
        if self._has_cycle('depend_on_ids'):
            raise ValidationError(_("Two tasks cannot depend on each other."))

    @api.model
    def _get_recurrence_fields(self):
        return [
            'repeat_interval',
            'repeat_unit',
            'repeat_type',
            'repeat_until',
        ]

    @api.depends('recurring_task')
    def _compute_repeat(self):
        rec_fields = self._get_recurrence_fields()
        defaults = self.default_get(rec_fields)
        for task in self:
            for f in rec_fields:
                if task.recurrence_id:
                    task[f] = task.recurrence_id.sudo()[f]
                else:
                    if task.recurring_task:
                        task[f] = defaults.get(f)
                    else:
                        task[f] = False

    def _is_recurrence_valid(self):
        self.ensure_one()
        return self.repeat_interval > 0 and\
                (self.repeat_type != 'until' or self.repeat_until and self.repeat_until > fields.Date.today())

    @api.depends('recurrence_id')
    def _compute_recurring_count(self):
        self.recurring_count = 0
        recurring_tasks = self.filtered(lambda l: l.recurrence_id)
        count = self.env['project.task']._read_group([('recurrence_id', 'in', recurring_tasks.recurrence_id.ids)], ['recurrence_id'], ['__count'])
        tasks_count = {recurrence.id: count for recurrence, count in count}
        for task in recurring_tasks:
            task.recurring_count = tasks_count.get(task.recurrence_id.id, 0)

    @api.depends('depend_on_ids')
    def _compute_depend_on_count(self):
        tasks_with_dependency = self.filtered('allow_task_dependencies')
        tasks_without_dependency = self - tasks_with_dependency
        tasks_without_dependency.depend_on_count = 0
        tasks_without_dependency.closed_depend_on_count = 0
        if not any(self._ids):
            for task in self:
                task.depend_on_count = len(task.depend_on_ids)
                task.closed_depend_on_count = len(task.depend_on_ids.filtered(lambda r: r.state in CLOSED_STATES))
            return
        if tasks_with_dependency:
            # need the sudo for project sharing
            total_and_closed_depend_on_count = {
                dependent_on.id: (count, sum(s in CLOSED_STATES for s in states))
                for dependent_on, states, count in self.env['project.task']._read_group(
                    [('dependent_ids', 'in', tasks_with_dependency.ids)],
                    ['dependent_ids'],
                    ['state:array_agg', '__count'],
                )
            }
            for task in tasks_with_dependency:
                task.depend_on_count, task.closed_depend_on_count = total_and_closed_depend_on_count.get(task._origin.id or task.id, (0, 0))

    @api.depends('dependent_ids')
    def _compute_dependent_tasks_count(self):
        tasks_with_dependency = self.filtered('allow_task_dependencies')
        (self - tasks_with_dependency).dependent_tasks_count = 0
        if tasks_with_dependency:
            group_dependent = self.env['project.task']._read_group([
                ('depend_on_ids', 'in', tasks_with_dependency.ids),
                ('is_closed', '=', False),
            ], ['depend_on_ids'], ['__count'])
            dependent_tasks_count_dict = {
                depend_on.id: count
                for depend_on, count in group_dependent
            }
            for task in tasks_with_dependency:
                task.dependent_tasks_count = dependent_tasks_count_dict.get(task.id, 0)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('Error! You cannot create a recursive hierarchy of tasks.'))

    def _get_attachments_search_domain(self):
        self.ensure_one()
        return [('res_id', '=', self.id), ('res_model', '=', 'project.task')]

    def _compute_attachment_ids(self):
        for task in self:
            attachment_ids = self.env['ir.attachment'].search(task._get_attachments_search_domain()).ids
            message_attachment_ids = task.mapped('message_ids.attachment_ids').ids  # from mail_thread
            task.attachment_ids = [(6, 0, list(set(attachment_ids) - set(message_attachment_ids)))]

    @api.depends('create_date', 'date_end', 'date_assign')
    def _compute_elapsed(self):
        task_linked_to_calendar = self.filtered(
            lambda task: task.project_id.resource_calendar_id and task.create_date
        )
        for task in task_linked_to_calendar:
            dt_create_date = fields.Datetime.from_string(task.create_date)

            if task.date_assign:
                dt_date_assign = fields.Datetime.from_string(task.date_assign)
                duration_data = task.project_id.resource_calendar_id.get_work_duration_data(dt_create_date, dt_date_assign, compute_leaves=True)
                task.working_hours_open = duration_data['hours']
                task.working_days_open = duration_data['days']
            else:
                task.working_hours_open = 0.0
                task.working_days_open = 0.0

            if task.date_end:
                dt_date_end = fields.Datetime.from_string(task.date_end)
                duration_data = task.project_id.resource_calendar_id.get_work_duration_data(dt_create_date, dt_date_end, compute_leaves=True)
                task.working_hours_close = duration_data['hours']
                task.working_days_close = duration_data['days']
            else:
                task.working_hours_close = 0.0
                task.working_days_close = 0.0

        (self - task_linked_to_calendar).update(dict.fromkeys(
            ['working_hours_open', 'working_hours_close', 'working_days_open', 'working_days_close'], 0.0))

    def _compute_access_url(self):
        super()._compute_access_url()
        for task in self:
            task.access_url = f'/my/tasks/{task.id}'

    def _compute_access_warning(self):
        super()._compute_access_warning()
        for task in self.filtered(lambda x: x.project_id.privacy_visibility != 'portal'):
            visibility_field = self.env['ir.model.fields'].search([('model', '=', 'project.project'), ('name', '=', 'privacy_visibility')], limit=1)
            visibility_public = self.env['ir.model.fields.selection'].search([('field_id', '=', visibility_field.id), ('value', '=', 'portal')])
            task.access_warning = _(
                "The task cannot be shared with the recipient(s) because the privacy of the project is too restricted. Set the privacy of the project to '%(visibility)s' in order to make it accessible by the recipient(s).",
                visibility=visibility_public.name,
            )

    @api.depends('child_ids.allocated_hours')
    def _compute_subtask_allocated_hours(self):
        for task in self:
            task.subtask_allocated_hours = sum(task.child_ids.mapped('allocated_hours'))

    @api.depends('child_ids')
    def _compute_subtask_count(self):
        if not any(self._ids):
            for task in self:
                task.subtask_count, task.closed_subtask_count = len(task.child_ids), len(task.child_ids.filtered(lambda r: r.state in CLOSED_STATES))
            return
        total_and_closed_subtask_count_per_parent_id = {
            parent.id: (count, sum(s in CLOSED_STATES for s in states))
            for parent, states, count in self.env['project.task']._read_group(
                [('parent_id', 'in', self.ids)],
                ['parent_id'],
                ['state:array_agg', '__count'],
            )
        }
        for task in self:
            task.subtask_count, task.closed_subtask_count = total_and_closed_subtask_count_per_parent_id.get(task.id, (0, 0))

    @api.depends('partner_id.phone', 'partner_id.mobile')
    def _compute_partner_phone(self):
        for task in self:
            task.partner_phone = task.partner_id.mobile or task.partner_id.phone or False

    def _inverse_partner_phone(self):
        for task in self:
            if task.partner_id:
                if task.partner_id.mobile or not task.partner_id.phone:
                    task.partner_id.mobile = task.partner_phone
                else:
                    task.partner_id.phone = task.partner_phone

    @api.onchange('company_id')
    def _onchange_task_company(self):
        if self.project_id.company_id and self.project_id.company_id != self.company_id:
            self.project_id = False

    @api.depends('project_id.company_id', 'parent_id.company_id')
    def _compute_company_id(self):
        for task in self:
            if not task.parent_id and not task.project_id:
                continue
            task.company_id = task.project_id.company_id or task.parent_id.company_id

    @api.depends('project_id')
    def _compute_stage_id(self):
        for task in self:
            project = task.project_id or task.parent_id.project_id
            if project:
                if project not in task.stage_id.project_ids:
                    task.stage_id = task.stage_find(project.id, [('fold', '=', False)])
            else:
                task.stage_id = False

    @api.depends('user_ids')
    def _compute_portal_user_names(self):
        """ This compute method allows to see all the names of assigned users to each task contained in `self`.

            When we are in the project sharing feature, the `user_ids` contains only the users if we are a portal user.
            That is, only the users in the same company of the current user.
            So this compute method is a related of `user_ids.name` but with more records that the portal user
            can normally see.
            (In other words, this compute is only used in project sharing views to see all assignees for each task)
        """
        if self._origin:
            # fetch 'user_ids' in superuser mode (and override value in cache
            # browse is useful to avoid miscache because of the newIds contained in self
            self.invalidate_recordset(fnames=['user_ids'])
            self._origin.fetch(['user_ids'])
        for task in self.with_context(prefetch_fields=False):
            task.portal_user_names = format_list(self.env, task.user_ids.mapped('name'))

    def _search_portal_user_names(self, operator, value):
        if operator != 'ilike' and not isinstance(value, str):
            raise ValidationError(_('Not Implemented.'))

        sql = SQL("""(
            SELECT task_user.task_id
              FROM project_task_user_rel task_user
        INNER JOIN res_users users ON task_user.user_id = users.id
        INNER JOIN res_partner partners ON partners.id = users.partner_id
             WHERE partners.name ILIKE %s
        )""", f"%{value}%")
        return [('id', 'in', sql)]

    def _compute_display_parent_task_button(self):
        accessible_parent_tasks = self.parent_id.with_user(self.env.user)._filtered_access('read')
        for task in self:
            task.display_parent_task_button = task.parent_id in accessible_parent_tasks

    def _compute_current_user_same_company_partner(self):
        commercial_partner_id = self.env.user.partner_id.commercial_partner_id
        for task in self:
            task.current_user_same_company_partner = task.partner_id and commercial_partner_id == task.partner_id.commercial_partner_id

    def _compute_display_follow_button(self):
        if not self.env.user.share:
            self.display_follow_button = False
            return
        project_collaborator_read_group = self.env['project.collaborator']._read_group(
            [('project_id', 'in', self.project_id.ids), ('partner_id', '=', self.env.user.partner_id.id)],
            ['project_id'],
            ['limited_access:bool_and'],
        )
        limited_access_per_project_id = dict(project_collaborator_read_group)
        for task in self:
            task.display_follow_button = not limited_access_per_project_id.get(task.project_id, True)

    def _get_group_pattern(self):
        return {
            'tags_and_users': r'\s([#@]%s[^\s]+)',
            'priority': r'\s(!)',
        }

    def _prepare_pattern_groups(self):
        group = self._get_group_pattern()
        return [
            group['tags_and_users'] % '',
            group['priority'],
        ]

    def _get_groups_patterns(self):
        return [
            r'(?:%s)*' % ('|').join(self._prepare_pattern_groups()),
        ]

    def _get_cannot_start_with_patterns(self):
        return [r'(?![#!@\s])']

    def _extract_tags_and_users(self):
        tags = []
        users = []
        tags_and_users_group = self._get_group_pattern()['tags_and_users']
        for word in re.findall(tags_and_users_group % '', self.display_name):
            (tags if word.startswith('#') else users).append(word[1:])
        users_to_keep = []
        user_ids = []
        for user in users:
            matched_users = self.env['res.users'].name_search(user)
            if len(matched_users) == 1:
                user_ids.append(Command.link(matched_users[0][0]))
            else:
                users_to_keep.append(r'%s\b' % user)
        self.user_ids = user_ids
        if tags:
            domain = expression.OR([[('name', '=ilike', tag)] for tag in tags])
            existing_tags = self.env['project.tags'].search(domain)
            existing_tags_names = {tag.name.lower() for tag in existing_tags}
            new_tags_names = {tag for tag in tags if tag.lower() not in existing_tags_names}
            self.tag_ids = [Command.set(existing_tags.ids)] + [Command.create({'name': name}) for name in new_tags_names]
        pattern = tags_and_users_group % ('(?!%s)' % ('|').join(users_to_keep) if users_to_keep else '')
        self.display_name, dummy = re.subn(pattern, '', self.display_name)

    def _extract_priority(self):
        self.priority = "1"
        priority_group = self._get_group_pattern()['priority']
        self.display_name, dummy = re.subn(priority_group, '', self.display_name)

    def _get_groups(self):
        return [
            lambda task: task._extract_tags_and_users(),
            lambda task: task._extract_priority(),
        ]

    def _inverse_display_name(self):
        for task in self:
            pattern = re.compile(r'^%s.+?%s$' % (
                ('').join(task._get_cannot_start_with_patterns()),
                ('').join(task._get_groups_patterns()))
            )
            match = pattern.match(task.display_name)
            if match:
                for group, extract_data in enumerate(task._get_groups(), start=1):
                    if match.group(group):
                        extract_data(task)
                task.name = task.display_name.strip()

    def _compute_link_preview_name(self):
        for task in self:
            link_preview_name = task.display_name
            if task.project_id:
                link_preview_name += f' | {task.project_id.sudo().name}'
            task.link_preview_name = link_preview_name

    def copy_data(self, default=None):
        default = dict(default or {})
        default.update({
            'depend_on_ids': False,
            'dependent_ids': False,
        })
        vals_list = super().copy_data(default=default)
        not_project_user = not self.env.user.has_group('project.group_project_user')
        if not_project_user:
            vals_list = [{k: v for k, v in vals.items() if k in self.SELF_READABLE_FIELDS} for vals in vals_list]

        milestone_mapping = self.env.context.get('milestone_mapping', {})
        for task, vals in zip(self, vals_list):

            if not default.get('stage_id'):
                vals['stage_id'] = task.stage_id.id
            if 'active' not in default and not task['active'] and not self.env.context.get('copy_project'):
                vals['active'] = True
            vals['name'] = task.name if self.env.context.get('copy_project') else _("%s (copy)", task.name)
            if task.recurrence_id and not default.get('recurrence_id'):
                vals['recurrence_id'] = task.recurrence_id.copy().id
            if task.allow_milestones:
                vals['milestone_id'] = milestone_mapping.get(vals['milestone_id'], vals['milestone_id'])
            if task.child_ids and not default.get('child_ids'):
                default = {
                    'parent_id': False,
                }
                vals['child_ids'] = [Command.create(child_id.copy_data(default)[0]) for child_id in task.child_ids]
        return vals_list

    def _create_task_mapping(self, copied_tasks):
        """
        Thanks to the way create and command.create is handled, when a task with 2 children is copied, we have the guarantee that the children of the
        copied task will have the same index in the child_ids recordset. We can use this behavior to create a mapping containing all the original tasks and their copy.
        :return:
            task_mapping: a dict containing the mapping of the original task ids and their copied task (k: original_task.id, v: new_task)
            task_dependencies: a dict containing the ids of the dependencies of the original task when they have one.
            (k: original_task_id, v: [original_task.depend_on_ids.ids, original_task.dependent_ids.ids]
        """
        task_mapping, task_dependencies = {}, {}
        for original_task, copied_task in zip(self, copied_tasks):
            task_mapping[original_task.id] = copied_task
            if original_task.allow_task_dependencies and (original_task.depend_on_ids or original_task.dependent_ids):
                task_dependencies[original_task.id] = [original_task.depend_on_ids.ids, original_task.dependent_ids.ids]
            if original_task.child_ids:
                # If the task has children, we have to call the method create_task_mapping to get their ids and dependencies mapping too.
                children_mapping, children_dependencies = original_task.child_ids._create_task_mapping(copied_task.child_ids)
                task_mapping.update(children_mapping)
                task_dependencies.update(children_dependencies)
        return task_mapping, task_dependencies

    def _portal_get_parent_hash_token(self, pid):
        return self.project_id._sign_token(pid)

    def _resolve_copied_dependencies(self, copied_tasks):
        task_mapping, task_dependencies = self._create_task_mapping(copied_tasks)

        for original_task_id, (depend_on_ids, dependant_ids) in task_dependencies.items():
            # If one of the task_id in the dependencies mapping is also a key of the task_mapping, it means that this task was copied too.
            # In this case, we should exchange this id with the id of the corresponding copied task
            task_mapping[original_task_id].depend_on_ids = [
                task_id if task_id not in task_mapping else task_mapping[task_id].id
                for task_id in depend_on_ids
            ]
            task_mapping[original_task_id].dependent_ids = [
                task_id if task_id not in task_mapping else task_mapping[task_id].id
                for task_id in dependant_ids
            ]

    def copy(self, default=None):
        default = default or {}
        copied_tasks = super(ProjectTask, self.with_context(
            mail_auto_subscribe_no_notify=True,
            mail_create_nosubscribe=True,
            mail_create_nolog=True,
        )).copy(default=default)

        self._resolve_copied_dependencies(copied_tasks)

        return copied_tasks

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
        return super().get_empty_list_help(help)

    # ----------------------------------------
    # Case management
    # ----------------------------------------

    def stage_find(self, section_id, domain=[], order='sequence, id'):
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
    def fields_get(self, allfields=None, attributes=None):
        fields = super().fields_get(allfields=allfields, attributes=attributes)
        if not self.env.user._is_portal():
            return fields
        readable_fields = self.SELF_READABLE_FIELDS
        public_fields = {field_name: description for field_name, description in fields.items() if field_name in readable_fields}

        writable_fields = self.SELF_WRITABLE_FIELDS
        for field_name, description in public_fields.items():
            if field_name not in writable_fields and not description.get('readonly', False):
                # If the field is not in Writable fields and it is not readonly then we force the readonly to True
                description['readonly'] = True

        return public_fields

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of fields_get making fields readonly for portal users
        makes the view cache dependent on the fact the user has the group portal or not"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.user._is_portal(),)

    @api.model
    def default_get(self, default_fields):
        vals = super().default_get(default_fields)

        # prevent creating new task in the waiting state
        if 'state' in default_fields and vals.get('state') == '04_waiting_normal':
            vals['state'] = '01_in_progress'

        if 'repeat_until' in default_fields:
            vals['repeat_until'] = fields.Date.today() + timedelta(days=7)

        if 'partner_id' in vals and not vals['partner_id']:
            # if the default_partner_id=False or no default_partner_id then we search the partner based on the project and parent
            project_id = vals.get('project_id')
            parent_id = vals.get('parent_id', self.env.context.get('default_parent_id'))
            if project_id or parent_id:
                partner_id = self._get_default_partner_id(
                    project_id and self.env['project.project'].browse(project_id),
                    parent_id and self.env['project.task'].browse(parent_id)
                )
                if partner_id:
                    vals['partner_id'] = partner_id
        project_id = vals.get('project_id', self.env.context.get('default_project_id'))
        if project_id:
            project = self.env['project.project'].browse(project_id)
            if 'company_id' in default_fields and 'default_project_id' not in self.env.context:
                vals['company_id'] = project.sudo().company_id
        elif 'default_user_ids' not in self.env.context and 'user_ids' in default_fields:
            user_ids = vals.get('user_ids', [])
            user_ids.append(Command.link(self.env.user.id))
            vals['user_ids'] = user_ids

        return vals

    def _ensure_fields_are_accessible(self, fields, operation='read', check_group_user=True):
        """" ensure all fields are accessible by the current user

            This method checks if the portal user can access to all fields given in parameter.
            By default, it checks if the current user is a portal user and then checks if all fields are accessible for this user.

            :param fields: list of fields to check if the current user can access.
            :param operation: contains either 'read' to check readable fields or 'write' to check writable fields.
            :param check_group_user: contains boolean value.
                - True, if the method has to check if the current user is a portal one.
                - False if we are sure the user is a portal user,
        """
        assert operation in ('read', 'write'), 'Invalid operation'
        if fields and (not check_group_user or self.env.user._is_portal()) and not self.env.su:
            unauthorized_fields = set(fields) - (self.SELF_READABLE_FIELDS if operation == 'read' else self.SELF_WRITABLE_FIELDS)
            if unauthorized_fields:
                unauthorized_field_list = format_list(self.env, list(unauthorized_fields))
                if operation == 'read':
                    error_message = _('You cannot read the following fields on tasks: %(field_list)s', field_list=unauthorized_field_list)
                else:
                    error_message = _('You cannot write on the following fields on tasks: %(field_list)s', field_list=unauthorized_field_list)
                raise AccessError(error_message)

    def _has_field_access(self, field, operation):
        if not super()._has_field_access(field, operation):
            return False
        if not self.env.su and self.env.user._is_portal():
            # additional checks for portal users
            if operation == 'read':
                return field.name in self.SELF_READABLE_FIELDS
            if operation == 'write':
                return field.name in self.SELF_WRITABLE_FIELDS
        return True

    def _determine_fields_to_fetch(self, field_names, ignore_when_in_cache=False):
        if not self.env.su and self.env.user._is_portal():
            valid_names = self.SELF_READABLE_FIELDS
            field_names = [fname for fname in field_names if fname in valid_names]
        return super()._determine_fields_to_fetch(field_names, ignore_when_in_cache)

    def _get_portal_sudo_vals(self, vals, defaults=False):
        """ returns the values which must be written without and with sudo when a portal user creates / writes a task.
            :param vals: dict of {field: value}, the values to create/write
            :return: a tuple with 2 dicts:
                - the first with the values to write without sudo
                - the second with the values to write with sudo
        """
        vals_no_sudo = {key: val for key, val in vals.items() if self._fields[key].type in ('one2many', 'many2many')}
        if defaults:
            vals_no_sudo.update({
                key[8:]: value
                for key, value in self.env.context.items()
                if key.startswith('default_') and key[8:] in self.SELF_WRITABLE_FIELDS and self._fields[key[8:]].type in ('one2many', 'many2many')
            })
        vals_sudo = {key: val for key, val in vals.items() if key not in vals_no_sudo}
        return vals_no_sudo, vals_sudo

    @api.model
    def _get_portal_sudo_context(self):
        return {
            key: value for key, value in self.env.context.items()
            if key == 'default_project_id'
            or key == 'default_user_ids' and value is False
            or not key.startswith('default_')
            or key[8:] in (field for field in self.SELF_WRITABLE_FIELDS if self._fields[field].type not in ('one2many', 'many2many'))
        }

    def _set_stage_on_project_from_task(self):
        stage_ids_per_project = defaultdict(list)
        for task in self:
            if task.stage_id and task.stage_id not in task.project_id.type_ids and task.stage_id.id not in stage_ids_per_project[task.project_id]:
                stage_ids_per_project[task.project_id].append(task.stage_id.id)

        for project, stage_ids in stage_ids_per_project.items():
            project.write({'type_ids': [Command.link(stage_id) for stage_id in stage_ids]})

    def _load_records_create(self, vals_list):
        for vals in vals_list:
            if vals.get('recurring_task'):
                if not vals.get('recurrence_id'):
                    default_val = self.default_get(self._get_recurrence_fields())
                    vals.update(**default_val)
            project_id = vals.get('project_id')
            if project_id:
                self = self.with_context(default_project_id=project_id)
        tasks = super()._load_records_create(vals_list)

        return tasks

    @api.model_create_multi
    def create(self, vals_list):
        new_context = dict(self.env.context)
        default_personal_stage = new_context.pop('default_personal_stage_type_ids', False)
        default_project_id = new_context.get("default_project_id", False)
        self = self.with_context(new_context)

        is_portal_user = self.env.user._is_portal()
        if is_portal_user:
            self.browse().check_access('create')
        default_stage = dict()
        for vals in vals_list:
            project_id = vals.get('project_id') or default_project_id

            if vals.get('user_ids'):
                vals['date_assign'] = fields.Datetime.now()
                if not (vals.get('parent_id') or project_id):
                    user_ids = self._fields['user_ids'].convert_to_cache(vals.get('user_ids', []), self.env['project.task'])
                    if self.env.user.id not in list(user_ids) + [SUPERUSER_ID]:
                        vals['user_ids'] = [Command.set(list(user_ids) + [self.env.user.id])]
            if default_personal_stage and 'personal_stage_type_id' not in vals:
                vals['personal_stage_type_id'] = default_personal_stage[0]
            if not vals.get('name') and vals.get('display_name'):
                vals['name'] = vals['display_name']
            if is_portal_user:
                self._ensure_fields_are_accessible(vals.keys(), operation='write', check_group_user=False)

            if project_id and not "company_id" in vals:
                vals["company_id"] = self.env["project.project"].browse(
                    project_id
                ).company_id.id
            if not project_id and ("stage_id" in vals or self.env.context.get('default_stage_id')):
                vals["stage_id"] = False

            if project_id and "stage_id" not in vals:
                # 1) Allows keeping the batch creation of tasks
                # 2) Ensure the defaults are correct (and computed once by project),
                # by using default get (instead of _get_default_stage_id or _stage_find),
                if project_id not in default_stage:
                    default_stage[project_id] = self.with_context(
                        default_project_id=project_id
                    ).default_get(['stage_id']).get('stage_id')
                vals["stage_id"] = default_stage[project_id]

            # Stage change: Update date_end if folded stage and date_last_stage_update
            if vals.get('stage_id'):
                vals.update(self.update_date_end(vals['stage_id']))
                vals['date_last_stage_update'] = fields.Datetime.now()
            # recurrence
            rec_fields = vals.keys() & self._get_recurrence_fields()
            if rec_fields and vals.get('recurring_task') is True:
                rec_values = {rec_field: vals[rec_field] for rec_field in rec_fields}
                recurrence = self.env['project.task.recurrence'].create(rec_values)
                vals['recurrence_id'] = recurrence.id
        # The sudo is required for a portal user as the record creation
        # requires the read access on other models, as mail.template
        # in order to compute the field tracking
        was_in_sudo = self.env.su
        if is_portal_user:
            vals_list_no_sudo, vals_list = zip(*(self._get_portal_sudo_vals(vals, defaults=True) for vals in vals_list))
            self_no_sudo, self = self, self.sudo().with_context(self._get_portal_sudo_context())
        tasks = super(ProjectTask, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        if is_portal_user:
            for task, vals in zip(tasks.with_env(self_no_sudo.env), vals_list_no_sudo):
                task.write(vals)
        tasks._populate_missing_personal_stages()
        self._task_message_auto_subscribe_notify({task: task.user_ids - self.env.user for task in tasks})

        # in case we were already in sudo, we don't check the rights.
        if is_portal_user and not was_in_sudo:
            # since we use sudo to create tasks, we need to check
            # if the portal user could really create the tasks based on the ir rule.
            tasks.browse().with_user(self.env.user).check_access('create')
        current_partner = self.env.user.partner_id

        all_partner_emails = []
        for task in tasks:
            all_partner_emails += tools.email_normalize_all(task.email_cc)
        partners = self.env['res.partner'].search([('email', 'in', all_partner_emails)])
        partner_per_email = {
            partner.email: partner
            for partner in partners
            if not all(u.share for u in partner.user_ids)
        }
        if tasks.project_id:
            tasks.sudo()._set_stage_on_project_from_task()
        for task in tasks:
            if task.project_id.privacy_visibility == 'portal':
                task._portal_ensure_token()
            for follower in task.parent_id.message_follower_ids:
                task.message_subscribe(follower.partner_id.ids, follower.subtype_ids.ids)
            if current_partner not in task.message_partner_ids:
                task.message_subscribe(current_partner.ids)
            if task.email_cc:
                partners_with_internal_user = self.env['res.partner']
                for email in tools.email_normalize_all(task.email_cc):
                    new_partner = partner_per_email.get(email)
                    if new_partner:
                        partners_with_internal_user |= new_partner
                if not partners_with_internal_user:
                    continue
                task._send_email_notify_to_cc(partners_with_internal_user)
                task.message_subscribe(partners_with_internal_user.ids)
        return tasks

    def write(self, vals):
        if len(self) == 1:
            handle_history_divergence(self, 'description', vals)
        portal_can_write = False
        project_link_per_task_id = {}
        partner_ids = []
        if self.env.user._is_portal() and not self.env.su:
            # Check if all fields in vals are in SELF_WRITABLE_FIELDS
            self._ensure_fields_are_accessible(vals.keys(), operation='write', check_group_user=False)
            self.check_access('write')
            portal_can_write = True

        if 'milestone_id' in vals:
            # WARNING: has to be done after 'project_id' vals is written on subtasks
            milestone = self.env['project.milestone'].browse(vals['milestone_id'])

            # 1. Task for which the milestone is unvalid -> milestone_id is reset
            if 'project_id' not in vals:
                unvalid_milestone_tasks = self.filtered(lambda task: task.project_id != milestone.project_id) if vals['milestone_id'] else self.env['project.task']
            else:
                unvalid_milestone_tasks = self if not vals['milestone_id'] or milestone.project_id.id != vals['project_id'] else self.env['project.task']
            valid_milestone_tasks = self - unvalid_milestone_tasks
            if unvalid_milestone_tasks:
                unvalid_milestone_tasks.write({'milestone_id': False})
                if valid_milestone_tasks:
                    valid_milestone_tasks.write({'milestone_id': vals['milestone_id']})
                del vals['milestone_id']

            # 2. Parent's milestone is set to subtask with no milestone recursively
            subtasks_to_update = valid_milestone_tasks.child_ids.filtered(
                lambda task: (task not in self and \
                              not task.milestone_id and \
                              task.project_id == milestone.project_id and \
                              task.state not in CLOSED_STATES))

            # 3. If parent and child task share the same milestone, child task's milestone is updated when the parent one is changed
            # No need to check if state is changed in vals as it won't affect the subtasks selected for update
            if 'project_id' not in vals:
                subtasks_to_update |= valid_milestone_tasks.child_ids.filtered(
                    lambda task: (task not in self and \
                                  task.milestone_id == task.parent_id.milestone_id and \
                                  task.state not in CLOSED_STATES))
            else:
                subtasks_to_update |= valid_milestone_tasks.child_ids.filtered(
                    lambda task: (task not in self and \
                                  (not task.display_in_project or task.project_id.id == vals['project_id']) and \
                                  task.milestone_id == task.parent_id.milestone_id  and \
                                  task.state not in CLOSED_STATES))
            if subtasks_to_update:
                subtasks_to_update.write({'milestone_id': vals['milestone_id']})

        if vals.get('parent_id') in self.ids:
            raise UserError(_("Sorry. You can't set a task as its parent task."))

        # stage change: update date_last_stage_update
        now = fields.Datetime.now()
        if 'stage_id' in vals:
            if not 'project_id' in vals and self.filtered(lambda t: not t.project_id):
                raise UserError(_('You can only set a personal stage on a private task.'))

            vals.update(self.update_date_end(vals['stage_id']))
            vals['date_last_stage_update'] = now
        task_ids_without_user_set = set()
        if 'user_ids' in vals and 'date_assign' not in vals:
            # prepare update of date_assign after super call
            task_ids_without_user_set = {task.id for task in self if not task.user_ids}

        # recurrence fields
        rec_fields = vals.keys() & self._get_recurrence_fields()
        if rec_fields:
            rec_values = {rec_field: vals[rec_field] for rec_field in rec_fields}
            for task in self:
                if task.recurrence_id:
                    task.recurrence_id.write(rec_values)
                elif vals.get('recurring_task'):
                    recurrence = self.env['project.task.recurrence'].create(rec_values)
                    task.recurrence_id = recurrence.id

        if not vals.get('recurring_task', True) and self.recurrence_id:
            tasks_in_recurrence = self.recurrence_id.task_ids
            self.recurrence_id.unlink()
            tasks_in_recurrence.write({'recurring_task': False})

        # The sudo is required for a portal user as the record update
        # requires the write access on others models, as rating.rating
        # in order to keep the same name than the task.
        if portal_can_write:
            self_no_sudo, self = self, self.sudo().with_context(self._get_portal_sudo_context())
            vals_no_sudo, vals = self._get_portal_sudo_vals(vals)

        # Track user_ids to send assignment notifications
        old_user_ids = {t: t.user_ids for t in self.sudo()}

        if "personal_stage_type_id" in vals and not vals['personal_stage_type_id']:
            del vals['personal_stage_type_id']

        # sends an email to the 'Task Creation' subtype subscribers
        # When project_id is changed
        if vals.get('project_id'):
            project = self.env['project.project'].browse(vals.get('project_id'))
            notification_subtype_id = self.env['ir.model.data']._xmlid_to_res_id('project.mt_project_task_new')
            partner_ids = project.message_follower_ids.filtered(lambda follower: notification_subtype_id in follower.subtype_ids.ids).partner_id.ids
            if partner_ids:
                link_per_project_id = {}
                for task in self:
                    if task.project_id:
                        project_link = link_per_project_id.get(task.project_id.id)
                        if not project_link:
                            project_link = link_per_project_id[task.project_id.id] = task.project_id._get_html_link(title=task.project_id.display_name)
                        project_link_per_task_id[task.id] = project_link
        result = super().write(vals)
        if portal_can_write:
            super(ProjectTask, self_no_sudo).write(vals_no_sudo)

        if 'user_ids' in vals:
            self._populate_missing_personal_stages()

        # user_ids change: update date_assign
        if 'user_ids' in vals:
            for task in self:
                if not task.user_ids and task.date_assign:
                    task.date_assign = False
                elif 'date_assign' not in vals and task.id in task_ids_without_user_set:
                    task.date_assign = now

        # rating on stage
        if 'stage_id' in vals and vals.get('stage_id'):
            self.filtered(lambda x: x.project_id.rating_active and x.project_id.rating_status == 'stage')._send_task_rating_mail(force_send=True)

        if 'state' in vals:
            # specific use case: when the blocked task goes from 'forced' done state to a not closed state, we fix the state back to waiting
            for task in self:
                if task.allow_task_dependencies:
                    if task.is_blocked_by_dependences() and vals['state'] not in CLOSED_STATES and vals['state'] != '04_waiting_normal':
                        task.state = '04_waiting_normal'
                task.date_last_stage_update = now
        elif 'project_id' in vals:
            self.filtered(lambda t: t.state != '04_waiting_normal').state = '01_in_progress'

        # Do not recompute the state when changing the parent (to avoid resetting the state)
        if 'parent_id' in vals:
            self.env.remove_to_compute(self._fields['state'], self)

        self._task_message_auto_subscribe_notify({task: task.user_ids - old_user_ids[task] - self.env.user for task in self})

        if partner_ids:
            for task in self:
                project_link = project_link_per_task_id.get(task.id)
                if project_link:
                    body = _(
                        'Task Transferred from Project %(source_project)s to %(destination_project)s',
                        source_project=project_link,
                        destination_project=self.project_id._get_html_link(title=self.project_id.display_name),
                    )
                else:
                    body = _('Task Converted from To-Do')
                task.message_notify(
                    body=body,
                    partner_ids=partner_ids,
                    email_layout_xmlid='mail.mail_notification_layout',
                    record_name=task.display_name,
               )
        return result

    def unlink(self):
        # Add subtasks to batch of tasks to delete
        self |= self._get_all_subtasks()
        last_task_id_per_recurrence_id = self.recurrence_id._get_last_task_id_per_recurrence_id()
        for task in self:
            if task.id == last_task_id_per_recurrence_id.get(task.recurrence_id.id):
                task.recurrence_id.unlink()
        return super().unlink()

    def _where_calc(self, domain, active_test=True):
        """ Tasks views don't show the sub-tasks / ('display_in_project', '=', True).
            The pseudo-filter "Show Sub-tasks" adds the key 'show_subtasks' in the context.
            In that case, we pop the leaf from the domain.
        """
        if self.env.context.get('show_subtasks'):
            domain = filter_domain_leaf(domain, lambda field: field != 'display_in_project')
        return super()._where_calc(domain, active_test)

    def update_date_end(self, stage_id):
        project_task_type = self.env['project.task.type'].browse(stage_id)
        if project_task_type.fold:
            return {'date_end': fields.Datetime.now()}
        return {'date_end': False}

    def _search_on_comodel(self, domain, field, comodel, additional_domain=None):
        """ This method is called by `group_expand` methods, whose purpose is to add empty groups to the `read_group`
            (which otherwise returns groups containing records that match the domain).
            When specifically filtering on a comodel's field, the result of the `read_group` should contain all matching groups.
            However, if the search isn't filtered on any comodel's field, the result shouldn't be affected,
            which explains why we return `False` if `filtered_domain` is empty.

            Returns:
                False or recordset of the comodel given in parameter.
        """
        def _change_operator(domain):
            new_domain = []
            for dom in domain:
                if len(dom) == 3:
                    _, op, value = dom
                    op = "ilike" if op == "child_of" else op
                    if isinstance(value, list) and all(isinstance(val, int) for val in value):
                        new_domain.append(("id", op, value))
                    if isinstance(value, str) or (isinstance(value, list) and not all(isinstance(val, str) for val in value)):
                        new_domain.append(("name", op, value))
                    if isinstance(value, int):
                        if op == "=":
                            op = "in"
                        if op == "!=":
                            op = "not in"
                        new_domain.append(("id", op, [value]))
                else:
                    new_domain.append(dom)
            return new_domain

        filtered_domain = filter_domain_leaf(domain, lambda field_to_check: field_to_check in [
            field,
            f"{field}.id",
            f"{field}.name",
        ], {
            field: "name",
            f"{field}.id": "id",
            f"{field}.name": "name",
        })
        filtered_domain = _change_operator(filtered_domain)
        if not filtered_domain:
            return self.env[comodel]
        if additional_domain:
            filtered_domain = expression.AND([filtered_domain, additional_domain])
        return self.env[comodel].search(filtered_domain)

    # ---------------------------------------------------
    # Subtasks
    # ---------------------------------------------------

    @api.depends('parent_id.partner_id', 'project_id')
    def _compute_partner_id(self):
        """ Compute the partner_id when the tasks have no partner_id.

            Use the project partner_id if any, or else the parent task partner_id.
        """
        for task in self:
            if task.partner_id and not (task.project_id or task.parent_id):
                task.partner_id = False
                continue
            if not task.partner_id:
                task.partner_id = self._get_default_partner_id(task.project_id, task.parent_id)

    @api.depends('project_id')
    def _compute_milestone_id(self):
        for task in self:
            if task.project_id != task.milestone_id.project_id:
                task.milestone_id = task.parent_id.project_id == task.project_id and task.parent_id.milestone_id

    def _compute_has_late_and_unreached_milestone(self):
        if all(not task.allow_milestones for task in self):
            self.has_late_and_unreached_milestone = False
            return
        late_milestones = self.env['project.milestone'].sudo()._search([  # sudo is needed for the portal user in Project Sharing.
            ('id', 'in', self.milestone_id.ids),
            ('is_reached', '=', False),
            ('deadline', '<=', fields.Date.today()),
        ])
        for task in self:
            task.has_late_and_unreached_milestone = task.allow_milestones and task.milestone_id.id in late_milestones

    def _search_has_late_and_unreached_milestone(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError(_(
                "The search does not support operator %(operator)s or value %(value)s.",
                operator=operator,
                value=value,
            ))
        domain = [
            ('allow_milestones', '=', True),
            ('milestone_id', '!=', False),
            ('milestone_id.is_reached', '=', False),
            ('milestone_id.deadline', '!=', False), ('milestone_id.deadline', '<', fields.Date.today())
        ]
        if (operator == '!=' and value) or (operator == '=' and not value):
            domain.insert(0, expression.NOT_OPERATOR)
            domain = expression.distribute_not(domain)
        return domain

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals=msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        if self.stage_id:
            render_context['subtitles'].append(_('Stage: %s', self.stage_id.name))
        return render_context

    def _send_email_notify_to_cc(self, partners_to_notify):
        self.ensure_one()
        template_id = self.env['ir.model.data']._xmlid_to_res_id('project.task_invitation_follower', raise_if_not_found=False)
        if not template_id:
            return
        task_model_description = self.env['ir.model']._get(self._name).display_name
        values = {
            'object': self,
        }
        for partner in partners_to_notify:
            values['partner_name'] = partner.name
            assignation_msg = self.env['ir.qweb']._render('project.task_invitation_follower', values, minimal_qcontext=True)
            self.message_notify(
                subject=_('You have been invited to follow %s', self.display_name),
                body=assignation_msg,
                partner_ids=partner.ids,
                record_name=self.display_name,
                email_layout_xmlid='mail.mail_notification_layout',
                model_description=task_model_description,
                mail_auto_delete=True,
            )

    @api.model
    def _task_message_auto_subscribe_notify(self, users_per_task):
        if self.env.context.get('mail_auto_subscribe_no_notify'):
            return
        # Utility method to send assignation notification upon writing/creation.
        template_id = self.env['ir.model.data']._xmlid_to_res_id('project.project_message_user_assigned', raise_if_not_found=False)
        if not template_id:
            return
        task_model_description = self.env['ir.model']._get(self._name).display_name
        for task, users in users_per_task.items():
            if not users:
                continue
            values = {
                'object': task,
                'model_description': task_model_description,
                'access_link': task._notify_get_action_link('view'),
            }
            for user in users:
                values.update(assignee_name=user.sudo().name)
                assignation_msg = self.env['ir.qweb']._render('project.project_message_user_assigned', values, minimal_qcontext=True)
                assignation_msg = self.env['mail.render.mixin']._replace_local_links(assignation_msg)
                task.message_notify(
                    subject=_('You have been assigned to %s', task.display_name),
                    body=assignation_msg,
                    partner_ids=user.partner_id.ids,
                    record_name=task.display_name,
                    email_layout_xmlid='mail.mail_notification_layout',
                    model_description=task_model_description,
                    mail_auto_delete=False,
                )

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        if 'user_ids' not in updated_values:
            return []
        # Since the changes to user_ids becoming a m2m, the default implementation of this function
        #  could not work anymore, override the function to keep the functionality.
        new_followers = []
        # Normalize input to tuple of ids
        value = self._fields['user_ids'].convert_to_cache(updated_values.get('user_ids', []), self.env['project.task'], validate=False)
        users = self.env['res.users'].browse(value)
        for user in users:
            try:
                if user.partner_id:
                    # The you have been assigned notification is handled separately
                    new_followers.append((user.partner_id.id, default_subtype_ids, False))
            except Exception:
                pass
        return new_followers

    def _track_template(self, changes):
        res = super()._track_template(changes)
        test_task = self[0]
        if 'stage_id' in changes and test_task.stage_id.mail_template_id:
            res['stage_id'] = (test_task.stage_id.mail_template_id, {
                'auto_delete_keep_log': False,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
        return res

    def _creation_subtype(self):
        return self.env.ref('project.mt_task_new')

    def _creation_message(self):
        self.ensure_one()
        if self.project_id:
            return _('A new task has been created in the "%(project_name)s" project.',
                     project_name=self.project_id.display_name)
        return _('A new task has been created and is not part of any project.')

    def _track_subtype(self, init_values):
        self.ensure_one()
        mail_message_subtype_per_state = {
            '1_done': 'project.mt_task_done',
            '1_canceled': 'project.mt_task_canceled',
            '01_in_progress': 'project.mt_task_in_progress',
            '03_approved': 'project.mt_task_approved',
            '02_changes_requested': 'project.mt_task_changes_requested',
            '04_waiting_normal': 'project.mt_task_waiting',
        }

        if 'stage_id' in init_values:
            return self.env.ref('project.mt_task_stage')
        elif 'state' in init_values and self.state in mail_message_subtype_per_state:
            return self.env.ref(mail_message_subtype_per_state[self.state])
        return super()._track_subtype(init_values)

    def _mail_get_message_subtypes(self):
        res = super()._mail_get_message_subtypes()
        if not self.project_id.rating_active:
            res -= self.env.ref('project.mt_task_rating')
        if len(self) == 1:
            waiting_subtype = self.env.ref('project.mt_task_waiting')
            if ((self.project_id and not self.project_id.allow_task_dependencies)\
                or (not self.project_id and not self.env.user.has_group('project.group_project_task_dependencies')))\
                and waiting_subtype in res:
                res -= waiting_subtype
        return res

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        # Handle project users and managers recipients that can assign
        # tasks and create new one directly from notification emails. Also give
        # access button to portal users and portal customers. If they are notified
        # they should probably have access to the document.
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()

        project_user_group_id = self.env.ref('project.group_project_user').id
        new_group = ('group_project_user', lambda pdata: pdata['type'] == 'user' and project_user_group_id in pdata['groups'], {})
        groups = [new_group] + groups

        if self.project_privacy_visibility == 'portal':
            groups.insert(0, (
                'allowed_portal_users',
                lambda pdata: pdata['type'] == 'portal',
                {
                    'active': True,
                    'has_button_access': True,
                }
            ))
        portal_privacy = self.project_id.privacy_visibility == 'portal'
        for group_name, _group_method, group_data in groups:
            if group_name in ('customer', 'user') or group_name == 'portal_customer' and not portal_privacy:
                group_data['has_button_access'] = False
            elif group_name == 'portal_customer' and portal_privacy:
                group_data['has_button_access'] = True

        return groups

    def _notify_get_reply_to(self, default=None):
        # Override to set alias of tasks to their project if any
        aliases = self.sudo().mapped('project_id')._notify_get_reply_to(default=default)
        res = {task.id: aliases.get(task.project_id.id) for task in self}
        leftover = self.filtered(lambda rec: not rec.project_id)
        if leftover:
            res.update(super(ProjectTask, leftover)._notify_get_reply_to(default=default))
        return res

    def _ensure_personal_stages(self):
        user = self.env.user
        ProjectTaskTypeSudo = self.env['project.task.type'].sudo()
        # In the case no stages have been found, we create the default stages for the user
        if not ProjectTaskTypeSudo.search_count([('user_id', '=', user.id)], limit=1):
            ProjectTaskTypeSudo.with_context(lang=user.lang, default_project_id=False).create(
                self.with_context(lang=user.lang)._get_default_personal_stage_create_vals(user.id)
            )

    def task_email_split(self, msg):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        aliases = self.mapped('project_id.alias_name')
        return [x for x in email_list if x.split('@')[0] not in aliases]

    @api.model
    def message_new(self, msg, custom_values=None):
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(self.env.context or {})
        create_context['default_user_ids'] = False
        create_context['mail_notify_author'] = True  # Allows sending stage updates to the author
        if custom_values is None:
            custom_values = {}
        # Auto create partner if not existant when the task is created from email
        if not msg.get('author_id') and msg.get('email_from'):
            msg['author_id'] = self.env['res.partner'].create({
                'email': msg['email_from'],
                'name': msg['email_from'],
            }).id

        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'allocated_hours': 0.0,
            'partner_id': msg.get('author_id'),
        }
        defaults.update(custom_values)

        task = super(ProjectTask, self.with_context(create_context)).message_new(msg, custom_values=defaults)
        email_list = task.task_email_split(msg)
        partner_ids = [p.id for p in self.env['mail.thread']._mail_find_partner_from_emails(email_list, records=task, force_create=False) if p]
        task.message_subscribe(partner_ids)
        return task

    def message_update(self, msg, update_vals=None):
        email_list = self.task_email_split(msg)
        partner_ids = [p.id for p in self.env['mail.thread']._mail_find_partner_from_emails(email_list, records=self, force_create=False) if p]
        self.message_subscribe(partner_ids)
        return super().message_update(msg, update_vals=update_vals)

    def _message_get_suggested_recipients(self):
        recipients = super()._message_get_suggested_recipients()
        if self.partner_id:
            reason = _('Customer Email') if self.partner_id.email else _('Customer')
            self._message_add_suggested_recipient(recipients, partner=self.partner_id, reason=reason)
        return recipients

    def _notify_by_email_get_headers(self, headers=None):
        headers = super()._notify_by_email_get_headers(headers=headers)
        if self.project_id:
            current_objects = [h for h in headers.get('X-Odoo-Objects', '').split(',') if h]
            current_objects.insert(0, 'project.project-%s, ' % self.project_id.id)
            headers['X-Odoo-Objects'] = ','.join(current_objects)
        if self.tag_ids:
            headers['X-Odoo-Tags'] = ','.join(self.tag_ids.mapped('name'))
        return headers

    def _message_post_after_hook(self, message, msg_vals):
        if message.attachment_ids and not self.displayed_image_id:
            image_attachments = message.attachment_ids.filtered(lambda a: a.mimetype == 'image')
            if image_attachments:
                self.displayed_image_id = image_attachments[0]

        # use the sanitized body of the email from the message thread to populate the task's description
        if (
           not self.description
           and message.subtype_id == self._creation_subtype()
           and self.partner_id == message.author_id
           and msg_vals['message_type'] == 'email'
        ):
            self.description = message.body
        return super()._message_post_after_hook(message, msg_vals)

    def _get_projects_to_make_billable_domain(self, additional_domain=None):
        return expression.AND([
            [('partner_id', '!=', False)],
            additional_domain or [],
        ])

    def _get_all_subtasks(self):
        return self.browse(set.union(set(), *self._get_subtask_ids_per_task_id().values()))

    def _get_subtask_ids_per_task_id(self):
        if not self:
            return {}

        res = dict.fromkeys(self._ids, [])
        if all(self._ids):
            self.env.cr.execute(
                """
         WITH RECURSIVE task_tree
                     AS (
                     SELECT id, id as supertask_id
                       FROM project_task
                      WHERE id IN %(ancestor_ids)s
                      UNION
                         SELECT t.id, tree.supertask_id
                           FROM project_task t
                           JOIN task_tree tree
                             ON tree.id = t.parent_id
                            AND t.active in (TRUE, %(active)s)
                          WHERE t.parent_id IS NOT NULL
               ) SELECT supertask_id, ARRAY_AGG(id)
                   FROM task_tree
                  WHERE id != supertask_id
               GROUP BY supertask_id
                """,
                {
                    "ancestor_ids": tuple(self.ids),
                    "active": self._context.get('active_test', True),
                }
            )
            res.update(dict(self.env.cr.fetchall()))
        else:
            res.update({
                task.id: task._get_subtasks_recursively().ids
                for task in self
            })
        return res

    def _get_subtasks_recursively(self):
        children = self.child_ids
        if not children:
            return self.env['project.task']
        return children + children._get_subtasks_recursively()

    def action_open_parent_task(self):
        return {
            'name': _('Parent Task'),
            'view_mode': 'form',
            'res_model': 'project.task',
            'res_id': self.parent_id.id,
            'type': 'ir.actions.act_window',
            'context': self._context
        }

    def action_project_sharing_view_parent_task(self):
        if self.parent_id.project_id != self.project_id and self.env.user._is_portal():
            project = self.parent_id.project_id._filtered_access('read')
            if project:
                url = f"/my/projects/{self.parent_id.project_id.id}/task/{self.parent_id.id}"
                if project._check_project_sharing_access():
                    url = f"/my/projects/{self.parent_id.project_id.id}?task_id={self.parent_id.id}"
                return {
                    "name": "Portal Parent Task",
                    "type": "ir.actions.act_url",
                    "url": url,
                }
            elif self.display_parent_task_button:
                return self.parent_id.get_portal_url()
            # The portal user has no access to the parent task, so normally the button should be invisible.
            return {}
        action = self.with_context({
            'search_view_ref': 'project.project_sharing_project_task_view_search',
        }).action_open_parent_task()
        action['views'] = [(self.env.ref('project.project_sharing_project_task_view_form').id, 'form')]
        action['search_view_id'] = self.env.ref("project.project_sharing_project_task_view_search").id
        return action

    # ------------
    # Actions
    # ------------

    def action_open_task(self):
        return {
            'view_mode': 'form',
            'res_model': 'project.task',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'context': self._context
        }

    def action_project_sharing_open_task(self):
        action = self.action_open_task()
        action['views'] = [[self.env.ref('project.project_sharing_project_task_view_form').id, 'form']]
        return action

    def action_project_sharing_open_subtasks(self):
        self.ensure_one()
        subtasks = self.env['project.task'].search([('id', 'child_of', self.id), ('id', '!=', self.id)])
        if subtasks.project_id == self.project_id:
            action = self.env['ir.actions.act_window']._for_xml_id('project.project_sharing_project_task_action_sub_task')
            if len(subtasks) == 1:
                action['view_mode'] = 'form'
                action['views'] = [(view_id, view_type) for view_id, view_type in action['views'] if view_type == 'form']
                action['res_id'] = subtasks.id
            return action
        return {
            'name': 'Portal Sub-tasks',
            'type': 'ir.actions.act_url',
            'url': f'/my/projects/{self.project_id.id}/task/{self.id}/subtasks' if len(subtasks) > 1 else subtasks.get_portal_url(query_string='project_sharing=1'),
        }

    def action_project_sharing_open_blocking(self):
        self.ensure_one()
        blockings = self.dependent_ids
        action = self.env['ir.actions.act_window']._for_xml_id('project.project_sharing_project_task_action_blocking_tasks')
        if len(blockings) == 1:
            action['view_mode'] = 'form'
            action['views'] = [(view_id, view_type) for view_id, view_type in action['views'] if view_type == 'form']
            action['res_id'] = blockings.id
        return action

    def action_dependent_tasks(self):
        self.ensure_one()
        return {
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'context': {**self._context, 'default_depend_on_ids': [Command.link(self.id)], 'show_project_update': False, 'search_default_open_tasks': True},
            'domain': [('depend_on_ids', '=', self.id)],
            'name': _('Dependent Tasks'),
            'view_mode': 'list,form,kanban,calendar,pivot,graph,activity',
        }

    def action_recurring_tasks(self):
        return {
            'name': _('Tasks in Recurrence'),
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'list,form,kanban,calendar,pivot,graph,activity',
            'context': {'create': False},
            'domain': [('recurrence_id', 'in', self.recurrence_id.ids)],
        }

    def action_project_sharing_recurring_tasks(self):
        self.ensure_one()
        recurrent_tasks = self.env['project.task'].search([('recurrence_id', 'in', self.recurrence_id.ids)])
        # If all the recurrent tasks are in the same project, open the list view in sharing mode.
        if recurrent_tasks.project_id == self.project_id:
            action = self.env['ir.actions.act_window']._for_xml_id('project.project_sharing_project_task_recurring_tasks_action')
            action.update({
                'context': {'default_project_id': self.project_id.id},
                'domain': [
                    ('project_id', '=', self.project_id.id),
                    ('recurrence_id', 'in', self.recurrence_id.ids)
                ]
            })
            return action
        # If at least one recurrent task belong to another project, open the portal page
        return {
            'name': 'Portal Recurrent Tasks',
            'type': 'ir.actions.act_url',
            'url':  f'/my/projects/{self.project_id.id}/task/{self.id}/recurrent_tasks',
        }

    def action_open_ratings(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('project.rating_rating_action_task')
        if self.rating_count == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.rating_ids[0].id
            action['views'] = [[self.env.ref('project.rating_rating_view_form_project').id, 'form']]
            return action
        else:
            return action

    def action_unlink_recurrence(self):
        self.recurrence_id.task_ids.recurring_task = False
        self.recurrence_id.unlink()

    def action_convert_to_subtask(self):
        self.ensure_one()
        if self.project_id:
            return {
                'name': _('Convert to Task/Sub-Task'),
                'type': 'ir.actions.act_window',
                'res_model': 'project.task',
                'res_id': self.id,
                'views': [(self.env.ref('project.project_task_convert_to_subtask_view_form', False).id, 'form')],
                'target': 'new',
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'danger',
                'message': _('Private tasks cannot be converted into sub-tasks. Please set a project on the task to gain access to this feature.'),
            }
        }

    def action_archive(self):
        child_tasks = self.child_ids.filtered(lambda child_task: not child_task.display_in_project)
        if child_tasks:
            child_tasks.action_archive()
        self.filtered(lambda t: not t.display_in_project and t.parent_id).display_in_project = True
        return super().action_archive()

    # ---------------------------------------------------
    # Rating business
    # ---------------------------------------------------

    def _send_task_rating_mail(self, force_send=False):
        for task in self:
            rating_template = task.stage_id.rating_template_id
            partner = task.partner_id
            if rating_template and partner and partner != self.env.user.partner_id:
                task.rating_send_request(rating_template, lang=task.partner_id.lang, force_send=force_send)

    def _rating_get_partner(self):
        res = super()._rating_get_partner()
        if not res and self.project_id.partner_id:
            return self.project_id.partner_id
        return res

    def rating_apply(self, rate, token=None, rating=None, feedback=None,
                     subtype_xmlid=None, notify_delay_send=False):
        rating = super().rating_apply(
            rate, token=token, rating=rating, feedback=feedback,
            subtype_xmlid=subtype_xmlid, notify_delay_send=notify_delay_send)
        if self.stage_id and self.stage_id.auto_validation_state:
            state = '03_approved' if rating.rating >= rating_data.RATING_LIMIT_SATISFIED else '02_changes_requested'
            self.write({'state': state})
        return rating

    def _rating_apply_get_default_subtype_id(self):
        return self.env['ir.model.data']._xmlid_to_res_id("project.mt_task_rating")

    def _rating_get_parent_field_name(self):
        return 'project_id'

    def _rating_get_operator(self):
        """ Overwrite since we have user_ids and not user_id """
        tasks_with_one_user = self.filtered(lambda task: len(task.user_ids) == 1 and task.user_ids.partner_id)
        return tasks_with_one_user.user_ids.partner_id or self.env['res.partner']

    # ---------------------------------------------------
    # Privacy
    # ---------------------------------------------------
    def _unsubscribe_portal_users(self):
        self.message_unsubscribe(partner_ids=self.message_partner_ids.filtered('user_ids.share').ids)

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        calendar = self.env.company.resource_calendar_id
        return calendar._get_unusual_days(
            datetime.combine(fields.Date.from_string(date_from), time.min).replace(tzinfo=UTC),
            datetime.combine(fields.Date.from_string(date_to), time.max).replace(tzinfo=UTC)
        )

    def action_redirect_to_project_task_form(self):
        menu_id = self.env.ref('project.menu_project_management_all_tasks').id
        return {
            'type': 'ir.actions.act_url',
            'url': f"/odoo/1/action-project.act_project_project_2_project_task_all/{self.id}?menu_id={menu_id}",
            'target': 'new',
        }

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # A read_group can not be performed if records are grouped by personal_stage_type_id as it is a computed field.
        # personal_stage_type_ids behaves like a M2O from the point of view of the user, we therefore use this field instead.
        if 'personal_stage_type_id' in groupby and (not lazy or groupby[0] == 'personal_stage_type_id'):
            groupby = ["personal_stage_type_ids" if field == "personal_stage_type_id" else field for field in groupby] # limitation: problem when both personal_stage_type_id and personal_stage_type_ids appear in read_group, but this has no functional utility
            result = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
            for group in result:
                group['personal_stage_type_id'] = group.pop('personal_stage_type_ids', False)
                group['personal_stage_type_id_count'] = group.pop('personal_stage_type_ids_count', 0)
            return result
        return super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)

    # ---------------------------------------------------
    # Project Sharing
    # ---------------------------------------------------

    def project_sharing_toggle_is_follower(self):
        self.ensure_one()
        self.check_access('write')
        is_follower = self.message_is_follower
        if is_follower:
            self.sudo().message_unsubscribe(self.env.user.partner_id.ids)
        else:
            self.sudo().message_subscribe(self.env.user.partner_id.ids)
        return not is_follower

    @api.depends('subtask_count', 'closed_subtask_count')
    def _compute_subtask_completion_percentage(self):
        for task in self:
            task.subtask_completion_percentage = task.subtask_count and task.closed_subtask_count / task.subtask_count

    @api.model
    def _get_allowed_access_params(self):
        return super()._get_allowed_access_params() | {'project_sharing_id'}

    @api.model
    def _get_thread_with_access(self, thread_id, project_sharing_id=None, token=None, **kwargs):
        if project_sharing_id:
            if token := ProjectSharingChatter._check_project_access_and_get_token(
                self, project_sharing_id, self._name, thread_id, token
            ):
                token = token
        return super()._get_thread_with_access(thread_id, project_sharing_id=project_sharing_id, token=token, **kwargs)

    def get_mention_suggestions(self, search, limit=8):
        """Return the 'limit'-first followers of the given task or followers of its project matching
        a 'search' string as a list of partner data (returned by `_to_store()`).
        See similar method for all partners `get_mention_suggestions()`.
        """
        self.ensure_one()
        project = self.project_id
        if not (
            project
            and project._check_project_sharing_access()
            and project._get_thread_with_access(project.id)
        ):
            return {}
        # sudo: mail.followers - reading message_follower_ids on accessible task/project is allowed
        followers = project.sudo().message_follower_ids | self.sudo().message_follower_ids
        domain = expression.AND([
            self.env["res.partner"]._get_mention_suggestions_domain(search),
            [("id", "in", followers.partner_id.ids)],
        ])
        partners = self.env["res.partner"].sudo()._search_mention_suggestions(domain, limit)
        return Store(partners).get_result()
