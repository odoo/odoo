# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import json
from collections import defaultdict
from datetime import timedelta

from odoo import api, Command, fields, models, _, _lt
from odoo.addons.rating.models import rating_data
from odoo.exceptions import UserError
from odoo.tools import get_lang, SQL
from .project_update import STATUS_COLOR
from .project_task import CLOSED_STATES


class Project(models.Model):
    _name = "project.project"
    _description = "Project"
    _inherit = ['portal.mixin', 'mail.alias.mixin', 'rating.parent.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = "sequence, name, id"
    _rating_satisfaction_days = 30  # takes 30 days by default
    _systray_view = 'activity'

    def _compute_attached_docs_count(self):
        docs_count = {}
        if self.ids:
            self.env.cr.execute(
                """
                WITH docs AS (
                     SELECT res_id as id, count(*) as count
                       FROM ir_attachment
                      WHERE res_model = 'project.project'
                        AND res_id IN %(project_ids)s
                   GROUP BY res_id

                  UNION ALL

                     SELECT t.project_id as id, count(*) as count
                       FROM ir_attachment a
                       JOIN project_task t ON a.res_model = 'project.task' AND a.res_id = t.id
                      WHERE t.project_id IN %(project_ids)s
                   GROUP BY t.project_id
                )
                SELECT id, sum(count)
                  FROM docs
              GROUP BY id
                """,
                {"project_ids": tuple(self.ids)}
            )
            docs_count = dict(self.env.cr.fetchall())
        for project in self:
            project.doc_count = docs_count.get(project.id, 0)

    def _compute_task_count(self):
        project_and_state_counts = self.env['project.task'].with_context(
            active_test=any(project.active for project in self)
        )._read_group(
            [('project_id', 'in', self.ids)],
            ['project_id', 'state'],
            ['__count'],
        )
        task_counts_per_project_id = defaultdict(lambda: {
            'open_task_count': 0,
            'closed_task_count': 0,
        })
        for project, state, count in project_and_state_counts:
            task_counts_per_project_id[project.id]['closed_task_count' if state in CLOSED_STATES else 'open_task_count'] += count
        for project in self:
            open_task_count, closed_task_count = task_counts_per_project_id[project.id].values()
            project.closed_task_count = closed_task_count
            project.task_count = open_task_count + closed_task_count

    def _default_stage_id(self):
        # Since project stages are order by sequence first, this should fetch the one with the lowest sequence number.
        return self.env['project.project.stage'].search([], limit=1)

    @api.model
    def _search_is_favorite(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))
        return [('favorite_user_ids', 'in' if (operator == '=') == value else 'not in', self.env.uid)]

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

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        return self.env['project.project.stage'].search([], order=order)

    name = fields.Char("Name", index='trigram', required=True, tracking=True, translate=True, default_export_compatible=True)
    description = fields.Html(help="Description to provide more information and context about this project")
    active = fields.Boolean(default=True,
        help="If the active field is set to False, it will allow you to hide the project without removing it.")
    sequence = fields.Integer(default=10)
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True, tracking=True, domain="['|', ('company_id', '=?', company_id), ('company_id', '=', False)]")
    company_id = fields.Many2one('res.company', string='Company', compute="_compute_company_id", inverse="_inverse_company_id", store=True, readonly=False)
    currency_id = fields.Many2one('res.currency', compute="_compute_currency_id", string="Currency", readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False, ondelete='set null',
        domain="['|', ('company_id', '=', False), ('company_id', '=?', company_id)]", check_company=True,
        help="Analytic account to which this project, its tasks and its timesheets are linked. \n"
            "Track the costs and revenues of your project by setting this analytic account on your related documents (e.g. sales orders, invoices, purchase orders, vendor bills, expenses etc.).\n"
            "This analytic account can be changed on each task individually if necessary.\n"
            "An analytic account is required in order to use timesheets.")
    analytic_account_balance = fields.Monetary(related="analytic_account_id.balance")

    favorite_user_ids = fields.Many2many(
        'res.users', 'project_favorite_user_rel', 'project_id', 'user_id',
        default=_get_default_favorite_user_ids,
        string='Members')
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite', search='_search_is_favorite',
        compute_sudo=True, string='Show Project on Dashboard')
    label_tasks = fields.Char(string='Use Tasks as', default='Tasks', translate=True,
        help="Name used to refer to the tasks of your project e.g. tasks, tickets, sprints, etc...")
    tasks = fields.One2many('project.task', 'project_id', string="Task Activities")
    resource_calendar_id = fields.Many2one(
        'resource.calendar', string='Working Time', compute='_compute_resource_calendar_id')
    type_ids = fields.Many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', string='Tasks Stages')
    task_count = fields.Integer(compute='_compute_task_count', string="Task Count")
    closed_task_count = fields.Integer(compute='_compute_task_count', string="Closed Task Count")
    task_ids = fields.One2many('project.task', 'project_id', string='Tasks',
                               domain=lambda self: [('state', 'in', self.env['project.task'].OPEN_STATES)])
    color = fields.Integer(string='Color Index')
    user_id = fields.Many2one('res.users', string='Project Manager', default=lambda self: self.env.user, tracking=True)
    alias_id = fields.Many2one(help="Internal email associated with this project. Incoming emails are automatically synchronized "
                                    "with Tasks (or optionally Issues if the Issue Tracker module is installed).")
    privacy_visibility = fields.Selection([
            ('followers', 'Invited internal users (private)'),
            ('employees', 'All internal users'),
            ('portal', 'Invited portal users and all internal users (public)'),
        ],
        string='Visibility', required=True,
        default='portal',
        help="People to whom this project and its tasks will be visible.\n\n"
            "- Invited internal users: when following a project, internal users will get access to all of its tasks without distinction. "
            "Otherwise, they will only get access to the specific tasks they are following.\n "
            "A user with the project > administrator access right level can still access this project and its tasks, even if they are not explicitly part of the followers.\n\n"
            "- All internal users: all internal users can access the project and all of its tasks without distinction.\n\n"
            "- Invited portal users and all internal users: all internal users can access the project and all of its tasks without distinction.\n"
            "When following a project, portal users will get access to all of its tasks without distinction. Otherwise, they will only get access to the specific tasks they are following.\n\n"
            "When a project is shared in read-only, the portal user is redirected to their portal. They can view the tasks, but not edit them.\n"
            "When a project is shared in edit, the portal user is redirected to the kanban and list views of the tasks. They can modify a selected number of fields on the tasks.\n\n"
            "In any case, an internal user with no project access rights can still access a task, "
            "provided that they are given the corresponding URL (and that they are part of the followers if the project is private).")
    privacy_visibility_warning = fields.Char('Privacy Visibility Warning', compute='_compute_privacy_visibility_warning')
    access_instruction_message = fields.Char('Access Instruction Message', compute='_compute_access_instruction_message')
    doc_count = fields.Integer(compute='_compute_attached_docs_count', string="Number of documents attached")
    date_start = fields.Date(string='Start Date')
    date = fields.Date(string='Expiration Date', index=True, tracking=True,
        help="Date on which this project ends. The timeframe defined on the project is taken into account when viewing its planning.")
    allow_task_dependencies = fields.Boolean('Task Dependencies', default=lambda self: self.env.user.has_group('project.group_project_task_dependencies'))
    allow_milestones = fields.Boolean('Milestones', default=lambda self: self.env.user.has_group('project.group_project_milestone'))
    tag_ids = fields.Many2many('project.tags', relation='project_project_project_tags_rel', string='Tags')
    task_properties_definition = fields.PropertiesDefinition('Task Properties')

    # Project Sharing fields
    collaborator_ids = fields.One2many('project.collaborator', 'project_id', string='Collaborators', copy=False)
    collaborator_count = fields.Integer('# Collaborators', compute='_compute_collaborator_count', compute_sudo=True)

    # rating fields
    rating_request_deadline = fields.Datetime(compute='_compute_rating_request_deadline', store=True)
    rating_active = fields.Boolean('Customer Ratings', default=lambda self: self.env.user.has_group('project.group_project_rating'))
    allow_rating = fields.Boolean('Allow Customer Ratings', compute="_compute_allow_rating", default=lambda self: self.env.user.has_group('project.group_project_rating'))
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
        tracking=True, index=True, copy=False, default=_default_stage_id, group_expand='_read_group_stage_ids')

    update_ids = fields.One2many('project.update', 'project_id')
    last_update_id = fields.Many2one('project.update', string='Last Update', copy=False)
    last_update_status = fields.Selection(selection=[
        ('on_track', 'On Track'),
        ('at_risk', 'At Risk'),
        ('off_track', 'Off Track'),
        ('on_hold', 'On Hold'),
        ('to_define', 'Set Status'),
        ('done', 'Done'),
    ], default='to_define', compute='_compute_last_update_status', store=True, readonly=False, required=True)
    last_update_color = fields.Integer(compute='_compute_last_update_color')
    milestone_ids = fields.One2many('project.milestone', 'project_id')
    milestone_count = fields.Integer(compute='_compute_milestone_count', groups='project.group_project_milestone')
    milestone_count_reached = fields.Integer(compute='_compute_milestone_reached_count', groups='project.group_project_milestone')
    is_milestone_exceeded = fields.Boolean(compute="_compute_is_milestone_exceeded", search='_search_is_milestone_exceeded')

    _sql_constraints = [
        ('project_date_greater', 'check(date >= date_start)', "The project's start date must be before its end date.")
    ]

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if (self.env.user.has_group('project.group_project_stages') and self.stage_id.company_id
                and self.stage_id.company_id != self.company_id):
            self.stage_id = self.env['project.project.stage'].search(
                [('company_id', 'in', [self.company_id.id, False])],
                order=f"sequence asc, {self.env['project.project.stage']._order}",
                limit=1,
            ).id

    def _compute_access_url(self):
        super(Project, self)._compute_access_url()
        for project in self:
            project.access_url = f'/my/projects/{project.id}'

    def _compute_access_warning(self):
        super(Project, self)._compute_access_warning()
        for project in self.filtered(lambda x: x.privacy_visibility != 'portal'):
            project.access_warning = _(
                "The project cannot be shared with the recipient(s) because the privacy of the project is too restricted. Set the privacy to 'Visible by following customers' in order to make it accessible by the recipient(s).")

    @api.depends_context('uid')
    def _compute_allow_rating(self):
        self.allow_rating = self.env.user.has_group('project.group_project_rating')

    @api.depends('analytic_account_id.company_id')
    def _compute_company_id(self):
        for project in self:
            # if a new restriction is put on the account, the restriction on the project is updated.
            if project.analytic_account_id.company_id:
                project.company_id = project.analytic_account_id.company_id

    @api.depends_context('company')
    @api.depends('company_id', 'company_id.resource_calendar_id')
    def _compute_resource_calendar_id(self):
        for project in self:
            project.resource_calendar_id = project.company_id.resource_calendar_id or self.env.company.resource_calendar_id

    def _inverse_company_id(self):
        """
        Ensures that the new company of the project is valid for the account. If not set back the previous company, and raise a user Error.
        Ensures that the new company of the project is valid for the partner
        """
        for project in self:
            account = project.analytic_account_id
            if project.partner_id and project.partner_id.company_id and project.company_id and project.company_id != project.partner_id.company_id:
                raise UserError(_('The project and the associated partner must be linked to the same company.'))
            if not account or not account.company_id:
                continue
            # if the account of the project has more than one company linked to it, or if it has aal, do not update the account, and set back the old company on the project.
            if (account.project_count > 1 or account.line_ids) and project.company_id != account.company_id:
                raise UserError(
                    _("The project's company cannot be changed if its analytic account has analytic lines or if more than one project is linked to it."))
            account.company_id = project.company_id

    @api.depends('rating_status', 'rating_status_period')
    def _compute_rating_request_deadline(self):
        periods = {'daily': 1, 'weekly': 7, 'bimonthly': 15, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        for project in self:
            project.rating_request_deadline = fields.datetime.now() + timedelta(days=periods.get(project.rating_status_period, 0))

    @api.depends('last_update_id.status')
    def _compute_last_update_status(self):
        for project in self:
            project.last_update_status = project.last_update_id.status or 'to_define'

    @api.depends('last_update_status')
    def _compute_last_update_color(self):
        for project in self:
            project.last_update_color = STATUS_COLOR[project.last_update_status]

    @api.depends('milestone_ids')
    def _compute_milestone_count(self):
        read_group = self.env['project.milestone']._read_group([('project_id', 'in', self.ids)], ['project_id'], ['__count'])
        mapped_count = {project.id: count for project, count in read_group}
        for project in self:
            project.milestone_count = mapped_count.get(project.id, 0)

    @api.depends('milestone_ids.is_reached')
    def _compute_milestone_reached_count(self):
        read_group = self.env['project.milestone']._read_group(
            [('project_id', 'in', self.ids), ('is_reached', '=', True)],
            ['project_id'],
            ['__count'],
        )
        mapped_count = {project.id: count for project, count in read_group}
        for project in self:
            project.milestone_count_reached = mapped_count.get(project.id, 0)

    @api.depends('milestone_ids', 'milestone_ids.is_reached', 'milestone_ids.deadline', 'allow_milestones')
    def _compute_is_milestone_exceeded(self):
        today = fields.Date.context_today(self)
        read_group = self.env['project.milestone']._read_group([
            ('project_id', 'in', self.filtered('allow_milestones').ids),
            ('is_reached', '=', False),
            ('deadline', '<=', today)], ['project_id'], ['__count'])
        mapped_count = {project.id: count for project, count in read_group}
        for project in self:
            project.is_milestone_exceeded = bool(mapped_count.get(project.id, 0))

    @api.depends_context('company')
    @api.depends('company_id')
    def _compute_currency_id(self):
        default_currency_id = self.env.company.currency_id
        for project in self:
            project.currency_id = project.company_id.currency_id or default_currency_id

    @api.model
    def _search_is_milestone_exceeded(self, operator, value):
        if not isinstance(value, bool):
            raise ValueError(_('Invalid value: %s', value))
        if operator not in ['=', '!=']:
            raise ValueError(_('Invalid operator: %s', operator))

        query = """
            SELECT P.id
              FROM project_project P
         LEFT JOIN project_milestone M ON P.id = M.project_id
             WHERE M.is_reached IS false
               AND P.allow_milestones IS true
               AND M.deadline <= CAST(now() AS date)
        """
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            operator_new = 'inselect'
        else:
            operator_new = 'not inselect'
        return [('id', operator_new, (query, ()))]

    @api.depends('collaborator_ids', 'privacy_visibility')
    def _compute_collaborator_count(self):
        project_sharings = self.filtered(lambda project: project.privacy_visibility == 'portal')
        collaborator_read_group = self.env['project.collaborator']._read_group(
            [('project_id', 'in', project_sharings.ids)],
            ['project_id'],
            ['__count'],
        )
        collaborator_count_by_project = {project.id: count for project, count in collaborator_read_group}
        for project in self:
            project.collaborator_count = collaborator_count_by_project.get(project.id, 0)

    @api.depends('privacy_visibility')
    def _compute_privacy_visibility_warning(self):
        for project in self:
            if not project.ids:
                project.privacy_visibility_warning = ''
            elif project.privacy_visibility == 'portal' and project._origin.privacy_visibility != 'portal':
                project.privacy_visibility_warning = _('Customers will be added to the followers of their project and tasks.')
            elif project.privacy_visibility != 'portal' and project._origin.privacy_visibility == 'portal':
                project.privacy_visibility_warning = _('Portal users will be removed from the followers of the project and its tasks.')
            else:
                project.privacy_visibility_warning = ''

    @api.depends('privacy_visibility')
    def _compute_access_instruction_message(self):
        for project in self:
            if project.privacy_visibility == 'portal':
                project.access_instruction_message = _('Grant portal users access to your project or tasks by adding them as followers. Customers automatically get access to their tasks in their portal.')
            elif project.privacy_visibility == 'followers':
                project.access_instruction_message = _('Grant employees access to your project or tasks by adding them as followers. Employees automatically get access to the tasks they are assigned to.')
            else:
                project.access_instruction_message = ''

    # TODO: Remove in master
    @api.onchange('date_start', 'date')
    def _onchange_planned_date(self):
        return

    @api.model
    def _map_tasks_default_valeus(self, task, project):
        """ get the default value for the copied task on project duplication """
        return {
            'stage_id': task.stage_id.id,
            'name': task.name,
            'state': task.state,
            'company_id': project.company_id.id,
            'project_id': project.id,
        }

    def map_tasks(self, new_project_id):
        """ copy and map tasks from old to new project """
        project = self.browse(new_project_id)
        new_tasks = self.env['project.task']
        # We want to copy archived task, but do not propagate an active_test context key
        task_ids = self.env['project.task'].with_context(active_test=False).search([('project_id', '=', self.id), ('parent_id', '=', False)]).ids
        if self.allow_task_dependencies and 'task_mapping' not in self.env.context:
            self = self.with_context(task_mapping=dict())
        for task in self.env['project.task'].browse(task_ids):
            # preserve task name and stage, normally altered during copy
            defaults = self._map_tasks_default_valeus(task, project)
            new_tasks |= task.copy(defaults)
        all_subtasks = new_tasks._get_all_subtasks()
        subtasks_not_displayed = all_subtasks.filtered(
            lambda task: not task.display_in_project
        )
        project.write({'tasks': [Command.set(new_tasks.ids)]})
        subtasks_not_displayed.write({
            'display_in_project': False
        })
        return True

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)", self.name)
        self_with_mail_context = self.with_context(mail_auto_subscribe_no_notify=True, mail_create_nosubscribe=True)
        project = super(Project, self_with_mail_context).copy(default)
        for follower in self.message_follower_ids:
            project.message_subscribe(partner_ids=follower.partner_id.ids, subtype_ids=follower.subtype_ids.ids)
        if self.allow_milestones:
            if 'milestone_mapping' not in self.env.context:
                self = self.with_context(milestone_mapping=dict())
            project.milestone_ids = [milestone.copy().id for milestone in self.milestone_ids]
        if 'tasks' not in default:
            self.map_tasks(project.id)

        return project

    @api.model
    def name_create(self, name):
        res = super().name_create(name)
        if res:
            # We create a default stage `new` for projects created on the fly.
            self.browse(res[0]).type_ids += self.env['project.task.type'].sudo().create({'name': _('New')})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # Prevent double project creation
        self = self.with_context(mail_create_nosubscribe=True)
        if any('label_tasks' in vals and not vals['label_tasks'] for vals in vals_list):
            task_label = _("Tasks")
            for vals in vals_list:
                if 'label_tasks' in vals and not vals['label_tasks']:
                    vals['label_tasks'] = task_label
        if len(self.env.companies) > 1 and self.env.user.has_group('project.group_project_stages'):
            # Select the stage whether the default_stage_id field is set in context (quick create) or if it is not (normal create)
            stage = self.env['project.project.stage'].browse(self._context['default_stage_id']) if 'default_stage_id' in self._context else self._default_stage_id()
            # The project's company_id must be the same as the stage's company_id
            if stage.company_id:
                for vals in vals_list:
                    vals['company_id'] = stage.company_id.id
        projects = super().create(vals_list)
        return projects

    def write(self, vals):
        # Here we modify the project's stage according to the selected company (selecting the first
        # stage in sequence that is linked to the company).
        company_id = vals.get('company_id')
        if self.env.user.has_group('project.group_project_stages') and company_id:
            projects_already_with_company = self.filtered(lambda p: p.company_id.id == company_id)
            if projects_already_with_company:
                projects_already_with_company.write({key: value for key, value in vals.items() if key != 'company_id'})
                self -= projects_already_with_company
            if company_id not in (None, *self.company_id.ids) and self.stage_id.company_id:
                ProjectStage = self.env['project.project.stage']
                vals["stage_id"] = ProjectStage.search(
                    [('company_id', 'in', (company_id, False))],
                    order=f"sequence asc, {ProjectStage._order}",
                    limit=1,
                ).id

        # directly compute is_favorite to dodge allow write access right
        if 'is_favorite' in vals:
            vals.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)

        if 'last_update_status' in vals and vals['last_update_status'] != 'to_define':
            for project in self:
                # This does not benefit from multi create, this is to allow the default description from being built.
                # This does seem ok since last_update_status should only be updated on one record at once.
                self.env['project.update'].with_context(default_project_id=project.id).create({
                    'name': _('Status Update - ') + fields.Date.today().strftime(get_lang(self.env).date_format),
                    'status': vals.get('last_update_status'),
                })
            vals.pop('last_update_status')
        if vals.get('privacy_visibility'):
            self._change_privacy_visibility(vals['privacy_visibility'])

        date_start = vals.get('date_start', True)
        date_end = vals.get('date', True)
        if not date_start or not date_end:
            vals['date_start'] = False
            vals['date'] = False
        else:
            no_current_date_begin = not all(project.date_start for project in self)
            no_current_date_end = not all(project.date for project in self)
            date_start_update = 'date_start' in vals
            date_end_update = 'date' in vals
            if (date_start_update and no_current_date_end and not date_end_update):
                del vals['date_start']
            elif (date_end_update and no_current_date_begin and not date_start_update):
                del vals['date']

        res = super(Project, self).write(vals) if vals else True

        if 'allow_task_dependencies' in vals and not vals.get('allow_task_dependencies'):
            self.env['project.task'].search([('project_id', 'in', self.ids), ('state', '=', '04_waiting_normal')]).write({'state': '01_in_progress'})

        if 'active' in vals:
            # archiving/unarchiving a project does it on its tasks, too
            self.with_context(active_test=False).mapped('tasks').write({'active': vals['active']})
        if 'name' in vals and self.analytic_account_id:
            projects_read_group = self.env['project.project']._read_group(
                [('analytic_account_id', 'in', self.analytic_account_id.ids)],
                ['analytic_account_id'],
                having=[('__count', '=', 1)],
            )
            analytic_account_to_update = self.env['account.analytic.account'].browse([
                analytic_account.id for [analytic_account] in projects_read_group
            ])
            analytic_account_to_update.write({'name': self.name})
        return res

    def unlink(self):
        # Delete the empty related analytic account
        analytic_accounts_to_delete = self.env['account.analytic.account']
        tasks = self.with_context(active_test=False).tasks
        for project in self:
            if project.analytic_account_id and not project.analytic_account_id.line_ids:
                analytic_accounts_to_delete |= project.analytic_account_id
        result = super(Project, self).unlink()
        tasks.unlink()
        analytic_accounts_to_delete.unlink()
        return result

    def _order_field_to_sql(self, alias, field_name, direction, nulls, query):
        if field_name == 'is_favorite':
            sql_field = SQL(
                "%s IN (SELECT project_id FROM project_favorite_user_rel WHERE user_id = %s)",
                SQL.identifier(alias, 'id'), self.env.uid,
            )
            return SQL("%s %s %s", sql_field, direction, nulls)

        return super()._order_field_to_sql(alias, field_name, direction, nulls, query)

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        """
        Subscribe to newly created task but not all existing active task when subscribing to a project.
        User update notification preference of project its propagated to all the tasks that the user is
        currently following.
        """
        res = super(Project, self).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
        if subtype_ids:
            project_subtypes = self.env['mail.message.subtype'].browse(subtype_ids)
            task_subtypes = (project_subtypes.mapped('parent_id') | project_subtypes.filtered(lambda sub: sub.internal or sub.default)).ids
            if task_subtypes:
                for task in self.task_ids:
                    partners = set(task.message_partner_ids.ids) & set(partner_ids)
                    if partners:
                        task.message_subscribe(partner_ids=list(partners), subtype_ids=task_subtypes)
                self.update_ids.message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
        return res

    def _alias_get_creation_values(self):
        values = super(Project, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('project.task').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['project_id'] = self.id
        return values

    @api.constrains('stage_id')
    def _ensure_stage_has_same_company(self):
        for project in self:
            if project.stage_id.company_id and project.stage_id.company_id != project.company_id:
                raise UserError(
                    _('This project is associated with %s, whereas the selected stage belongs to %s. '
                    'There are a couple of options to consider: either remove the company designation '
                    'from the project or from the stage. Alternatively, you can update the company '
                    'information for these records to align them under the same company.', project.company_id.name, project.stage_id.company_id.name)
                    if project.company_id else
                    _('This project is not associated to any company, while the stage is associated to %s. '
                    'There are a couple of options to consider: either change the project\'s company '
                    'to align with the stage\'s company or remove the company designation from the stage', project.stage_id.company_id.name)
                )

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _track_template(self, changes):
        res = super()._track_template(changes)
        project = self[0]
        if self.user_has_groups('project.group_project_stages') and 'stage_id' in changes and project.stage_id.mail_template_id:
            res['stage_id'] = (project.stage_id.mail_template_id, {
                'auto_delete_keep_log': False,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light',
            })
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values:
            return self.env.ref('project.mt_project_stage_change')
        return super()._track_subtype(init_values)

    def _mail_get_message_subtypes(self):
        res = super()._mail_get_message_subtypes()
        if not self.rating_active:
            res -= self.env.ref('project.mt_project_task_rating')
        if len(self) == 1:
            waiting_subtype = self.env.ref('project.mt_project_task_waiting')
            if not self.allow_task_dependencies and waiting_subtype in res:
                res -= waiting_subtype
        return res

    # ---------------------------------------------------
    #  Actions
    # ---------------------------------------------------

    def action_project_task_burndown_chart_report(self):
        action = self.env['ir.actions.act_window']._for_xml_id('project.action_project_task_burndown_chart_report')
        action['display_name'] = _("%(name)s's Burndown Chart", name=self.name)
        context = action['context'].replace('active_id', str(self.id))
        context = ast.literal_eval(context)
        context.update({
            'stage_name_and_sequence_per_id': {
                stage.id: {
                    'sequence': stage.sequence,
                    'name': stage.name
                } for stage in self.type_ids
            }
        })
        action['context'] = context
        return action

    # TODO to remove in master
    def action_project_timesheets(self):
        pass

    def project_update_all_action(self):
        action = self.env['ir.actions.act_window']._for_xml_id('project.project_update_all_action')
        action['display_name'] = _("%(name)s's Updates", name=self.name)
        return action

    def action_project_sharing(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('project.project_sharing_project_task_action')
        action['context'] = {
            'default_project_id': self.id,
            'delete': False,
            'search_default_open_tasks': True,
            'active_id_chatter': self.id,
        }
        action['display_name'] = self.name
        return action

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

    def action_view_tasks(self):
        action = self.env['ir.actions.act_window'].with_context({'active_id': self.id})._for_xml_id('project.act_project_project_2_project_task_all')
        action['display_name'] = _("%(name)s", name=self.name)
        context = action['context'].replace('active_id', str(self.id))
        context = ast.literal_eval(context)
        context.update({
            'create': self.active,
            'active_test': self.active
            })
        action['context'] = context
        return action

    def action_view_all_rating(self):
        """ return the action to see all the rating of the project and activate default filters"""
        action = self.env['ir.actions.act_window']._for_xml_id('project.rating_rating_action_view_project_rating')
        action['display_name'] = _("%(name)s's Rating", name=self.name)
        action_context = ast.literal_eval(action['context']) if action['context'] else {}
        action_context.update(self._context)
        action_context['search_default_rating_last_30_days'] = 1
        action_context.pop('group_by', None)
        action['domain'] = [('consumed', '=', True), ('parent_res_model', '=', 'project.project'), ('parent_res_id', '=', self.id)]
        if self.rating_count == 1:
            action.update({
                'view_mode': 'form',
                'views': [(view_id, view_type) for view_id, view_type in action['views'] if view_type == 'form'],
                'res_id': self.rating_ids[0].id, # [0] since rating_ids might be > then rating_count
            })
        return dict(action, context=action_context)

    def action_view_tasks_analysis(self):
        """ return the action to see the tasks analysis report of the project """
        action = self.env['ir.actions.act_window']._for_xml_id('project.action_project_task_user_tree')
        action['display_name'] = _("%(name)s's Tasks Analysis", name=self.name)
        action_context = ast.literal_eval(action['context']) if action['context'] else {}
        action_context['search_default_project_id'] = self.id
        return dict(action, context=action_context)

    def action_get_list_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("%(name)s's Milestones", name=self.name),
            'domain': [('project_id', '=', self.id)],
            'res_model': 'project.milestone',
            'views': [(self.env.ref('project.project_milestone_view_tree').id, 'tree')],
            'view_mode': 'tree',
            'help': _("""
                <p class="o_view_nocontent_smiling_face">
                    No milestones found. Let's create one!
                </p><p>
                    Track major progress points that must be reached to achieve success.
                </p>
            """),
            'context': {
                'default_project_id': self.id,
                **self.env.context
            }
        }

    # ---------------------------------------------
    #  PROJECT UPDATES
    # ---------------------------------------------

    def action_profitability_items(self, section_name, domain=None, res_id=False):
        return {}

    def get_last_update_or_default(self):
        self.ensure_one()
        labels = dict(self._fields['last_update_status']._description_selection(self.env))
        return {
            'status': labels.get(self.last_update_status, _('Set Status')),
            'color': self.last_update_color,
        }

    def get_panel_data(self):
        self.ensure_one()
        if not self.user_has_groups('project.group_project_user'):
            return {}
        show_profitability = self._show_profitability()
        panel_data = {
            'user': self._get_user_values(),
            'buttons': sorted(self._get_stat_buttons(), key=lambda k: k['sequence']),
            'currency_id': self.currency_id.id,
            'show_project_profitability_helper': show_profitability and self._show_profitability_helper(),
        }
        if self.allow_milestones:
            panel_data['milestones'] = self._get_milestones()
        if show_profitability:
            profitability_items = self._get_profitability_items()
            if self._get_profitability_sequence_per_invoice_type() and profitability_items and 'revenues' in profitability_items and 'costs' in profitability_items:  # sort the data values
                profitability_items['revenues']['data'] = sorted(profitability_items['revenues']['data'], key=lambda k: k['sequence'])
                profitability_items['costs']['data'] = sorted(profitability_items['costs']['data'], key=lambda k: k['sequence'])
            panel_data['profitability_items'] = profitability_items
            panel_data['profitability_labels'] = self._get_profitability_labels()
        return panel_data

    def get_milestones(self):
        if self.user_has_groups('project.group_project_user'):
            return self._get_milestones()
        return {}

    def _get_profitability_labels(self):
        return {}

    def _get_profitability_sequence_per_invoice_type(self):
        return {}

    def _get_already_included_profitability_invoice_line_ids(self):
        # To be extended to avoid account.move.line overlap between
        # profitability reports.
        return []

    def _get_user_values(self):
        return {
            'is_project_user': self.user_has_groups('project.group_project_user'),
        }

    def _show_profitability(self):
        self.ensure_one()
        return True

    def _show_profitability_helper(self):
        return self.user_has_groups('analytic.group_analytic_accounting')

    def _get_profitability_aal_domain(self):
        return [('account_id', 'in', self.analytic_account_id.ids)]

    def _get_profitability_items(self, with_action=True):
        return self._get_items_from_aal(with_action)

    def _get_items_from_aal(self, with_action=True):
        return {
            'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
            'costs': {'data': [], 'total': {'billed': 0.0, 'to_bill': 0.0}},
        }

    def _get_milestones(self):
        self.ensure_one()
        return {
            'data': self.milestone_ids._get_data_list(),
        }

    def _get_stat_buttons(self):
        self.ensure_one()
        if self.task_count:
            number = _lt(
                "%(closed_task_count)s / %(task_count)s (%(closed_rate)s%%)",
                closed_task_count=self.closed_task_count,
                task_count=self.task_count,
                closed_rate=round(100 * self.closed_task_count / self.task_count),
            )
        else:
            number = _lt(
                "%(closed_task_count)s / %(task_count)s",
                closed_task_count=self.closed_task_count,
                task_count=self.task_count,
            )
        buttons = [{
            'icon': 'check',
            'text': _lt('Tasks'),
            'number': number,
            'action_type': 'object',
            'action': 'action_view_tasks',
            'show': True,
            'sequence': 1,
        }]
        if self.rating_count != 0 and self.user_has_groups('project.group_project_rating'):
            if self.rating_avg >= rating_data.RATING_AVG_TOP:
                icon = 'smile-o text-success'
            elif self.rating_avg >= rating_data.RATING_AVG_OK:
                icon = 'meh-o text-warning'
            else:
                icon = 'frown-o text-danger'
            buttons.append({
                'icon': icon,
                'text': _lt('Average Rating'),
                'number': f'{int(self.rating_avg) if self.rating_avg.is_integer() else round(self.rating_avg, 1)} / 5',
                'action_type': 'object',
                'action': 'action_view_all_rating',
                'show': self.rating_active,
                'sequence': 15,
            })
        if self.user_has_groups('project.group_project_user'):
            buttons.append({
                'icon': 'area-chart',
                'text': _lt('Burndown Chart'),
                'action_type': 'action',
                'action': 'project.action_project_task_burndown_chart_report',
                'additional_context': json.dumps({
                    'active_id': self.id,
                    'stage_name_and_sequence_per_id': {
                        stage.id: {
                            'sequence': stage.sequence,
                            'name': stage.name
                        } for stage in self.type_ids
                    },
                }),
                'show': True,
                'sequence': 60,
            })
        return buttons

    # ---------------------------------------------------
    #  Business Methods
    # ---------------------------------------------------

    def _get_hide_partner(self):
        return False

    @api.model
    def _create_analytic_account_from_values(self, values):
        company = self.env['res.company'].browse(values.get('company_id', False))
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        analytic_account = self.env['account.analytic.account'].create({
            'name': values.get('name', _('Unknown Analytic Account')),
            'company_id': company.id,
            'partner_id': values.get('partner_id'),
            'plan_id': project_plan.id,
        })
        return analytic_account

    def _create_analytic_account(self):
        for project in self:
            company_id = project.company_id.id
            project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
            analytic_account = self.env['account.analytic.account'].create({
                'name': project.name,
                'company_id': company_id,
                'partner_id': project.partner_id.id,
                'plan_id': project_plan.id,
                'active': True,
            })
            project.write({'analytic_account_id': analytic_account.id})

    def _get_projects_to_make_billable_domain(self):
        return [('partner_id', '!=', False)]

    # ---------------------------------------------------
    # Rating business
    # ---------------------------------------------------

    # This method should be called once a day by the scheduler
    @api.model
    def _send_rating_all(self):
        projects = self.search([
            ('rating_active', '=', True),
            ('rating_status', '=', 'periodic'),
            ('rating_request_deadline', '<=', fields.Datetime.now())
        ])
        for project in projects:
            project.task_ids._send_task_rating_mail()
            project._compute_rating_request_deadline()
            self.env.cr.commit()

    # ---------------------------------------------------
    # Privacy
    # ---------------------------------------------------

    def _change_privacy_visibility(self, new_visibility):
        """
        Unsubscribe non-internal users from the project and tasks if the project privacy visibility
        goes from 'portal' to a different value.
        If the privacy visibility is set to 'portal', subscribe back project and tasks partners.
        """
        for project in self:
            if project.privacy_visibility == new_visibility:
                continue
            if new_visibility == 'portal':
                project.message_subscribe(partner_ids=project.partner_id.ids)
                for task in project.task_ids.filtered('partner_id'):
                    task.message_subscribe(partner_ids=task.partner_id.ids)
            elif project.privacy_visibility == 'portal':
                portal_users = project.message_partner_ids.user_ids.filtered('share')
                project.message_unsubscribe(partner_ids=portal_users.partner_id.ids)
                project.tasks._unsubscribe_portal_users()

    # ---------------------------------------------------
    # Project sharing
    # ---------------------------------------------------
    def _check_project_sharing_access(self):
        self.ensure_one()
        if self.privacy_visibility != 'portal':
            return False
        if self.env.user.has_group('base.group_portal'):
            return self.env['project.collaborator'].search([('project_id', '=', self.sudo().id), ('partner_id', '=', self.env.user.partner_id.id)])
        return self.env.user._is_internal()

    def _add_collaborators(self, partners):
        self.ensure_one()
        user_group_id = self.env['ir.model.data']._xmlid_to_res_id('base.group_user')
        all_collaborators = self.collaborator_ids.partner_id
        new_collaborators = partners.filtered(
            lambda partner:
                partner not in all_collaborators
                and (not partner.user_ids or user_group_id not in partner.user_ids[0].groups_id.ids)
        )
        if not new_collaborators:
            # Then we have nothing to do
            return
        self.write({'collaborator_ids': [
            Command.create({
                'partner_id': collaborator.id,
            }) for collaborator in new_collaborators],
        })
