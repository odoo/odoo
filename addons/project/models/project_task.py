# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .project_task_template import CLOSED_STATES

from pytz import UTC
from collections import defaultdict
from datetime import timedelta, datetime, time

from odoo import api, fields, models, tools, _
from odoo.fields import Command, Date, Domain
from odoo.addons.rating.models import rating_data
from odoo.exceptions import UserError, ValidationError
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
    'stage_id_color',
    'access_token',
    'access_url',
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
    'color',
    'parent_id',
    'priority',
    'state',
    'is_closed',
}


class ProjectTask(models.Model):
    _name = 'project.task'
    _description = "Task"
    _date_name = "date_assign"
    _inherit = [
        'project.task.template',
        'portal.mixin',
        'mail.thread.cc',
        'mail.activity.mixin',
        'rating.mixin',
        'mail.tracking.duration.mixin',
    ]
    _mail_post_access = 'read'
    _mail_thread_customer = True
    _primary_email = 'email_from'
    _track_duration_field = 'stage_id'

    @api.model
    def _get_default_partner_id(self, project=None, parent=None):
        if parent and parent.partner_id:
            return parent.partner_id.id
        if project and project.partner_id:
            return project.partner_id.id
        return False

    @api.model
    def _default_user_ids(self):
        return self.env.user.ids if any(key in self.env.context for key in ('default_personal_stage_type_ids', 'default_personal_stage_type_id')) else ()

    @api.model
    def _read_group_personal_stage_type_ids(self, stages, domain):
        return stages.search(['|', ('id', 'in', stages.ids), ('user_id', '=', self.env.user.id)])

    name = fields.Char(tracking=True)
    stage_id = fields.Many2one(tracking=True)
    state = fields.Selection(tracking=True, inverse='_inverse_state')
    priority = fields.Selection(tracking=True)
    date_assign = fields.Datetime(string='Assigning Date', copy=False, readonly=True,
        help="Date on which this task was last assigned (or unassigned). Based on this, you can get statistics on the time it usually takes to assign tasks.")
    date_deadline = fields.Datetime(tracking=True, copy=False)
    project_id = fields.Many2one('project.project', required=False, falsy_value_label=_lt("🔒 Private"))
    allocated_hours = fields.Float(tracking=True)
    user_ids = fields.Many2many('res.users', relation='project_task_user_rel', column1='task_id', column2='user_id', string='Assignees', context={'active_test': False}, tracking=True, default=_default_user_ids, domain="[('share', '=', False), ('active', '=', True)]", falsy_value_label=_lt("👤 Unassigned"))
    # User names displayed in project sharing views
    portal_user_names = fields.Char(compute='_compute_portal_user_names', compute_sudo=True, search='_search_portal_user_names', export_string_translation=False)
    # Second Many2many containing the actual personal stage for the current user
    # See project_task_stage_personal.py for the model defininition
    personal_stage_type_ids = fields.Many2many('project.task.type', 'project_task_user_rel', column1='task_id', column2='stage_id',
        ondelete='restrict', group_expand='_read_group_personal_stage_type_ids', copy=False,
        domain="[('user_id', '=', uid)]", string='Personal Stages', export_string_translation=False)
    # Personal Stage computed from the user
    personal_stage_id = fields.Many2one('project.task.stage.personal', string='Personal Stage State', compute_sudo=False,
        compute='_compute_personal_stage_id',
        search='_search_personal_stage_id',
        group_expand='_read_group_personal_stage_type_ids',
        help="The current user's personal stage.")
    personal_stage_type_id = fields.Many2one('project.task.type', string='Personal Stage',
        related='personal_stage_id.stage_id',
        readonly=False, store=False,
        help="The current user's personal task stage.", domain="[('user_id', '=', uid)]",
        group_expand='_read_group_personal_stage_type_ids')
    partner_id = fields.Many2one('res.partner',
        string='Customer', recursive=True, tracking=True, compute='_compute_partner_id', store=True, readonly=False, index='btree_not_null',
        domain="['|', ('company_id', '=?', company_id), ('company_id', '=', False)]", )
    partner_phone = fields.Char(
        compute='_compute_partner_phone', inverse='_inverse_partner_phone',
        string="Contact Number", readonly=False, store=True, copy=False
    )
    # Need this field to check there is no email loops when Odoo reply automatically
    email_from = fields.Char('Email From')
    email_cc = fields.Char(help='Email addresses that were in the CC of the incoming emails from this task and that are not currently linked to an existing customer.')
    rating_active = fields.Boolean(string='Project Rating Status', related="project_id.rating_active")

    parent_id = fields.Many2one('project.task', string='Parent Task', inverse="_inverse_parent_id", index=True, domain="['!', ('id', 'child_of', id)]", tracking=True)
    child_ids = fields.One2many('project.task', 'parent_id', string="Sub-tasks", domain="[('recurring_task', '=', False)]", export_string_translation=False)
    project_privacy_visibility = fields.Selection(related='project_id.privacy_visibility', string="Project Visibility", tracking=False)
    # Computed field about working time elapsed between record creation and assignation/closing.
    working_hours_open = fields.Float(compute='_compute_elapsed', string='Working Hours to Assign', digits=(16, 2), store=True, aggregator="avg")
    working_hours_close = fields.Float(compute='_compute_elapsed', string='Working Hours to Close', digits=(16, 2), store=True, aggregator="avg")
    working_days_open = fields.Float(compute='_compute_elapsed', string='Working Days to Assign', store=True, aggregator="avg")
    working_days_close = fields.Float(compute='_compute_elapsed', string='Working Days to Close', store=True, aggregator="avg")
    # customer portal: include comment and (incoming/outgoing) emails in communication history
    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', 'in', ['email', 'comment', 'email_outgoing', 'auto_comment'])], export_string_translation=False)
    milestone_id = fields.Many2one(tracking=True)
    task_template_id = fields.Many2one(
        comodel_name='project.task.template',
        string='Task Template',
        copy=False,
    )

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
    recurring_count = fields.Integer(string="Tasks in Recurrence", compute='_compute_recurring_count')
    recurrence_id = fields.Many2one('project.task.recurrence', copy=False, index='btree_not_null')
    repeat_interval = fields.Integer(compute='_compute_repeat', compute_sudo=True, readonly=False, default=1)
    repeat_unit = fields.Selection(compute='_compute_repeat', compute_sudo=True, readonly=False)
    repeat_type = fields.Selection(
        selection_add=[('until', 'Until')],
        default="forever", string="Until", compute='_compute_repeat', compute_sudo=True, readonly=False)
    repeat_until = fields.Date(compute='_compute_repeat', compute_sudo=True, readonly=False)

    link_preview_name = fields.Char(compute='_compute_link_preview_name', export_string_translation=False)

    _recurring_task_has_no_parent = models.Constraint(
        'CHECK (NOT (recurring_task IS TRUE AND parent_id IS NOT NULL))',
        'You cannot convert this task into a sub-task because it is recurrent.',
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
    def TASK_PORTAL_READABLE_FIELDS(self):
        return PROJECT_TASK_READABLE_FIELDS

    @property
    def TASK_PORTAL_WRITABLE_FIELDS(self):
        return PROJECT_TASK_WRITABLE_FIELDS

    def _get_rotting_depends_fields(self):
        return super()._get_rotting_depends_fields() + ['is_closed']

    def _get_rotting_domain(self):
        return super()._get_rotting_domain() & Domain('is_closed', '=', False)

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

    @api.model
    def _search_personal_stage_id(self, operator, value):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        field_name = 'display_name' if any(isinstance(v, str) for v in value) or value == '' else 'id'  # noqa: PLC1901
        domain = Domain(field_name, operator, value) & Domain('user_id', '=', self.env.uid)
        personal_stages = self.env['project.task.stage.personal']._search(domain)
        return Domain('id', 'in', personal_stages.subselect('task_id'))

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
            project_followers = self.project_id.sudo().message_follower_ids.filtered(lambda f: f.partner_id.id in partner_ids)
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
        return super()._get_recurrence_fields() + ['repeat_until']

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

    @api.depends('partner_id.phone')
    def _compute_partner_phone(self):
        for task in self:
            task.partner_phone = task.partner_id.phone or False

    def _inverse_partner_phone(self):
        for task in self:
            if task.partner_id:
                task.partner_id.phone = task.partner_phone

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
        if operator != 'ilike' or not isinstance(value, str):
            return NotImplemented

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
        # filter only readable fields
        vals_list = [
            {
                k: v
                for k, v in vals.items()
                if self._has_field_access(self._fields[k], 'read')
            }
            for vals in vals_list
        ]

        for task, vals in zip(self, vals_list):
            if task.recurrence_id and not default.get('recurrence_id'):
                vals['recurrence_id'] = task.recurrence_id.copy().id
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
        log_message = _("Task Created")
        copied_tasks._message_log_batch(bodies={task.id: log_message for task in copied_tasks})

        return copied_tasks

    @api.model
    def get_empty_list_help(self, help_message):
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
        return super().get_empty_list_help(help_message)

    # ------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of fields_get making fields readonly for portal users
        makes the view cache dependent on the fact the user has the group portal or not"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (self.env.user._is_portal(),)

    @api.model
    def default_get(self, fields):
        vals = super().default_get(fields)

        if 'repeat_until' in fields:
            vals['repeat_until'] = Date.today() + timedelta(days=7)

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
            if 'company_id' in fields and 'default_project_id' not in self.env.context:
                vals['company_id'] = project.sudo().company_id.id
        elif 'default_user_ids' not in self.env.context and 'user_ids' in fields:
            user_ids = vals.get('user_ids', [])
            user_ids.append(Command.link(self.env.user.id))
            vals['user_ids'] = user_ids
        return vals

    @api.model
    @tools.ormcache(cache='stable')
    def _portal_accessible_fields(self) -> tuple[frozenset[str], frozenset[str]]:
        """Readable and writable fields by portal users."""
        readable = frozenset(self.TASK_PORTAL_READABLE_FIELDS)
        writeable = frozenset(self.TASK_PORTAL_WRITABLE_FIELDS)
        return readable | writeable, writeable

    def _has_field_access(self, field, operation):
        if not super()._has_field_access(field, operation):
            return False
        if not self.env.su and self.env.user._is_portal():
            # additional checks for portal users
            readable, writeable = self._portal_accessible_fields()
            if operation == 'read':
                return field.name in readable
            if operation == 'write':
                return field.name in writeable
        return True

    def _ensure_fields_write(self, vals, defaults=False):
        if defaults:
            vals = {
                **{key[8:]: value for key, value in self.env.context.items() if key.startswith("default_")},
                **vals
            }

        for fname, value in vals.items():
            field = self._fields.get(fname)
            if field and field.type == 'many2one':
                self.env[field.comodel_name].browse(value).check_access('read')

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
        # Some values are determined by this override and must be written as
        # sudo for portal users, because they do not have access to these
        # fields. Other values must not be written as sudo.
        additional_vals_list = [{} for _ in vals_list]

        new_context = dict(self.env.context)
        default_personal_stage = new_context.pop('default_personal_stage_type_ids', False)
        for vals, additional_vals in zip(vals_list, additional_vals_list):
            if default_personal_stage and 'personal_stage_type_id' not in vals:
                additional_vals['personal_stage_type_id'] = default_personal_stage[0]
        # create the task, write computed inaccessible fields in sudo
        for vals, computed_vals in zip(vals_list, additional_vals_list):
            if self.env.user._is_portal() and not self.env.su:
                self._ensure_fields_write(vals, defaults=True)
            # recurrence
            rec_fields = vals.keys() & self._get_recurrence_fields()
            if rec_fields and vals.get('recurring_task') is True:
                rec_values = {rec_field: vals[rec_field] for rec_field in rec_fields}
                recurrence = self.env['project.task.recurrence'].create(rec_values)
                vals['recurrence_id'] = recurrence.id
            for field_name in list(computed_vals):
                if self._has_field_access(self._fields[field_name], 'write'):
                    vals[field_name] = computed_vals.pop(field_name)
        tasks = super().create(vals_list)
        self._task_message_auto_subscribe_notify({task: task.user_ids - self.env.user for task in tasks})

        tasks._populate_missing_personal_stages()
        current_partner = self.env.user.partner_id

        all_partner_emails = []
        for task in tasks.sudo():
            all_partner_emails += tools.email_normalize_all(task.email_cc)
        partners = self.env['res.partner'].search([('email', 'in', all_partner_emails)])
        partner_per_email = {
            partner.email: partner
            for partner in partners
            if not all(u.share for u in partner.user_ids)
        }
        for task in tasks.sudo():
            if task.project_id.privacy_visibility in ['invited_users', 'portal']:
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
        self.check_access('write')
        partner_ids = []
        if self.env.user._is_portal() and not self.env.su:
            self._ensure_fields_write(vals, defaults=False)

        now = fields.Datetime.now()
        # task_ids_without_user_set = set()
        if 'user_ids' in vals:
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

        # Track user_ids to send assignment notifications
        old_user_ids = {t: t.user_ids for t in self.sudo()}

        if "personal_stage_type_id" in vals and not vals['personal_stage_type_id']:
            del vals['personal_stage_type_id']

        # sends an email to the 'Task Creation' subtype subscribers
        # When project_id is changed
        project_link_per_task_id = {}
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

        if 'user_ids' in vals:
            self._populate_missing_personal_stages()

        # user_ids change: update date_assign
        if 'user_ids' in vals:
            for task in self.sudo():
                if not task.user_ids and task.date_assign:
                    task.date_assign = False
                elif 'date_assign' not in vals and task.id in task_ids_without_user_set:
                    task.date_assign = now

        # rating on stage
        if 'stage_id' in vals and vals.get('stage_id'):
            self.sudo().filtered(lambda x: x.project_id.rating_active and x.project_id.rating_status == 'stage')._send_task_rating_mail(force_send=True)

        if 'state' in vals:
            # specific use case: when the blocked task goes from 'forced' done state to a not closed state, we fix the state back to waiting
            for task in self.sudo():
                if task.allow_task_dependencies:
                    if task.is_blocked_by_dependences() and vals['state'] not in CLOSED_STATES and vals['state'] != '04_waiting_normal':
                        task.state = '04_waiting_normal'
                task.date_last_stage_update = now

        self._task_message_auto_subscribe_notify({task: task.user_ids - old_user_ids[task] - self.env.user for task in self})

        if partner_ids:
            for task in self:
                project_link = project_link_per_task_id.get(task.id)
                if project_link:
                    body = _(
                        'Task Transferred from Project %(source_project)s to %(destination_project)s',
                        source_project=project_link,
                        destination_project=task.project_id._get_html_link(title=task.project_id.display_name),
                    )
                else:
                    body = _('Task Converted from To-Do')
                task.message_notify(
                    body=body,
                    partner_ids=partner_ids,
                    email_layout_xmlid='mail.mail_notification_layout',
                    notify_author_mention=False,
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
            return Domain(new_domain)

        filtered_domain = filter_domain_leaf(domain, lambda field_to_check: field_to_check in [
            field,
            f"{field}.id",
            f"{field}.name",
        ], {
            field: "name",
            f"{field}.id": "id",
            f"{field}.name": "name",
        })
        if filtered_domain.is_true():
            return self.env[comodel]
        filtered_domain = _change_operator(filtered_domain)
        if additional_domain:
            filtered_domain &= Domain(additional_domain)
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

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False,
                                                   force_record_name=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals=msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang,
            force_record_name=force_record_name,
        )
        project_name = self.project_id.sudo().name
        stage_name = self.stage_id.name
        subtitles = ""
        if project_name and stage_name:
            subtitles = _('Project: %(project_name)s, Stage: %(stage_name)s', project_name=project_name, stage_name=stage_name)
        elif project_name:
            subtitles = _('Project: %(project_name)s', project_name=project_name)
        elif stage_name:
            subtitles = _('Stage: %(stage_name)s', stage_name=stage_name)
        if subtitles:
            render_context['subtitles'].append(subtitles)
        return render_context

    def _send_email_notify_to_cc(self, partners_to_notify):
        # TDE TODO: this should be removed with email-like recipients management
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

        if self.project_privacy_visibility in ['invited_users', 'portal']:
            groups.insert(0, (
                'allowed_portal_users',
                lambda pdata: pdata['type'] in ['invited_users', 'portal'],
                {
                    'active': True,
                    'has_button_access': True,
                }
            ))
        portal_privacy = self.project_id.privacy_visibility in ['invited_users', 'portal']
        for group_name, _group_method, group_data in groups:
            if group_name in ('customer', 'user') or group_name == 'portal_customer' and not portal_privacy:
                group_data['has_button_access'] = False
            elif group_name == 'portal_customer' and portal_privacy:
                group_data['has_button_access'] = True

        return groups

    def _notify_get_reply_to(self, default=None, author_id=False):
        # Override to set alias of tasks to their project if any
        aliases = self.sudo().mapped('project_id')._notify_get_reply_to(default=default, author_id=author_id)
        res = {task.id: aliases.get(task.project_id.id) for task in self}
        leftover = self.filtered(lambda rec: not rec.project_id)
        if leftover:
            res.update(super(ProjectTask, leftover)._notify_get_reply_to(default=default, author_id=author_id))
        return res

    def _find_internal_users_from_address_mail(self, emails, project_id=False):
        sanitized_email_dict = self._mail_cc_sanitized_raw_dict(emails)
        matched_partners = self.env['res.partner']._find_or_create_from_emails(
            sanitized_email_dict.keys(),
            no_create=True
        )
        partners = self.env['res.partner'].concat(*matched_partners)
        unresolved_emails = set(sanitized_email_dict) - set(partners.mapped("email"))
        unmatched_partner_emails = [sanitized_email_dict.get(email) for email in unresolved_emails]
        if project_id:
            project = self.env["project.project"].browse(project_id)
            project_alias_address = project.alias_name + "@" + project.alias_domain_id.name
            # Removing project alias from unmatched_partner_emails as this will be added to cc_mail address and when
            # a mail is sent unnecessary partner is created in the name of project_alias
            unmatched_partner_emails.remove(project_alias_address)

        users = partners.user_ids
        internal_user_ids = users.filtered(lambda u: not u.share).ids

        partner_emails_without_internal_users = (partners - users.partner_id).mapped("email_formatted")

        return internal_user_ids, partner_emails_without_internal_users, unmatched_partner_emails

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(self.env.context or {})
        create_context['default_user_ids'] = False
        if custom_values is None:
            custom_values = {}
        # Auto create partner if not existent when the task is created from email
        if not msg_dict.get('author_id') and msg_dict.get('email_from'):
            author = self.env['mail.thread']._partner_find_from_emails_single([msg_dict['email_from']], no_create=False)
            msg_dict['author_id'] = author.id

        defaults = {
            'name': msg_dict.get('subject') or _("No Subject"),
            'allocated_hours': 0.0,
            'partner_id': msg_dict.get('author_id'),
            'email_cc': ", ".join(self._mail_cc_sanitized_raw_dict(msg_dict.get('cc')).values()) if custom_values.get('project_id') else ""

        }
        defaults.update(custom_values)

        # users having email address matched from emails recepients are filtered out and added as assignees to the task
        if msg_dict.get('to'):
            internal_users, partner_emails_without_users, unmatched_partner_emails = self._find_internal_users_from_address_mail(msg_dict.get('to'), defaults.get('project_id'))
            # set only internal users as assignees
            defaults['user_ids'] = defaults.get('user_ids', []) + internal_users
            if custom_values.get("project_id") and (partner_emails_without_users or unmatched_partner_emails):
                defaults["email_cc"] = defaults.get("email_cc", "") + ", " + ", ".join(partner_emails_without_users + unmatched_partner_emails)
        task = super(ProjectTask, self.with_context(create_context)).message_new(msg_dict, custom_values=defaults)
        partners = task._partner_find_from_emails_single(tools.email_split((msg_dict.get('to') or '') + ',' + (msg_dict.get('cc') or '')), no_create=True)
        if task.project_id:
            task.message_subscribe(partners.ids)
        return task

    def message_update(self, msg_dict, update_vals=None):
        for task in self:
            partners = task._partner_find_from_emails_single(tools.email_split((msg_dict.get('to') or '') + ',' + (msg_dict.get('cc') or '')), no_create=True)
            task.message_subscribe(partners.ids)
        return super().message_update(msg_dict, update_vals=update_vals)

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
        return Domain('partner_id', '!=', False) & Domain(additional_domain or Domain.TRUE)

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
            'context': self.env.context
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
            'context': {**self.env.context, 'default_depend_on_ids': [Command.link(self.id)], 'show_project_update': False, 'search_default_open_tasks': True},
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

    def _project_task_template_vals(self):
        defaults = {}
        if self.recurring_task:
            defaults = {
                'repeat_interval': self.repeat_interval,
                'repeat_unit': self.repeat_unit,
                'repeat_type': self.repeat_type,
                'repeat_until': self.repeat_until,
            }
        template_fields = self.env['project.task.template']._fields
        generated_task = self.with_context(copy_project=True).copy_data(defaults)[0]

        def filter_vals(vals):
            """Recursively filter values by template_fields, including nested child_ids."""
            filtered = {}
            for f_name, value in vals.items():
                if f_name in template_fields:
                    if f_name == "child_ids" and value:
                        filtered_children = []
                        for command, _, child_vals in value:
                            filtered_children.append((command, 0, filter_vals(child_vals)))
                        filtered[f_name] = filtered_children
                    else:
                        filtered[f_name] = value
            return filtered
        return filter_vals(generated_task)

    def action_generate_task_template(self):
        self.ensure_one()
        task_template_vals = self._project_task_template_vals()
        task_template = self.env['project.task.template'].create(task_template_vals)
        self.task_template_id = task_template.id
        return {
            'type': 'ir.actions.client',
            'tag': 'project_show_template_notification',
            'params': {
                'res_model': 'project.task.template',
                'res_id': self.task_template_id.id,
                'undo_method': "unlink",
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'soft_reload',
                },
            },
        }

    def plan_task_in_calendar(self, vals):
        self.ensure_one()
        return self.write(vals)

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
            'url': f"/odoo/{self.project_id.id}/action-project.act_project_project_2_project_task_all/{self.id}?menu_id={menu_id}",
            'target': 'new',
        }

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None) -> list[tuple]:
        # A _read_group cannot be performed if records are grouped by personal_stage_type_id
        # as it is a computed field. personal_stage_type_ids behaves like a M2O from the point
        # of view of the user, we therefore use this field instead.
        if 'personal_stage_type_id' in groupby:
            # limitation: problem when both personal_stage_type_id and personal_stage_type_ids
            # appear in read_group, but this has no functional utility
            groupby = ['personal_stage_type_ids' if fname == 'personal_stage_type_id' else fname for fname in groupby]
            if order:
                order = order.replace('personal_stage_type_id', 'personal_stage_type_ids')
        return super()._read_group(domain, groupby, aggregates, having, offset, limit, order)

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

    @api.model
    def _get_allowed_access_params(self):
        return super()._get_allowed_access_params() | {'project_sharing_id'}

    @api.model
    def _get_thread_with_access(self, thread_id, *, project_sharing_id=None, token=None, **kwargs):
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
        domain = (
            Domain(self.env["res.partner"]._get_mention_suggestions_domain(search))
            & Domain("id", "in", followers.partner_id.ids)
        )
        partners = self.env["res.partner"].sudo()._search_mention_suggestions(domain, limit)
        return (
            Store()
            .add(partners, ["email", "im_status", "name", *partners._get_store_mention_fields()])
            .get_result()
        )

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Tasks'),
            'template': '/project/static/xls/tasks_import_template.xlsx',
        }]
