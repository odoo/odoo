# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)


class ProjectProjectTemplate(models.Model):
    _name = 'project.project.template'
    _description = "Project Template"

    def __compute_task_temp_count(self, count_field='task_count'):
        count_fields = {fname for fname in self._fields if 'count' in fname}
        if count_field not in count_fields:
            raise ValueError(f"Parameter 'count_field' can only be one of {count_fields}, got {count_field} instead.")
        domain = Domain('project_template_id', 'in', self.ids)
        ProjectTask = self.env['project.task.template'].with_context(active_test=any(project_template.active for project_template in self))
        templates_count_by_project = dict(ProjectTask._read_group(domain, ['project_template_id'], ['__count']))
        for project_template in self:
            templates_count_by_project.get(project_template, 0)
            project_template.update({count_field: templates_count_by_project.get(project_template, 0)})

    def _compute_task_count(self):
        self.__compute_task_temp_count()

    def _default_stage_id(self):
        # Since project stages are order by sequence first, this should fetch the one with the lowest sequence number.
        return self.env['project.project.stage'].search([], limit=1)

    @api.model
    def _search_is_favorite(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [('favorite_user_ids', 'in', [self.env.uid])]

    name = fields.Char("Name", index='trigram', required=True, translate=True, default_export_compatible=True)
    description = fields.Html(help="Description to provide more information and context about this project")
    active = fields.Boolean(default=True, copy=False, export_string_translation=False)
    sequence = fields.Integer(default=10, export_string_translation=False)
    company_id = fields.Many2one('res.company', string='Company', store=True, readonly=False)

    resource_calendar_id = fields.Many2one(
        'resource.calendar', string='Working Time', compute='_compute_resource_calendar_id', export_string_translation=False)
    label_tasks = fields.Char(string='Use Tasks as', default=lambda s: s.env._('Tasks'), translate=True,
        help="Name used to refer to the tasks of your project e.g. tasks, tickets, sprints, etc...")
    type_ids = fields.Many2many('project.task.type', string='Tasks Stages in Template', export_string_translation=False)
    task_count = fields.Integer(compute='_compute_task_count', string="Task Count", export_string_translation=False)
    task_template_ids = fields.One2many('project.task.template', 'project_template_id', string='Task Templates', export_string_translation=False,
                               domain="[('is_closed', '=', False)]", copy=False)
    color = fields.Integer(string='Color Index', export_string_translation=False)
    user_id = fields.Many2one('res.users', string='Project Manager', default=lambda self: self.env.user, falsy_value_label=_lt("👤 Unassigned"))
    privacy_visibility = fields.Selection([
            ('followers', 'Invited internal users'),
            ('invited_users', 'Invited internal and portal users'),
            ('employees', 'All internal users'),
            ('portal', ' All internal users and invited portal users'),
        ],
        string='Visibility', required=True,
        default='portal',
        help="Project and Task Visibility:\n"
            "- Invited internal users: Can access only the project or tasks they follow. Assignees automatically get access.\n"
            "- Invited internal and portal users: Same as above, extended to portal users.\n"
            "- All internal users: Full access to the project and all its tasks.\n"
            "- All internal and invited portal users: Internal users get full access. Portal users can access only the project or tasks they follow.\n\n"
            "Portal Access Levels:\n"
            "- Read-only: Portal users see tasks via their portal but can’t edit them.\n"
            "- Edit (limited): Portal users access kanban/list views and can edit limited fields on followed tasks.\n"
            "- Edit: Same as above, with access to all tasks.\n\n"
            "Other Rules:\n"
            "- Internal users can open a task from a direct link, even without project access.\n"
            "- Project admins have access to private projects, even if not followers.\n")
    privacy_visibility_warning = fields.Char('Privacy Visibility Warning', compute='_compute_privacy_visibility_warning', export_string_translation=False)
    access_instruction_message = fields.Char('Access Instruction Message', compute='_compute_access_instruction_message', export_string_translation=False)
    date_start = fields.Date(string='Start Date', copy=False)
    date = fields.Date(string='Expiration Date', copy=False, index=True,
        help="Date on which this project ends. The timeframe defined on the project is taken into account when viewing its planning.")
    allow_task_dependencies = fields.Boolean('Task Dependencies', default=lambda self: self.env.user.has_group('project.group_project_task_dependencies'), inverse='_inverse_allow_task_dependencies')
    allow_milestones = fields.Boolean('Milestones', default=lambda self: self.env.user.has_group('project.group_project_milestone'))
    tag_ids = fields.Many2many('project.tags', string='Tags')
    task_properties_definition = fields.PropertiesDefinition('Task Properties')

    # rating fields
    rating_active = fields.Boolean('Customer Ratings', default=lambda self: self.env.user.has_group('project.group_project_rating'))
    rating_status = fields.Selection(
        [('stage', 'when reaching a given stage'),
         ('periodic', 'on a periodic basis')
        ], 'Customer Ratings Status', default="stage", required=True,
        help="Collect feedback from your customers by sending them a rating request when a task enters a certain stage. To do so, define a rating email template on the corresponding stages.\n"
             "Rating when changing stage: an email will be automatically sent when the task reaches the stage on which the rating email template is set.\n"
             "Periodic rating: an email will be automatically sent at regular intervals as long as the task remains in the stage in which the rating email template is set.")
    rating_status_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('bimonthly', 'Twice a Month'),
        ('monthly', 'Once a Month'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')], 'Rating Frequency', required=True, default='monthly')

    # Not `required` since this is an option to enable in project settings.
    stage_id = fields.Many2one('project.project.stage', string='Stage', ondelete='restrict', groups="project.group_project_stages",
        index=True, copy=False, default=_default_stage_id, group_expand='_read_group_expand_full')
    stage_id_color = fields.Integer(string='Stage Color', related="stage_id.color", export_string_translation=False)

    milestone_ids = fields.One2many('project.milestone', 'project_template_id', copy=True, export_string_translation=False)
    milestone_count = fields.Integer(compute='_compute_milestone_count', groups='project.group_project_milestone', export_string_translation=False)

    _project_date_greater = models.Constraint(
        'check(date >= date_start)',
        "The project's start date must be before its end date.",
    )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if (self.env.user.has_group('project.group_project_stages') and self.stage_id.company_id
                and self.stage_id.company_id != self.company_id):
            self.stage_id = self.env['project.project.stage'].search(
                [('company_id', 'in', [self.company_id.id, False])],
                order=f"sequence asc, {self.env['project.project.stage']._order}",
                limit=1,
            ).id

    @api.depends_context('company')
    @api.depends('company_id', 'company_id.resource_calendar_id')
    def _compute_resource_calendar_id(self):
        for template in self:
            template.resource_calendar_id = template.company_id.resource_calendar_id or self.env.company.resource_calendar_id

    @api.depends('privacy_visibility')
    def _compute_privacy_visibility_warning(self):
        _ = self.env._
        for project_template in self:
            if not project_template.ids:
                project_template.privacy_visibility_warning = ''
            elif project_template.privacy_visibility in ['invited_users', 'portal'] and project_template._origin.privacy_visibility not in ['invited_users', 'portal']:
                project_template.privacy_visibility_warning = _('Customers will be added to the followers of their project and tasks.')
            elif project_template.privacy_visibility not in ['invited_users', 'portal'] and project_template._origin.privacy_visibility in ['invited_users', 'portal']:
                project_template.privacy_visibility_warning = _('Portal users will be removed from the followers of the project and its tasks.')
            else:
                project_template.privacy_visibility_warning = ''

    @api.depends('privacy_visibility')
    def _compute_access_instruction_message(self):
        _ = self.env._
        for project_template in self:
            if project_template.privacy_visibility == 'portal':
                project_template.access_instruction_message = _('To give portal users access to your project, add them as followers. For task access, add them as followers for each task.')
            elif project_template.privacy_visibility == 'followers':
                project_template.access_instruction_message = _('Grant employees access to your project or tasks by adding them as followers. Employees automatically get access to the tasks they are assigned to.')
            elif project_template.privacy_visibility == 'invited_users':
                project_template.access_instruction_message = _("Grant users access by adding them as followers — either to the project or individual tasks. Internal users automatically gain access to tasks they are assigned to.")
            else:
                project_template.access_instruction_message = ''

    def _inverse_allow_task_dependencies(self):
        """ Reset state for waiting tasks in the project if the feature is disabled
            or recompute the tasks with dependencies if the project has the feature enabled again
        """
        project_with_task_dependencies_feature = self.filtered('allow_task_dependencies')
        projects_without_task_dependencies_feature = self - project_with_task_dependencies_feature
        ProjectTask = self.env['project.task']
        if (
            project_with_task_dependencies_feature
            and (
                open_tasks_with_dependencies := ProjectTask.search([
                    ('project_id', 'in', project_with_task_dependencies_feature.ids),
                    ('depend_on_ids.state', 'in', ProjectTask.OPEN_STATES),
                    ('state', 'in', ProjectTask.OPEN_STATES),
                ])
            )
        ):
            open_tasks_with_dependencies.state = '04_waiting_normal'
        if (
            projects_without_task_dependencies_feature
            and (
                waiting_tasks := ProjectTask.search([
                    ('project_id', 'in', projects_without_task_dependencies_feature.ids),
                    ('state', '=', '04_waiting_normal'),
                ])
            )
        ):
            waiting_tasks.state = '01_in_progress'

    @api.depends('milestone_ids')
    def _compute_milestone_count(self):
        read_group = self.env['project.milestone']._read_group([('project_template_id', 'in', self.ids)], ['project_template_id'], ['__count'])
        mapped_count = {template.id: count for template, count in read_group}
        for template in self:
            template.milestone_count = mapped_count.get(template.id, 0)

    @api.model
    def _map_tasks_default_values(self, project):
        """ get the default value for the copied task on project duplication.
        The stage_id, name field will be set for each task in the overwritten copy_data function in project.task """
        return {
            'state': '01_in_progress',
            'company_id': project.company_id.id,
            'project_template_id': project.id,
        }

    def map_tasks(self, new_project_id):
        """ copy and map tasks from old to new project Template"""
        template = self.browse(new_project_id)
        # We want to copy archived task, but do not propagate an active_test context key
        task_templates = self.env['project.task.template'].with_context(active_test=False).search([('project_template_id', '=', self.id), ('parent_id', '=', False)])
        self_ctx = self.with_context(self.env.context)
        if self.allow_task_dependencies and 'task_mapping' not in self.env.context:
            self_ctx = self.with_context(task_mapping=dict())
        # preserve task name and stage, normally altered during copy
        defaults = self_ctx._map_tasks_default_values(template)
        new_tasks = task_templates.with_context(copy_project=True).copy(defaults)
        all_subtasks = new_tasks._get_all_subtasks()
        all_subtasks.filtered(
            lambda child: child.project_template_id == self_ctx,
        ).write({
            'project_template_id': template.id,
        })
        return True

    @api.model_create_multi
    def create(self, vals_list):
        # Prevent double project creation
        if any('label_tasks' in vals and not vals['label_tasks'] for vals in vals_list):
            task_label = self.env._("Tasks")
            for vals in vals_list:
                if 'label_tasks' in vals and not vals['label_tasks']:
                    vals['label_tasks'] = task_label
        if self.env.user.has_group('project.group_project_stages'):
            if 'default_stage_id' in self.env.context:
                stage = self.env['project.project.stage'].browse(self.env.context['default_stage_id'])
                # The project's company_id must be the same as the stage's company_id
                if stage.company_id:
                    for vals in vals_list:
                        if vals.get('stage_id'):
                            continue
                        vals['company_id'] = stage.company_id.id
            else:
                companies_ids = [vals.get('company_id', False) for vals in vals_list] + [False]
                stages = self.env['project.project.stage'].search([('company_id', 'in', companies_ids)])
                for vals in vals_list:
                    if vals.get('stage_id'):
                        continue
                    # Pick the stage with the lowest sequence with no company or project's company
                    stage_domain = [False] if 'company_id' not in vals else [False, vals.get('company_id')]
                    stage = stages.filtered(lambda s: s.company_id.id in stage_domain)[:1]
                    vals['stage_id'] = stage.id

        for vals in vals_list:
            if vals.pop('is_favorite', False):
                vals['favorite_user_ids'] = [self.env.uid]
        projects = super().create(vals_list)
        return projects

    def copy(self, default=None):
        if self.env.context.get("from_project"):
            return super().copy(default=default)
        default = dict(default or {})
        # Since we dont want to copy the milestones if the original project has the feature disabled, we set the milestones to False by default.
        default['milestone_ids'] = False
        copy_context = dict(
             self.env.context,
             mail_auto_subscribe_no_notify=True,
             mail_create_nosubscribe=True,
         )
        copy_context.pop("default_stage_id", None)
        new_projects = super(ProjectProjectTemplate, self.with_context(copy_context)).copy(default=default)
        self_ctx = self.env.context
        if 'milestone_mapping' not in self_ctx:
            self_ctx = self.with_context(milestone_mapping={})
        for old_project, new_project in zip(self, new_projects):
            if old_project.allow_milestones:
                new_project.milestone_ids = self_ctx.milestone_ids.copy().ids
            if 'tasks' not in default:
                old_project.map_tasks(new_project.id)
            if not old_project.active:
                new_project.with_context(active_test=False).tasks.active = True
        return new_projects

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if self.env.context.get('copy_from_template') or 'name' in (default or {}):
            return vals_list
        return [dict(vals, name=self.env._("%s (copy)", project.name)) for project, vals in zip(self, vals_list)]

    def action_view_tasks(self):
        action = self.env['ir.actions.act_window'].with_context(active_id=self.id)._for_xml_id('project.act_project_template_2_task_template_all')
        action['display_name'] = self.name
        context = action['context'].replace('active_id', str(self.id))
        context = ast.literal_eval(context)
        context.update({
            'create': self.active,
            'active_test': self.active,
            'active_id': self.id,
        })
        action['context'] = context
        action['domain'] = action['domain'].replace('active_id', str(self.id))
        view_id_per_view_type = {
            'kanban': self.env.ref("project.view_task_template_kanban_default_groupby_stage_id").id,
            'list': self.env.ref("project.view_task_template_list_default_groupby_stage_id").id,
        }
        action["views"] = [
            (view_id_per_view_type.get(v_type, v_id), v_type)
            for v_id, v_type in action["views"]
        ]
        return action

    def action_get_list_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('project.project_milestone_action')
        action['display_name'] = self.env._("%(name)s's Milestones", name=self.name)
        return action

    def action_create_from_template(self, values=None, role_to_users_mapping=None):
        self.ensure_one()
        values = values or {}
        if self.date_start and self.date:
            if not values.get("date_start"):
                values["date_start"] = fields.Date.today()
            if not values.get("date"):
                values["date"] = values["date_start"] + (self.date - self.date_start)
        project_template_data = self.with_context(copy_from_template=True, copy_from_project_template=True).copy_data(default=values)
        project = self.env['project.project'].with_context(
            mail_create_nosubscribe=True,
            mail_create_nolog=True,
        ).sudo().create(project_template_data)
        self.task_template_ids.filtered(lambda t: t.is_task_template).\
            with_context(copy_from_template=True, is_copy_depend_task=True).\
            copy({'project_id': project.id, 'project_template_id': False})
        temp_converted_to_tasks = self.task_template_ids.filtered(lambda t: not t.is_task_template)
        if temp_converted_to_tasks:
            task_data = temp_converted_to_tasks.with_context(copy_from_project_template=True, copy_from_template=True, is_copy_depend_task=True).\
                copy_data({'project_id': project.id, 'project_template_id': False})
            created_tasks = self.env['project.task'].create(task_data)
            template_to_new = dict(zip(temp_converted_to_tasks, created_tasks))
            for template, new_task in template_to_new.items():
                if template.parent_id:
                    new_task.parent_id = template_to_new[template.parent_id]
        project.message_post(body=self.env._("Project created from template %(name)s.", name=self.name))

        # Tasks dispatching using project roles
        project.task_ids.role_ids = False
        if role_to_users_mapping and (mapping := role_to_users_mapping.filtered(lambda entry: entry.user_ids)):
            for template_task, new_task in zip(self.task_template_ids, project.task_ids):
                for entry in mapping:
                    if entry.role_id in template_task.role_ids:
                        new_task.user_ids |= entry.user_ids
        return project
