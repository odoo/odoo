import re
from collections import defaultdict

from odoo import api, fields, models, SUPERUSER_ID
from odoo.fields import Command, Domain
from odoo.addons.web_editor.tools import handle_history_divergence
from odoo.exceptions import UserError, ValidationError
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)

CLOSED_STATES = {
    '1_done': 'Done',
    '1_canceled': 'Cancelled',
}


class ProjectTaskTemplate(models.Model):
    _name = "project.task.template"
    _description = "Task Template"
    _inherit = 'html.field.history.mixin'
    _systray_view = 'list'
    _order = "priority desc, sequence, date_deadline asc, id desc"

    def _get_versioned_fields(self):
        return [ProjectTaskTemplate.description.name]

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        return self.stage_find(project_id, order="fold, sequence, id")

    @api.model
    def _default_user_ids(self):
        return self.env.user.ids if any(key in self.env.context for key in ('default_personal_stage_type_ids', 'default_personal_stage_type_id')) else ()

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        search_domain = [('id', 'in', stages.ids)]
        if 'default_project_id' in self.env.context and not self.env.context.get('subtask_action') and 'project_kanban' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain

        stage_ids = stages._search(search_domain, order=stages._order)
        return stages.browse(stage_ids)

    @api.model
    def _default_company_id(self):
        if self.env.context.get('default_project_id'):
            return self.env['project.project'].browse(self.env.context['default_project_id']).company_id
        return False

    active = fields.Boolean(default=True, export_string_translation=False)
    name = fields.Char(string='Title', required=True, index='trigram')
    description = fields.Html(string='Description', sanitize_attributes=False)
    priority = fields.Selection([
        ('0', 'Low priority'),
        ('1', 'Medium priority'),
        ('2', 'High priority'),
        ('3', 'Urgent'),
    ], default='0', index=True, string="Priority")
    sequence = fields.Integer(string='Sequence', default=10, export_string_translation=False)
    stage_id = fields.Many2one('project.task.type', string='Stage', compute='_compute_stage_id',
        store=True, readonly=False, index=True,
        default=_get_default_stage_id, group_expand='_read_group_stage_ids',
        domain="[('project_ids', '=', project_id)]")
    stage_id_color = fields.Integer(string='Stage Color', related="stage_id.color", export_string_translation=False)
    tag_ids = fields.Many2many('project.tags', string='Tags')

    state = fields.Selection([
        ('01_in_progress', 'In Progress'),
        ('02_changes_requested', 'Changes Requested'),
        ('03_approved', 'Approved'),
        *CLOSED_STATES.items(),
        ('04_waiting_normal', 'Waiting'),
    ], string='State', copy=False, default='01_in_progress', required=True, compute='_compute_state', readonly=False, store=True, index=True, recursive=True)
    is_closed = fields.Boolean("Closed state", compute='_compute_is_closed', search='_search_is_closed')

    create_date = fields.Datetime("Created On", readonly=True, index=True)
    write_date = fields.Datetime("Last Updated On", readonly=True)
    date_end = fields.Datetime(string='Ending Date', index=True)
    date_deadline = fields.Datetime(string='Deadline', index=True)

    date_last_stage_update = fields.Datetime(string='Last Stage Update',
        index=True,
        copy=False,
        readonly=True,
        help="Date on which the state of your task has last been modified.\n"
            "Based on this information you can identify tasks that are stalling and get statistics on the time it usually takes to move tasks from one stage/state to another.")

    project_id = fields.Many2one('project.project', string='Project', domain="['|', ('company_id', '=', False), ('company_id', '=?',  company_id)]",
                                 compute="_compute_project_id", store=True, precompute=True, recursive=True, readonly=False, index=True, change_default=True, required=True)
    has_project_template = fields.Boolean(related='project_id.is_template', string="Has Project Template", export_string_translation=False)
    display_in_project = fields.Boolean(compute='_compute_display_in_project', store=True, export_string_translation=False)
    task_properties = fields.Properties('Properties', definition='project_id.task_properties_definition', copy=True)
    allocated_hours = fields.Float("Allocated Time")
    subtask_allocated_hours = fields.Float("Sub-tasks Allocated Time", compute='_compute_subtask_allocated_hours', export_string_translation=False,
        help="Sum of the hours allocated for all the sub-tasks (and their own sub-tasks) linked to this task. Usually less than or equal to the allocated hours of this task.")
    role_ids = fields.Many2many(
        'project.role',
        string='Project Roles',
        help="When you create a project from a template, you can choose which employee takes each role. These employees will be added to the tasks, along with anyone already assigned.",
    )
    # Tracking of this field is done in the write function
    user_ids = fields.Many2many('res.users', string='Assignees', context={'active_test': False}, default=_default_user_ids, domain="[('share', '=', False), ('active', '=', True)]", falsy_value_label=_lt("👤 Unassigned"))
    company_id = fields.Many2one('res.company', string='Company', compute='_compute_company_id', store=True, readonly=False, recursive=True, copy=True, default=_default_company_id)
    color = fields.Integer(string='Color Index', export_string_translation=False)
    attachment_ids = fields.One2many(
        'ir.attachment',
        compute='_compute_attachment_ids',
        string="Attachments",
        export_string_translation=False,
        help="Attachments that don't come from a message",
    )
    # In the domain of displayed_image_id, we couln't use attachment_ids because a one2many is represented as a list of commands so we used res_model & res_id
    displayed_image_id = fields.Many2one('ir.attachment', domain="[('res_model', '=', 'project.task.template'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]", string='Cover Image')

    parent_id = fields.Many2one('project.task.template', string='Parent Task', inverse="_inverse_parent_id", index=True, domain="['!', ('id', 'child_of', id)]", copy=False)
    child_ids = fields.One2many('project.task.template', 'parent_id', string="Sub-tasks", domain="[('recurring_task', '=', False)]", export_string_translation=False)
    subtask_count = fields.Integer("Sub-task Count", compute='_compute_subtask_count', export_string_translation=False)
    closed_subtask_count = fields.Integer("Closed Sub-tasks Count", compute='_compute_subtask_count', export_string_translation=False)
    subtask_completion_percentage = fields.Float(compute="_compute_subtask_completion_percentage", export_string_translation=False)
    allow_milestones = fields.Boolean(related='project_id.allow_milestones', export_string_translation=False)
    milestone_id = fields.Many2one(
        'project.milestone',
        'Milestone',
        domain="[('project_id', '=', project_id)]",
        compute='_compute_milestone_id',
        readonly=False,
        store=True,
        index='btree_not_null',
        help="Deliver your services automatically when a milestone is reached by linking it to a sales order item.",
    )
    has_late_and_unreached_milestone = fields.Boolean(
        compute='_compute_has_late_and_unreached_milestone',
        search='_search_has_late_and_unreached_milestone',
        export_string_translation=False,
    )
    # Task Template Dependencies fields
    allow_task_dependencies = fields.Boolean(related='project_id.allow_task_dependencies', export_string_translation=False)
    # Tracking of this field is done in the write function
    depend_on_ids = fields.Many2many('project.task')

    # recurrence fields
    recurring_task = fields.Boolean(string="Recurrent")
    repeat_interval = fields.Integer(string='Repeat Every', default=0)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week')
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
    ], default="forever", string="Until", readonly=True)

    # Quick creation shortcuts
    display_name = fields.Char(
        inverse='_inverse_display_name',
        help="""Use these keywords in the title to set new tasks:\n
            #tags Set tags on the task
            @user Assign the task to a user
            ! Set the task a high priority
            !! Set the task a high priority
            !!! Set the task a urgent priority\n
            Make sure to use the right format and order e.g. Improve the configuration screen #feature #v16 @Mitchell !""",
    )

    @api.depends('parent_id.project_id')
    def _compute_project_id(self):
        self.env.remove_to_compute(self._fields['display_in_project'], self)
        for task_template in self:
            if not task_template.display_in_project and task_template.parent_id and task_template.parent_id.project_id != task_template.project_id:
                task_template.project_id = task_template.parent_id.project_id

    @api.depends('project_id', 'parent_id')
    def _compute_display_in_project(self):
        for task_template in self:
            task_template.display_in_project = not task_template.project_id or (
                not task_template.parent_id or task_template.project_id != task_template.parent_id.project_id
            )

    def _inverse_parent_id(self):
        for task_template in self.sudo():
            if not task_template.parent_id:
                task_template.display_in_project = True
            elif task_template.display_in_project and task_template.project_id == task_template.parent_id.sudo().project_id:
                task_template.display_in_project = False

    @api.depends('stage_id', 'depend_on_ids.state')
    def _compute_state(self):
        for task_template in self:
            dependent_open_tasks = []
            if task_template.allow_task_dependencies:
                dependent_open_tasks = [dependent_task for dependent_task in task_template.depend_on_ids if dependent_task.state not in CLOSED_STATES]
            # if one of the blocking task is in a blocking state
            if dependent_open_tasks:
                # here we check that the blocked task is not already in a closed state (if the task is already done we don't put it in waiting state)
                if task_template.state not in CLOSED_STATES:
                    task_template.state = '04_waiting_normal'
            # if the task as no blocking dependencies and is in waiting_normal, the task goes back to in progress
            elif task_template.state not in CLOSED_STATES:
                task_template.state = '01_in_progress'

    @api.depends('state')
    def _compute_is_closed(self):
        for task_template in self:
            task_template.is_closed = task_template.state in CLOSED_STATES

    def _search_is_closed(self, operator, value):
        if operator == 'in':
            searched_states = list(CLOSED_STATES.keys())
        elif operator == 'not in':
            searched_states = self.OPEN_STATES
        else:
            return NotImplemented
        return [('state', 'in', searched_states)]

    @property
    def OPEN_STATES(self):
        """ Return a list of the technical names complementing the CLOSED_STATES, a.k.a the open states """
        return list(set(self._fields['state'].get_values(self.env)) - set(CLOSED_STATES))

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.state != '04_waiting_normal':
            self.state = '01_in_progress'

    @api.model
    def _get_recurrence_fields(self):
        return [
            'repeat_interval',
            'repeat_unit',
            'repeat_type',
        ]

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(self.env._('Error! You cannot create a recursive hierarchy of tasks.'))

    def _get_attachments_search_domain(self):
        self.ensure_one()
        return [('res_id', '=', self.id), ('res_model', '=', self._name)]

    def _compute_attachment_ids(self):
        for task_template in self:
            attachment_ids = self.env['ir.attachment'].search(task_template._get_attachments_search_domain()).ids
            message_attachment_ids = task_template.mapped('message_ids.attachment_ids').ids  # from mail_thread
            task_template.attachment_ids = [(6, 0, list(set(attachment_ids) - set(message_attachment_ids)))]

    @api.depends('child_ids.allocated_hours')
    def _compute_subtask_allocated_hours(self):
        for task_template in self:
            task_template.subtask_allocated_hours = sum(task_template.child_ids.mapped('allocated_hours'))

    @api.depends('child_ids')
    def _compute_subtask_count(self):
        if not any(self._ids):
            for task_template in self:
                task_template.subtask_count, task_template.closed_subtask_count = len(task_template.child_ids), len(task_template.child_ids.filtered(lambda r: r.state in CLOSED_STATES))
            return
        total_and_closed_subtask_count_per_parent_id = {
            parent.id: (count, sum(s in CLOSED_STATES for s in states))
            for parent, states, count in self._read_group(
                [('parent_id', 'in', self.ids)],
                ['parent_id'],
                ['state:array_agg', '__count'],
            )
        }
        for task_template in self:
            task_template.subtask_count, task_template.closed_subtask_count = total_and_closed_subtask_count_per_parent_id.get(task_template.id, (0, 0))

    @api.onchange('company_id')
    def _onchange_task_company(self):
        if self.project_id.company_id and self.project_id.company_id != self.company_id:
            self.project_id = False

    @api.depends('project_id.company_id', 'parent_id.company_id')
    def _compute_company_id(self):
        for task_template in self:
            if not task_template.parent_id and not task_template.project_id:
                continue
            task_template.company_id = task_template.project_id.company_id or task_template.parent_id.company_id

    @api.depends('project_id')
    def _compute_stage_id(self):
        for task_template in self:
            project = task_template.project_id or task_template.parent_id.project_id
            if project:
                if project not in task_template.stage_id.project_ids:
                    task_template.stage_id = task_template.stage_find(project.id, [('fold', '=', False)])
            else:
                task_template.stage_id = False

    def _get_group_pattern(self):
        return {
            'tags_and_users': r'\s([#@]%s[^\s]+)',
            'priority': r'(?:^|\s)(!{1,3})(?=\s|$)',
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
            domain = Domain.OR(Domain('name', '=ilike', tag) for tag in tags)
            existing_tags = self.env['project.tags'].search(domain)
            existing_tags_names = {tag.name.lower() for tag in existing_tags}
            new_tags_names = {tag for tag in tags if tag.lower() not in existing_tags_names}
            self.tag_ids = [Command.set(existing_tags.ids)] + [Command.create({'name': name}) for name in new_tags_names]
        pattern = tags_and_users_group % ('(?!%s)' % ('|').join(users_to_keep) if users_to_keep else '')
        self.display_name, _ = re.subn(pattern, '', self.display_name)

    def _extract_priority(self):
        priority_group = self._get_group_pattern()['priority']
        match = re.search(priority_group, self.display_name)
        if match:
            self.priority = str(min(len(match.group(1)), 3))
            self.display_name, _dummy = re.subn(priority_group, '', self.display_name)

    def _get_groups(self):
        return [
            lambda task: task._extract_tags_and_users(),
            lambda task: task._extract_priority(),
        ]

    def _inverse_display_name(self):
        for task_template in self:
            pattern = re.compile(r'^%s.+?%s$' % (
                ('').join(task_template._get_cannot_start_with_patterns()),
                ('').join(task_template._get_groups_patterns()))
            )
            match = pattern.match(task_template.display_name)
            if match:
                for group, extract_data in enumerate(task_template._get_groups(), start=1):
                    if match.group(group):
                        extract_data(task_template)
                task_template.name = task_template.display_name.strip()

    def copy_data(self, default=None):
        default = dict(default or {})
        if not self.env.context.get('is_copy_depend_task'):
            default.update({
                'depend_on_ids': False,
            })
        vals_list = super().copy_data(default=default)
        # filter only readable fields
        vals_list = [
            {
                k: v
                for k, v in vals.items()
                if k in self._fields and self._has_field_access(self._fields[k], 'read')
            }
            for vals in vals_list
        ]

        active_users = self.env['res.users']
        has_default_users = 'user_ids' in default
        if not has_default_users:
            active_users = self.user_ids.filtered('active')
        milestone_mapping = self.env.context.get('milestone_mapping', {})
        for task, vals in zip(self, vals_list):

            if not default.get('stage_id'):
                vals['stage_id'] = task.stage_id.id
            if 'active' not in default and not task['active'] and not self.env.context.get('copy_project'):
                vals['active'] = True
            if not default.get('name'):
                vals['name'] = task.name if self.env.context.get('copy_project') or self.env.context.get('copy_from_template') else self.env._("%s (copy)", task.name)
            if task.allow_milestones:
                vals['milestone_id'] = milestone_mapping.get(vals['milestone_id'], vals['milestone_id'])
            if not self.env.context.get('copy_from_project_template'):
                if not default.get('child_ids') and task.child_ids:
                    default = {
                        'parent_id': False,
                    }
                    current_task = task
                    if self.env.context.get('copy_from_template'):
                        current_task = current_task.with_context(active_test=True)
                    child_ids = current_task.child_ids
                    vals['child_ids'] = [Command.create(child_id.copy_data(default)[0]) for child_id in child_ids]
            if not has_default_users and vals['user_ids']:
                task_active_users = task.user_ids & active_users
                vals['user_ids'] = [Command.set(task_active_users.ids)]
            if not self.env.context.get('is_copy_depend_task') and task.depend_on_ids:
                vals['depend_on_ids'] = [Command.clear()]

        return vals_list

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
    def default_get(self, fields):
        vals = super().default_get(fields)

        if project_id := self.env.context.get('default_create_in_project_id'):
            vals['project_id'] = project_id

        # prevent creating new task in the waiting state
        if 'state' in fields and vals.get('state') == '04_waiting_normal':
            vals['state'] = '01_in_progress'

        project_id = vals.get('project_id', self.env.context.get('default_project_id'))
        if project_id:
            project = self.env['project.project'].browse(project_id)
            if 'company_id' in fields and 'default_project_id' not in self.env.context:
                vals['company_id'] = project.sudo().company_id.id
        elif 'default_user_ids' not in self.env.context and 'user_ids' in fields:
            user_ids = vals.get('user_ids', [])
            user_ids.append(Command.link(self.env.user.id))
            vals['user_ids'] = user_ids

        parent_id = vals.get('parent_id', self.env.context.get('default_parent_id'))
        if parent_id:
            parent = self.env[self._name].browse(parent_id)
            if not vals.get('tag_ids'):
                vals['tag_ids'] = parent.tag_ids

        return vals

    def _set_stage_on_project_from_task(self):
        stage_ids_per_project = defaultdict(list)
        for task_template in self:
            if task_template.stage_id and task_template.stage_id not in task_template.project_id.type_ids and task_template.stage_id.id not in stage_ids_per_project[task_template.project_id]:
                stage_ids_per_project[task_template.project_id].append(task_template.stage_id.id)

        for project, stage_ids in stage_ids_per_project.items():
            project.write({'type_ids': [Command.link(stage_id) for stage_id in stage_ids]})

    @api.model_create_multi
    def create(self, vals_list):
        # Some values are determined by this override and must be written as
        # sudo for portal users, because they do not have access to these
        # fields. Other values must not be written as sudo.
        additional_vals_list = [{} for _ in vals_list]

        new_context = dict(self.env.context)
        default_project_id = new_context.pop('default_project_id', False)
        if not default_project_id:
            parent_task = self.browse({parent_id for vals in vals_list if (parent_id := vals.get('parent_id'))})
            if len(parent_task) == 1:
                default_project_id = parent_task.sudo().project_id.id
        # (portal) users that don't have write access can still create a task
        # in the project that will be checked using record rules
        new_context["default_create_in_project_id"] = default_project_id
        if not self._has_field_access(self._fields['user_ids'], 'write'):
            # remove user_ids if we have no access to it
            new_context.pop('default_user_ids', False)
        self_ctx = self.with_context(new_context)

        self_ctx.browse().check_access('create')
        default_stage = dict()
        for vals, additional_vals in zip(vals_list, additional_vals_list):
            project_id = vals.get('project_id') or default_project_id

            if vals.get('user_ids'):
                if not (vals.get('parent_id') or project_id):
                    user_ids = self_ctx._fields['user_ids'].convert_to_cache(vals.get('user_ids', []), self_ctx.env['project.task'])
                    if self_ctx.env.user.id not in list(user_ids) + [SUPERUSER_ID]:
                        additional_vals['user_ids'] = [Command.set(list(user_ids) + [self_ctx.env.user.id])]
            if not vals.get('name') and vals.get('display_name'):
                vals['name'] = vals['display_name']

            if project_id and not "company_id" in vals:
                additional_vals["company_id"] = self_ctx.env["project.project"].browse(
                    project_id
                ).company_id.id
            if not project_id and ("stage_id" in vals or self_ctx.env.context.get('default_stage_id')):
                vals["stage_id"] = False

            if project_id and "stage_id" not in vals:
                # 1) Allows keeping the batch creation of tasks
                # 2) Ensure the defaults are correct (and computed once by project),
                # by using default get (instead of _get_default_stage_id or _stage_find),
                if project_id not in default_stage:
                    default_stage[project_id] = self_ctx.with_context(
                        default_project_id=project_id
                    ).default_get(['stage_id']).get('stage_id')
                vals["stage_id"] = default_stage[project_id]

            # Stage change: Update date_end if folded stage and date_last_stage_update
            if vals.get('stage_id'):
                additional_vals.update(self_ctx.update_date_end(vals['stage_id']))
                additional_vals['date_last_stage_update'] = fields.Datetime.now()

        # create the task, write computed inaccessible fields in sudo
        for vals, computed_vals in zip(vals_list, additional_vals_list):
            for field_name in list(computed_vals):
                if self_ctx._has_field_access(self_ctx._fields[field_name], 'write'):
                    vals[field_name] = computed_vals.pop(field_name)
        # no track when the portal user create a task to avoid using during tracking
        # process since the portal does not have access to tracking models
        task_templates = super(ProjectTaskTemplate, self_ctx.with_context(mail_create_nosubscribe=True, mail_notrack=not self_ctx.env.su and self_ctx.env.user._is_portal())).create(vals_list)
        for task, computed_vals in zip(task_templates.sudo(), additional_vals_list):
            if computed_vals:
                task.write(computed_vals)
        if task_templates.project_id:
            task_templates.sudo()._set_stage_on_project_from_task()
        return task_templates

    def write(self, vals):
        if len(self) == 1:
            handle_history_divergence(self, 'description', vals)
        # Some values are determined by this override and must be written as
        # sudo for portal users, because they do not have access to these
        # fields. Other values must not be written as sudo.
        additional_vals = {}

        if 'milestone_id' in vals:
            # WARNING: has to be done after 'project_id' vals is written on subtasks
            milestone = self.env['project.milestone'].browse(vals['milestone_id'])

            # 1. Task for which the milestone is unvalid -> milestone_id is reset
            if 'project_id' not in vals:
                unvalid_milestone_tasks = self.filtered(lambda task: task.project_id != milestone.project_id) if vals['milestone_id'] else self.env[self._name]
            else:
                unvalid_milestone_tasks = self if not vals['milestone_id'] or milestone.project_id.id != vals['project_id'] else self.env[self._name]
            valid_milestone_tasks = self - unvalid_milestone_tasks
            if unvalid_milestone_tasks:
                unvalid_milestone_tasks.sudo().write({'milestone_id': False})
                if valid_milestone_tasks:
                    valid_milestone_tasks.sudo().write({'milestone_id': vals['milestone_id']})
                del vals['milestone_id']

            # 2. Parent's milestone is set to subtask with no milestone recursively
            subtasks_to_update = valid_milestone_tasks.child_ids.filtered(
                lambda task_template: (
                    task_template not in self and
                    not task_template.milestone_id and
                    task_template.project_id == milestone.project_id and
                    task_template.state not in CLOSED_STATES
                )
            )
            # 3. If parent and child task share the same milestone, child task's milestone is updated when the parent one is changed
            # No need to check if state is changed in vals as it won't affect the subtasks selected for update
            if 'project_id' not in vals:
                subtasks_to_update |= valid_milestone_tasks.child_ids.filtered(
                    lambda task_template: (
                        task_template not in self and
                        task_template.milestone_id == task_template.parent_id.milestone_id and
                        task_template.state not in CLOSED_STATES
                    )
                )
            else:
                subtasks_to_update |= valid_milestone_tasks.child_ids.filtered(
                    lambda task_template: (
                        task_template not in self and
                        (not task_template.display_in_project or task_template.project_id.id == vals['project_id']) and
                        task_template.milestone_id == task_template.parent_id.milestone_id and
                        task_template.state not in CLOSED_STATES
                    )
                )
            if subtasks_to_update:
                subtasks_to_update.sudo().write({'milestone_id': vals['milestone_id']})

        if vals.get('parent_id') in self.ids:
            raise UserError(self.env._("Sorry. You can't set a task as its parent task."))

        # stage change: update date_last_stage_update
        now = fields.Datetime.now()
        if 'stage_id' in vals:
            if not 'project_id' in vals and self.filtered(lambda t: not t.project_id):
                raise UserError(self.env._('You can only set a personal stage on a private task.'))

            additional_vals.update(self.update_date_end(vals['stage_id']))
            additional_vals['date_last_stage_update'] = now

        if vals.get('parent_id') is False:
            additional_vals['display_in_project'] = True
        if 'description' in vals:
            # the portal user cannot access to html_field_history and so it would be
            # better to write in sudo for description field to avoid giving access to html_field_history
            additional_vals['description'] = vals.pop('description')

        # write changes
        if self.env.su or not self.env.user._is_portal():
            vals.update(additional_vals)
        elif additional_vals:
            super(ProjectTaskTemplate, self.sudo()).write(additional_vals)
        result = super().write(vals)

        if 'project_id' in vals:
            self.filtered(lambda t: t.state != '04_waiting_normal').state = '01_in_progress'

        # Do not recompute the state when changing the parent (to avoid resetting the state)
        if 'parent_id' in vals:
            self.env.remove_to_compute(self._fields['state'], self)

        return result

    def update_date_end(self, stage_id):
        project_task_type = self.env['project.task.type'].browse(stage_id)
        if project_task_type.fold:
            return {'date_end': fields.Datetime.now()}
        return {'date_end': False}

    @api.depends('project_id')
    def _compute_milestone_id(self):
        for task_template in self:
            if task_template.project_id != task_template.milestone_id.project_id:
                task_template.milestone_id = task_template.parent_id.project_id == task_template.project_id and task_template.parent_id.milestone_id

    def _compute_has_late_and_unreached_milestone(self):
        if all(not task_template.allow_milestones for task_template in self):
            self.has_late_and_unreached_milestone = False
            return
        late_milestones = self.env['project.milestone'].sudo()._search([  # sudo is needed for the portal user in Project Sharing.
            ('id', 'in', self.milestone_id.ids),
            ('is_reached', '=', False),
            ('deadline', '<=', fields.Date.today()),
        ])
        for task_template in self:
            task_template.has_late_and_unreached_milestone = task_template.allow_milestones and task_template.milestone_id.id in late_milestones

    def _search_has_late_and_unreached_milestone(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [
            ('allow_milestones', '=', True),
            ('milestone_id', 'any', [
                ('is_reached', '=', False),
                ('deadline', '<', fields.Date.today()),
            ]),
        ]
    # ---------------------------------------------------
    # Subtasks
    # ---------------------------------------------------

    def _get_all_subtasks(self):
        return self.browse(set.union(set(), *self._get_subtask_ids_per_task_id().values()))

    def _get_subtask_ids_per_task_id(self):
        if not self:
            return {}
        res = {id_: [] for id_ in self._ids}
        if all(self._ids):
            query = f"""
                WITH RECURSIVE task_tree AS (
                    SELECT id, id as supertask_id
                      FROM {self._table}
                     WHERE id IN %(ancestor_ids)s
                    UNION
                    SELECT t.id, tree.supertask_id
                      FROM {self._table} t
                      JOIN task_tree tree
                        ON tree.id = t.parent_id
                       AND t.active in (TRUE, %(active)s)
                     WHERE t.parent_id IS NOT NULL
                )
                SELECT supertask_id, ARRAY_AGG(id)
                  FROM task_tree
                 WHERE id != supertask_id
                GROUP BY supertask_id
                """

            self.env.cr.execute(
                query,
                {
                    "ancestor_ids": tuple(self.ids),
                    "active": self.env.context.get('active_test', True),
                }
            )

            res.update(dict(self.env.cr.fetchall()))
        else:
            res.update({
                task_template.id: task_template._get_subtasks_recursively().ids
                for task_template in self
            })
        return res

    def _get_subtasks_recursively(self):
        children = self.child_ids
        if not children:
            return self.env[self._name]
        return children + children._get_subtasks_recursively()

    @api.depends('subtask_count', 'closed_subtask_count')
    def _compute_subtask_completion_percentage(self):
        for task_template in self:
            task_template.subtask_completion_percentage = task_template.subtask_count and task_template.closed_subtask_count / task_template.subtask_count

    def action_open_parent_task(self):
        return {
            'name': self.env._('Parent Task'),
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.parent_id.id,
            'type': 'ir.actions.act_window',
            'context': self.env.context,
        }

    def action_create_from_template(self, values=None):
        self.ensure_one()
        values = values or {}
        task_template_data = self.with_context(copy_from_template=True).copy_data(values)
        if task_template_data[0].get('recurring_task') and not task_template_data[0].get('repeat_interval'):
            task_template_data[0]['recurring_task'] = False
        task = self.env['project.task'].with_context(
            mail_create_nosubscribe=True,
            mail_create_nolog=True,
        ).sudo().create(task_template_data)
        task.message_post(subtype_xmlid='project.mt_task_new')
        return task.id

    def action_archive(self):
        child_task_template = self.child_ids.filtered(lambda child_task: not child_task.display_in_project)
        if child_task_template:
            child_task_template.action_archive()
        self.filtered(lambda t: not t.display_in_project and t.parent_id).display_in_project = True
        return super().action_archive()
