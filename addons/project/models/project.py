# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from datetime import timedelta, datetime
from random import randint

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError, RedirectWarning
from odoo.tools.misc import format_date, get_lang
from odoo.osv.expression import OR

from .project_task_recurrence import DAYS, WEEKS

class ProjectTaskType(models.Model):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence, id'

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=1)
    project_ids = fields.Many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', string='Projects',
        default=_get_default_project_ids)
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda s: _('Blocked'), translate=True, required=True,
        help='Override the default value displayed for the blocked state for kanban selection, when the task or issue is in that stage.')
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda s: _('Ready'), translate=True, required=True,
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
    is_closed = fields.Boolean('Closing Stage', help="Tasks in this stage are considered as closed.")
    disabled_rating_warning = fields.Text(compute='_compute_disabled_rating_warning')

    def unlink_wizard(self, stage_view=False):
        self = self.with_context(active_test=False)
        # retrieves all the projects with a least 1 task in that stage
        # a task can be in a stage even if the project is not assigned to the stage
        readgroup = self.with_context(active_test=False).env['project.task'].read_group([('stage_id', 'in', self.ids)], ['project_id'], ['project_id'])
        project_ids = list(set([project['project_id'][0] for project in readgroup] + self.project_ids.ids))

        wizard = self.with_context(project_ids=project_ids).env['project.task.type.delete.wizard'].create({
            'project_ids': project_ids,
            'stage_ids': self.ids
        })

        context = dict(self.env.context)
        context['stage_view'] = stage_view
        return {
            'name': _('Delete Stage'),
            'view_mode': 'form',
            'res_model': 'project.task.type.delete.wizard',
            'views': [(self.env.ref('project.view_project_task_type_delete_wizard').id, 'form')],
            'type': 'ir.actions.act_window',
            'res_id': wizard.id,
            'target': 'new',
            'context': context,
        }

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self.env['project.task'].search([('stage_id', 'in', self.ids)]).write({'active': False})
        return super(ProjectTaskType, self).write(vals)

    @api.depends('project_ids', 'project_ids.rating_active')
    def _compute_disabled_rating_warning(self):
        for stage in self:
            disabled_projects = stage.project_ids.filtered(lambda p: not p.rating_active)
            if disabled_projects:
                stage.disabled_rating_warning = '\n'.join('- %s' % p.name for p in disabled_projects)
            else:
                stage.disabled_rating_warning = False


class Project(models.Model):
    _name = "project.project"
    _description = "Project"
    _inherit = ['portal.mixin', 'mail.alias.mixin', 'mail.thread', 'rating.parent.mixin']
    _order = "sequence, name, id"
    _rating_satisfaction_days = False  # takes all existing ratings
    _check_company_auto = True

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
        task_data = self.env['project.task'].read_group([('project_id', 'in', self.ids), '|', '&', ('stage_id.is_closed', '=', False), ('stage_id.fold', '=', False), ('stage_id', '=', False)], ['project_id'], ['project_id'])
        result = dict((data['project_id'][0], data['project_id_count']) for data in task_data)
        for project in self:
            project.task_count = result.get(project.id, 0)

    def attachment_tree_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        action['domain'] = str([
            '|',
            '&',
            ('res_model', '=', 'project.project'),
            ('res_id', 'in', self.ids),
            '&',
            ('res_model', '=', 'project.task'),
            ('res_id', 'in', self.task_ids.ids)
        ])
        action['context'] = "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        return action

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

    name = fields.Char("Name", index=True, required=True, tracking=True)
    description = fields.Html()
    active = fields.Boolean(default=True,
        help="If the active field is set to False, it will allow you to hide the project without removing it.")
    sequence = fields.Integer(default=10, help="Gives the sequence order when displaying a list of Projects.")
    partner_id = fields.Many2one('res.partner', string='Customer', auto_join=True, tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_email = fields.Char(
        compute='_compute_partner_email', inverse='_inverse_partner_email',
        string='Email', readonly=False, store=True)
    partner_phone = fields.Char(
        compute='_compute_partner_phone', inverse='_inverse_partner_phone',
        string="Phone", readonly=False, store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", string="Currency", readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False, ondelete='set null',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", check_company=True,
        help="Analytic account to which this project is linked for financial management. "
             "Use an analytic account to record cost and revenue on your project.")

    favorite_user_ids = fields.Many2many(
        'res.users', 'project_favorite_user_rel', 'project_id', 'user_id',
        default=_get_default_favorite_user_ids,
        string='Members')
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite', string='Show Project on dashboard',
        help="Whether this project should be displayed on your dashboard.")
    label_tasks = fields.Char(string='Use Tasks as', default='Tasks', help="Label used for the tasks of the project.", translate=True)
    tasks = fields.One2many('project.task', 'project_id', string="Task Activities")
    resource_calendar_id = fields.Many2one(
        'resource.calendar', string='Working Time',
        related='company_id.resource_calendar_id')
    type_ids = fields.Many2many('project.task.type', 'project_task_type_rel', 'project_id', 'type_id', string='Tasks Stages')
    task_count = fields.Integer(compute='_compute_task_count', string="Task Count")
    task_ids = fields.One2many('project.task', 'project_id', string='Tasks',
                               domain=['|', ('stage_id.fold', '=', False), ('stage_id', '=', False)])
    color = fields.Integer(string='Color Index')
    user_id = fields.Many2one('res.users', string='Project Manager', default=lambda self: self.env.user, tracking=True)
    alias_enabled = fields.Boolean(string='Use email alias', compute='_compute_alias_enabled', readonly=False)
    alias_id = fields.Many2one('mail.alias', string='Alias', ondelete="restrict", required=True,
        help="Internal email associated with this project. Incoming emails are automatically synchronized "
             "with Tasks (or optionally Issues if the Issue Tracker module is installed).")
    privacy_visibility = fields.Selection([
            ('followers', 'Invited internal users'),
            ('employees', 'All internal users'),
            ('portal', 'Invited portal users and all internal users'),
        ],
        string='Visibility', required=True,
        default='portal',
        help="Defines the visibility of the tasks of the project:\n"
                "- Invited internal users: employees may only see the followed project and tasks.\n"
                "- All internal users: employees may see all project and tasks.\n"
                "- Invited portal and all internal users: employees may see everything."
                "   Portal users may see project and tasks followed by\n"
                "   them or by someone of their company.")

    allowed_user_ids = fields.Many2many('res.users', compute='_compute_allowed_users', inverse='_inverse_allowed_user')
    allowed_internal_user_ids = fields.Many2many('res.users', 'project_allowed_internal_users_rel',
                                                 string="Allowed Internal Users", default=lambda self: self.env.user, domain=[('share', '=', False)])
    allowed_portal_user_ids = fields.Many2many('res.users', 'project_allowed_portal_users_rel', string="Allowed Portal Users", domain=[('share', '=', True)])
    doc_count = fields.Integer(compute='_compute_attached_docs_count', string="Number of documents attached")
    date_start = fields.Date(string='Start Date')
    date = fields.Date(string='Expiration Date', index=True, tracking=True)
    subtask_project_id = fields.Many2one('project.project', string='Sub-task Project', ondelete="restrict",
        help="Project in which sub-tasks of the current project will be created. It can be the current project itself.")
    allow_subtasks = fields.Boolean('Sub-tasks', default=lambda self: self.env.user.has_group('project.group_subtask_project'))
    allow_recurring_tasks = fields.Boolean('Recurring Tasks', default=lambda self: self.env.user.has_group('project.group_project_recurring_tasks'))

    # rating fields
    rating_request_deadline = fields.Datetime(compute='_compute_rating_request_deadline', store=True)
    rating_active = fields.Boolean('Customer Ratings', default=True)
    rating_status = fields.Selection(
        [('stage', 'Rating when changing stage'),
         ('periodic', 'Periodical Rating')
        ], 'Customer Ratings Status', default="stage", required=True,
        help="How to get customer feedback?\n"
             "- Rating when changing stage: an email will be sent when a task is pulled in another stage.\n"
             "- Periodical Rating: email will be sent periodically.\n\n"
             "Don't forget to set up the mail templates on the stages for which you want to get the customer's feedbacks.")
    rating_status_period = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('bimonthly', 'Twice a Month'),
        ('monthly', 'Once a Month'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')], 'Rating Frequency', required=True, default='monthly')

    _sql_constraints = [
        ('project_date_greater', 'check(date >= date_start)', 'Error! project start-date must be lower than project end-date.')
    ]

    @api.depends('partner_id.email')
    def _compute_partner_email(self):
        for project in self:
            if project.partner_id and project.partner_id.email != project.partner_email:
                project.partner_email = project.partner_id.email

    def _inverse_partner_email(self):
        for project in self:
            if project.partner_id and project.partner_email != project.partner_id.email:
                project.partner_id.email = project.partner_email

    @api.depends('partner_id.phone')
    def _compute_partner_phone(self):
        for project in self:
            if project.partner_id and project.partner_phone != project.partner_id.phone:
                project.partner_phone = project.partner_id.phone

    def _inverse_partner_phone(self):
        for project in self:
            if project.partner_id and project.partner_phone != project.partner_id.phone:
                project.partner_id.phone = project.partner_phone

    @api.onchange('alias_enabled')
    def _onchange_alias_name(self):
        if not self.alias_enabled:
            self.alias_name = False

    def _compute_alias_enabled(self):
        for project in self:
            project.alias_enabled = project.alias_domain and project.alias_id.alias_name

    @api.depends('allowed_internal_user_ids', 'allowed_portal_user_ids')
    def _compute_allowed_users(self):
        for project in self:
            users = project.allowed_internal_user_ids | project.allowed_portal_user_ids
            project.allowed_user_ids = users

    def _inverse_allowed_user(self):
        for project in self:
            allowed_users = project.allowed_user_ids
            project.allowed_portal_user_ids = allowed_users.filtered('share')
            project.allowed_internal_user_ids = allowed_users - project.allowed_portal_user_ids

    def _compute_access_url(self):
        super(Project, self)._compute_access_url()
        for project in self:
            project.access_url = '/my/project/%s' % project.id

    def _compute_access_warning(self):
        super(Project, self)._compute_access_warning()
        for project in self.filtered(lambda x: x.privacy_visibility != 'portal'):
            project.access_warning = _(
                "The project cannot be shared with the recipient(s) because the privacy of the project is too restricted. Set the privacy to 'Visible by following customers' in order to make it accessible by the recipient(s).")

    @api.depends('rating_status', 'rating_status_period')
    def _compute_rating_request_deadline(self):
        periods = {'daily': 1, 'weekly': 7, 'bimonthly': 15, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        for project in self:
            project.rating_request_deadline = fields.datetime.now() + timedelta(days=periods.get(project.rating_status_period, 0))

    @api.model
    def _map_tasks_default_valeus(self, task, project):
        """ get the default value for the copied task on project duplication """
        return {
            'stage_id': task.stage_id.id,
            'name': task.name,
            'company_id': project.company_id.id,
        }

    def map_tasks(self, new_project_id):
        """ copy and map tasks from old to new project """
        project = self.browse(new_project_id)
        tasks = self.env['project.task']
        # We want to copy archived task, but do not propagate an active_test context key
        task_ids = self.env['project.task'].with_context(active_test=False).search([('project_id', '=', self.id)], order='parent_id').ids
        old_to_new_tasks = {}
        for task in self.env['project.task'].browse(task_ids):
            # preserve task name and stage, normally altered during copy
            defaults = self._map_tasks_default_valeus(task, project)
            if task.parent_id:
                # set the parent to the duplicated task
                defaults['parent_id'] = old_to_new_tasks.get(task.parent_id.id, False)
            new_task = task.copy(defaults)
            old_to_new_tasks[task.id] = new_task.id
            tasks += new_task

        return project.write({'tasks': [(6, 0, tasks.ids)]})

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)") % (self.name)
        project = super(Project, self).copy(default)
        if self.subtask_project_id == self:
            project.subtask_project_id = project
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
        if project.privacy_visibility == 'portal' and project.partner_id.user_ids:
            project.allowed_user_ids |= project.partner_id.user_ids
        return project

    def write(self, vals):
        allowed_users_changed = 'allowed_portal_user_ids' in vals or 'allowed_internal_user_ids' in vals
        if allowed_users_changed:
            allowed_users = {project: project.allowed_user_ids for project in self}
        # directly compute is_favorite to dodge allow write access right
        if 'is_favorite' in vals:
            vals.pop('is_favorite')
            self._fields['is_favorite'].determine_inverse(self)
        res = super(Project, self).write(vals) if vals else True

        if allowed_users_changed:
            for project in self:
                permission_removed = allowed_users.get(project) - project.allowed_user_ids
                allowed_portal_users_removed = permission_removed.filtered('share')
                project.message_unsubscribe(allowed_portal_users_removed.partner_id.commercial_partner_id.ids)
                for task in project.task_ids:
                    task.allowed_user_ids -= permission_removed

        if 'allow_recurring_tasks' in vals and not vals.get('allow_recurring_tasks'):
            self.env['project.task'].search([('project_id', 'in', self.ids), ('recurring_task', '=', True)]).write({'recurring_task': False})

        if 'active' in vals:
            # archiving/unarchiving a project does it on its tasks, too
            self.with_context(active_test=False).mapped('tasks').write({'active': vals['active']})
        if vals.get('partner_id') or vals.get('privacy_visibility'):
            for project in self.filtered(lambda project: project.privacy_visibility == 'portal'):
                project.allowed_user_ids |= project.partner_id.user_ids

        return res

    def action_unlink(self):
        wizard = self.env['project.delete.wizard'].create({
            'project_ids': self.ids
        })

        return {
            'name': _('Confirmation'),
            'view_mode': 'form',
            'res_model': 'project.delete.wizard',
            'views': [(self.env.ref('project.project_delete_wizard_form').id, 'form')],
            'type': 'ir.actions.act_window',
            'res_id': wizard.id,
            'target': 'new',
            'context': self.env.context,
        }

    def unlink(self):
        # Check project is empty
        for project in self.with_context(active_test=False):
            if project.tasks:
                raise UserError(_('You cannot delete a project containing tasks. You can either archive it or first delete all of its tasks.'))
        # Delete the empty related analytic account
        analytic_accounts_to_delete = self.env['account.analytic.account']
        for project in self:
            if project.analytic_account_id and not project.analytic_account_id.line_ids:
                analytic_accounts_to_delete |= project.analytic_account_id
        result = super(Project, self).unlink()
        analytic_accounts_to_delete.unlink()
        return result

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        """
        Subscribe to all existing active tasks when subscribing to a project
        And add the portal user subscribed to allowed portal users
        """
        res = super(Project, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
        project_subtypes = self.env['mail.message.subtype'].browse(subtype_ids) if subtype_ids else None
        task_subtypes = project_subtypes.mapped('parent_id').ids if project_subtypes else None
        if not subtype_ids or task_subtypes:
            self.mapped('tasks').message_subscribe(
                partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=task_subtypes)
        if partner_ids:
            all_users = self.env['res.partner'].browse(partner_ids).user_ids
            portal_users = all_users.filtered('share')
            internal_users = all_users - portal_users
            self.allowed_portal_user_ids |= portal_users
            self.allowed_internal_user_ids |= internal_users
        return res

    def message_unsubscribe(self, partner_ids=None, channel_ids=None):
        """ Unsubscribe from all tasks when unsubscribing from a project """
        self.mapped('tasks').message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)
        return super(Project, self).message_unsubscribe(partner_ids=partner_ids, channel_ids=channel_ids)

    def _alias_get_creation_values(self):
        values = super(Project, self)._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get('project.task').id
        if self.id:
            values['alias_defaults'] = defaults = ast.literal_eval(self.alias_defaults or "{}")
            defaults['project_id'] = self.id
        return values

    # ---------------------------------------------------
    #  Actions
    # ---------------------------------------------------

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
        action = self.with_context(active_id=self.id, active_ids=self.ids) \
            .env.ref('project.act_project_project_2_project_task_all') \
            .sudo().read()[0]
        action['display_name'] = self.name
        return action

    def action_view_account_analytic_line(self):
        """ return the action to see all the analytic lines of the project's analytic account """
        action = self.env["ir.actions.actions"]._for_xml_id("analytic.account_analytic_line_action")
        action['context'] = {'default_account_id': self.analytic_account_id.id}
        action['domain'] = [('account_id', '=', self.analytic_account_id.id)]
        return action

    def action_view_all_rating(self):
        """ return the action to see all the rating of the project and activate default filters"""
        action = self.env['ir.actions.act_window']._for_xml_id('project.rating_rating_action_view_project_rating')
        action['name'] = _('Ratings of %s') % (self.name,)
        action_context = ast.literal_eval(action['context']) if action['context'] else {}
        action_context.update(self._context)
        action_context['search_default_parent_res_name'] = self.name
        action_context.pop('group_by', None)
        return dict(action, context=action_context)

    # ---------------------------------------------------
    #  Business Methods
    # ---------------------------------------------------

    @api.model
    def _create_analytic_account_from_values(self, values):
        analytic_account = self.env['account.analytic.account'].create({
            'name': values.get('name', _('Unknown Analytic Account')),
            'company_id': values.get('company_id') or self.env.company.id,
            'partner_id': values.get('partner_id'),
            'active': True,
        })
        return analytic_account

    def _create_analytic_account(self):
        for project in self:
            analytic_account = self.env['account.analytic.account'].create({
                'name': project.name,
                'company_id': project.company_id.id,
                'partner_id': project.partner_id.id,
                'active': True,
            })
            project.write({'analytic_account_id': analytic_account.id})

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


class Task(models.Model):
    _name = "project.task"
    _description = "Task"
    _date_name = "date_assign"
    _inherit = ['portal.mixin', 'mail.thread.cc', 'mail.activity.mixin', 'rating.mixin']
    _mail_post_access = 'read'
    _order = "priority desc, sequence, id desc"
    _check_company_auto = True

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        return self.stage_find(project_id, [('fold', '=', False), ('is_closed', '=', False)])

    @api.model
    def _default_company_id(self):
        if self._context.get('default_project_id'):
            return self.env['project.project'].browse(self._context['default_project_id']).company_id
        return self.env.company

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = [('id', 'in', stages.ids)]
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain

        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    active = fields.Boolean(default=True)
    name = fields.Char(string='Title', tracking=True, required=True, index=True)
    description = fields.Html(string='Description')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Important'),
    ], default='0', index=True, string="Priority")
    sequence = fields.Integer(string='Sequence', index=True, default=10,
        help="Gives the sequence order when displaying a list of tasks.")
    stage_id = fields.Many2one('project.task.type', string='Stage', compute='_compute_stage_id',
        store=True, readonly=False, ondelete='restrict', tracking=True, index=True,
        default=_get_default_stage_id, group_expand='_read_group_stage_ids',
        domain="[('project_ids', '=', project_id)]", copy=False)
    tag_ids = fields.Many2many('project.tags', string='Tags')
    kanban_state = fields.Selection([
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked')], string='Kanban State',
        copy=False, default='normal', required=True)
    kanban_state_label = fields.Char(compute='_compute_kanban_state_label', string='Kanban State Label', tracking=True)
    create_date = fields.Datetime("Created On", readonly=True, index=True)
    write_date = fields.Datetime("Last Updated On", readonly=True, index=True)
    date_end = fields.Datetime(string='Ending Date', index=True, copy=False)
    date_assign = fields.Datetime(string='Assigning Date', index=True, copy=False, readonly=True)
    date_deadline = fields.Date(string='Deadline', index=True, copy=False, tracking=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update',
        index=True,
        copy=False,
        readonly=True)
    project_id = fields.Many2one('project.project', string='Project',
        compute='_compute_project_id', store=True, readonly=False,
        index=True, tracking=True, check_company=True, change_default=True)
    planned_hours = fields.Float("Initially Planned Hours", help='Time planned to achieve this task (including its sub-tasks).', tracking=True)
    subtask_planned_hours = fields.Float("Sub-tasks Planned Hours", compute='_compute_subtask_planned_hours', help="Sum of the time planned of all the sub-tasks linked to this task. Usually less or equal to the initially time planned of this task.")
    user_id = fields.Many2one('res.users',
        string='Assigned to',
        default=lambda self: self.env.uid,
        index=True, tracking=True)
    partner_id = fields.Many2one('res.partner',
        string='Customer',
        compute='_compute_partner_id', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_is_company = fields.Boolean(related='partner_id.is_company', readonly=True)
    commercial_partner_id = fields.Many2one(related='partner_id.commercial_partner_id')
    partner_email = fields.Char(
        compute='_compute_partner_email', inverse='_inverse_partner_email',
        string='Email', readonly=False, store=True)
    partner_phone = fields.Char(
        compute='_compute_partner_phone', inverse='_inverse_partner_phone',
        string="Phone", readonly=False, store=True)
    ribbon_message = fields.Char('Ribbon message', compute='_compute_ribbon_message')
    partner_city = fields.Char(related='partner_id.city', readonly=False)
    manager_id = fields.Many2one('res.users', string='Project Manager', related='project_id.user_id', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', compute='_compute_company_id', store=True, readonly=False,
        required=True, copy=True, default=_default_company_id)
    color = fields.Integer(string='Color Index')
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True, related_sudo=False)
    attachment_ids = fields.One2many('ir.attachment', compute='_compute_attachment_ids', string="Main Attachments",
        help="Attachment that don't come from message.")
    # In the domain of displayed_image_id, we couln't use attachment_ids because a one2many is represented as a list of commands so we used res_model & res_id
    displayed_image_id = fields.Many2one('ir.attachment', domain="[('res_model', '=', 'project.task'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]", string='Cover Image')
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked Explanation', readonly=True, related_sudo=False)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid Explanation', readonly=True, related_sudo=False)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing Explanation', readonly=True, related_sudo=False)
    is_closed = fields.Boolean(related="stage_id.is_closed", string="Closing Stage", readonly=True, related_sudo=False)
    parent_id = fields.Many2one('project.task', string='Parent Task', index=True)
    child_ids = fields.One2many('project.task', 'parent_id', string="Sub-tasks", context={'active_test': False})
    subtask_project_id = fields.Many2one('project.project', related="project_id.subtask_project_id", string='Sub-task Project', readonly=True)
    allow_subtasks = fields.Boolean(string="Allow Sub-tasks", related="project_id.allow_subtasks", readonly=True)
    subtask_count = fields.Integer("Sub-task count", compute='_compute_subtask_count')
    email_from = fields.Char(string='Email From', help="These people will receive email.", index=True,
        compute='_compute_email_from', store="True", readonly=False)
    allowed_user_ids = fields.Many2many('res.users', string="Visible to", groups='project.group_project_manager', compute='_compute_allowed_user_ids', store=True, readonly=False, copy=False)
    project_privacy_visibility = fields.Selection(related='project_id.privacy_visibility', string="Project Visibility")
    # Computed field about working time elapsed between record creation and assignation/closing.
    working_hours_open = fields.Float(compute='_compute_elapsed', string='Working hours to assign', store=True, group_operator="avg")
    working_hours_close = fields.Float(compute='_compute_elapsed', string='Working hours to close', store=True, group_operator="avg")
    working_days_open = fields.Float(compute='_compute_elapsed', string='Working days to assign', store=True, group_operator="avg")
    working_days_close = fields.Float(compute='_compute_elapsed', string='Working days to close', store=True, group_operator="avg")
    # customer portal: include comment and incoming emails in communication history
    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', 'in', ['email', 'comment'])])

    # recurrence fields
    allow_recurring_tasks = fields.Boolean(related='project_id.allow_recurring_tasks')
    recurring_task = fields.Boolean(string="Recurrent")
    recurring_count = fields.Integer(string="Tasks in Recurrence", compute='_compute_recurring_count')
    recurrence_id = fields.Many2one('project.task.recurrence', copy=False)
    recurrence_update = fields.Selection([
        ('this', 'This task'),
        ('subsequent', 'This and following tasks'),
        ('all', 'All tasks'),
    ], default='this', store=False)
    recurrence_message = fields.Char(string='Next Recurrencies', compute='_compute_recurrence_message')

    repeat_interval = fields.Integer(string='Repeat Every', default=1, compute='_compute_repeat', readonly=False)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', compute='_compute_repeat', readonly=False)
    repeat_type = fields.Selection([
        ('forever', 'Forever'),
        ('until', 'End Date'),
        ('after', 'Number of Repetitions'),
    ], default="forever", string="Until", compute='_compute_repeat', readonly=False)
    repeat_until = fields.Date(string="End Date", compute='_compute_repeat', readonly=False)
    repeat_number = fields.Integer(string="Repetitions", default=1, compute='_compute_repeat', readonly=False)

    repeat_on_month = fields.Selection([
        ('date', 'Date of the Month'),
        ('day', 'Day of the Month'),
    ], default='date', compute='_compute_repeat', readonly=False)

    repeat_on_year = fields.Selection([
        ('date', 'Date of the Year'),
        ('day', 'Day of the Year'),
    ], default='date', compute='_compute_repeat', readonly=False)

    mon = fields.Boolean(string="Mon", compute='_compute_repeat', readonly=False)
    tue = fields.Boolean(string="Tue", compute='_compute_repeat', readonly=False)
    wed = fields.Boolean(string="Wed", compute='_compute_repeat', readonly=False)
    thu = fields.Boolean(string="Thu", compute='_compute_repeat', readonly=False)
    fri = fields.Boolean(string="Fri", compute='_compute_repeat', readonly=False)
    sat = fields.Boolean(string="Sat", compute='_compute_repeat', readonly=False)
    sun = fields.Boolean(string="Sun", compute='_compute_repeat', readonly=False)

    repeat_day = fields.Selection([
        (str(i), str(i)) for i in range(1, 32)
    ], compute='_compute_repeat', readonly=False)
    repeat_week = fields.Selection([
        ('first', 'First'),
        ('second', 'Second'),
        ('third', 'Third'),
        ('last', 'Last'),
    ], default='first', compute='_compute_repeat', readonly=False)
    repeat_weekday = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ], string='Day Of The Week', compute='_compute_repeat', readonly=False)
    repeat_month = fields.Selection([
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March'),
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
    ], compute='_compute_repeat', readonly=False)

    repeat_show_dow = fields.Boolean(compute='_compute_repeat_visibility')
    repeat_show_day = fields.Boolean(compute='_compute_repeat_visibility')
    repeat_show_week = fields.Boolean(compute='_compute_repeat_visibility')
    repeat_show_month = fields.Boolean(compute='_compute_repeat_visibility')

    @api.model
    def _get_recurrence_fields(self):
        return ['repeat_interval', 'repeat_unit', 'repeat_type', 'repeat_until', 'repeat_number',
                'repeat_on_month', 'repeat_on_year', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat',
                'sun', 'repeat_day', 'repeat_week', 'repeat_month', 'repeat_weekday']

    @api.depends('recurring_task', 'repeat_unit', 'repeat_on_month', 'repeat_on_year')
    def _compute_repeat_visibility(self):
        for task in self:
            task.repeat_show_day = task.recurring_task and (task.repeat_unit == 'month' and task.repeat_on_month == 'date') or (task.repeat_unit == 'year' and task.repeat_on_year == 'date')
            task.repeat_show_week = task.recurring_task and (task.repeat_unit == 'month' and task.repeat_on_month == 'day') or (task.repeat_unit == 'year' and task.repeat_on_year == 'day')
            task.repeat_show_dow = task.recurring_task and task.repeat_unit == 'week'
            task.repeat_show_month = task.recurring_task and task.repeat_unit == 'year'

    @api.depends('recurring_task', 'repeat_unit')
    def _compute_repeat(self):
        rec_fields = self._get_recurrence_fields()
        defaults = self.default_get(rec_fields)
        for task in self:
            for f in rec_fields:
                if task.recurrence_id:
                    task[f] = task.recurrence_id[f]
                else:
                    if task.recurring_task:
                        task[f] = defaults.get(f)
                    else:
                        task[f] = False

    def _get_weekdays(self, n=1):
        self.ensure_one()
        if self.repeat_unit == 'week':
            return [fn(n) for day, fn in DAYS.items() if self[day]]
        return [DAYS.get(self.repeat_weekday)(n)]

    @api.depends(
        'recurring_task', 'repeat_interval', 'repeat_unit', 'repeat_type', 'repeat_until',
        'repeat_number', 'repeat_on_month', 'repeat_on_year', 'mon', 'tue', 'wed', 'thu', 'fri',
        'sat', 'sun', 'repeat_day', 'repeat_week', 'repeat_month', 'repeat_weekday')
    def _compute_recurrence_message(self):
        self.recurrence_message = False
        for task in self.filtered(lambda t: t.recurring_task and t._is_recurrence_valid()):
            date = fields.Date.today()
            number_occurrences = min(5, task.repeat_number if task.repeat_type == 'after' else 5)
            delta = task.repeat_interval if task.repeat_unit == 'day' else 1
            recurring_dates = self.env['project.task.recurrence']._get_next_recurring_dates(
                date + timedelta(days=delta),
                task.repeat_interval,
                task.repeat_unit,
                task.repeat_type,
                task.repeat_until,
                task.repeat_on_month,
                task.repeat_on_year,
                task._get_weekdays(WEEKS.get(task.repeat_week)),
                task.repeat_day,
                task.repeat_week,
                task.repeat_month,
                count=number_occurrences)
            date_format = self.env['res.lang']._lang_get(self.env.user.lang).date_format
            task.recurrence_message = '<ul>'
            for date in recurring_dates[:5]:
                task.recurrence_message += '<li>%s</li>' % date.strftime(date_format)
            if task.repeat_type == 'after' and task.repeat_number > 5 or task.repeat_type == 'forever' or len(recurring_dates) > 5:
                task.recurrence_message += '<li>...</li>'
            task.recurrence_message += '</ul>'
            if task.repeat_type == 'until':
                task.recurrence_message += _('<p><em>Number of tasks: %(tasks_count)s</em></p>') % {'tasks_count': len(recurring_dates)}

    def _is_recurrence_valid(self):
        self.ensure_one()
        return self.repeat_interval > 0 and\
                (not self.repeat_show_dow or self._get_weekdays()) and\
                (self.repeat_type != 'after' or self.repeat_number) and\
                (self.repeat_type != 'until' or self.repeat_until and self.repeat_until > fields.Date.today())

    @api.depends('recurrence_id')
    def _compute_recurring_count(self):
        self.recurring_count = 0
        recurring_tasks = self.filtered(lambda l: l.recurrence_id)
        count = self.env['project.task'].read_group([('recurrence_id', 'in', recurring_tasks.recurrence_id.ids)], ['id'], 'recurrence_id')
        tasks_count = {c.get('recurrence_id')[0]: c.get('recurrence_id_count') for c in count}
        for task in recurring_tasks:
            task.recurring_count = tasks_count.get(task.recurrence_id.id, 0)

    @api.depends('partner_id.email')
    def _compute_partner_email(self):
        for task in self:
            if task.partner_id and task.partner_id.email != task.partner_email:
                task.partner_email = task.partner_id.email

    def _inverse_partner_email(self):
        for task in self:
            if task.partner_id and task.partner_email != task.partner_id.email:
                task.partner_id.email = task.partner_email

    @api.depends('partner_id.phone')
    def _compute_partner_phone(self):
        for task in self:
            if task.partner_id and task.partner_phone != task.partner_id.phone:
                task.partner_phone = task.partner_id.phone

    def _inverse_partner_phone(self):
        for task in self:
            if task.partner_id and task.partner_phone != task.partner_id.phone:
                task.partner_id.phone = task.partner_phone

    @api.depends('partner_email', 'partner_phone', 'partner_id')
    def _compute_ribbon_message(self):
        for task in self:
            will_write_email = task.partner_id and task.partner_email != task.partner_id.email
            will_write_phone = task.partner_id and task.partner_phone != task.partner_id.phone

            if will_write_email and will_write_phone:
                task.ribbon_message = _('By saving this change, the customer email and phone number will also be updated.')
            elif will_write_email:
                task.ribbon_message = _('By saving this change, the customer email will also be updated.')
            elif will_write_phone:
                task.ribbon_message = _('By saving this change, the customer phone number will also be updated.')
            else:
                task.ribbon_message = False

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive hierarchy of tasks.'))

    @api.constrains('allowed_user_ids')
    def _check_no_portal_allowed(self):
        for task in self.filtered(lambda t: t.project_id.privacy_visibility != 'portal'):
            portal_users = task.allowed_user_ids.filtered('share')
            if portal_users:
                user_names = ', '.join(portal_users[:10].mapped('name'))
                raise ValidationError(_("The project visibility setting doesn't allow portal users to see the project's tasks. (%s)", user_names))

    def _compute_attachment_ids(self):
        for task in self:
            attachment_ids = self.env['ir.attachment'].search([('res_id', '=', task.id), ('res_model', '=', 'project.task')]).ids
            message_attachment_ids = task.mapped('message_ids.attachment_ids').ids  # from mail_thread
            task.attachment_ids = [(6, 0, list(set(attachment_ids) - set(message_attachment_ids)))]

    @api.depends('project_id.allowed_user_ids', 'project_id.privacy_visibility')
    def _compute_allowed_user_ids(self):
        for task in self:
            portal_users = task.allowed_user_ids.filtered('share')
            internal_users = task.allowed_user_ids - portal_users
            if task.project_id.privacy_visibility == 'followers':
                task.allowed_user_ids |= task.project_id.allowed_internal_user_ids
                task.allowed_user_ids -= portal_users
            elif task.project_id.privacy_visibility == 'portal':
                task.allowed_user_ids |= task.project_id.allowed_portal_user_ids
            if task.project_id.privacy_visibility != 'portal':
                task.allowed_user_ids -= portal_users
            elif task.project_id.privacy_visibility != 'followers':
                task.allowed_user_ids -= internal_users

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
            task.subtask_planned_hours = sum(child_task.planned_hours + child_task.subtask_planned_hours for child_task in task.child_ids)

    @api.depends('child_ids')
    def _compute_subtask_count(self):
        for task in self:
            task.subtask_count = len(task._get_all_subtasks())

    @api.onchange('company_id')
    def _onchange_task_company(self):
        if self.project_id.company_id != self.company_id:
            self.project_id = False

    @api.depends('project_id.company_id')
    def _compute_company_id(self):
        for task in self.filtered(lambda task: task.project_id):
            task.company_id = task.project_id.company_id

    @api.depends('project_id')
    def _compute_stage_id(self):
        for task in self:
            if task.project_id:
                if task.project_id not in task.stage_id.project_ids:
                    task.stage_id = task.stage_find(task.project_id.id, [
                        ('fold', '=', False), ('is_closed', '=', False)])
            else:
                task.stage_id = False

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _("%s (copy)", self.name)
        if self.recurrence_id:
            default['recurrence_id'] = self.recurrence_id.copy().id
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

    def message_subscribe(self, partner_ids=None, channel_ids=None, subtype_ids=None):
        """
        Add the users subscribed to allowed portal users
        """
        res = super(Task, self).message_subscribe(partner_ids=partner_ids, channel_ids=channel_ids, subtype_ids=subtype_ids)
        if partner_ids:
            new_allowed_users = self.env['res.partner'].browse(partner_ids).user_ids.filtered('share')
            tasks = self.filtered(lambda task: task.project_id.privacy_visibility == 'portal')
            tasks.sudo().write({'allowed_user_ids': [(4, user.id) for user in new_allowed_users]})
        return res

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
    def default_get(self, default_fields):
        vals = super(Task, self).default_get(default_fields)

        days = list(DAYS.keys())
        week_start = fields.Datetime.today().weekday()

        if all(d in default_fields for d in days):
            vals[days[week_start]] = True
        if 'repeat_day' in default_fields:
            vals['repeat_day'] = str(fields.Datetime.today().day)
        if 'repeat_month' in default_fields:
            vals['repeat_month'] = self._fields.get('repeat_month').selection[fields.Datetime.today().month - 1][0]
        if 'repeat_until' in default_fields:
            vals['repeat_until'] = fields.Date.today() + timedelta(days=7)
        if 'repeat_weekday' in default_fields:
            vals['repeat_weekday'] = self._fields.get('repeat_weekday').selection[week_start][0]

        return vals

    @api.model_create_multi
    def create(self, vals_list):
        default_stage = dict()
        for vals in vals_list:
            project_id = vals.get('project_id') or self.env.context.get('default_project_id')
            if project_id and not "company_id" in vals:
                vals["company_id"] = self.env["project.project"].browse(
                    project_id
                ).company_id.id or self.env.company.id
            if project_id and "stage_id" not in vals:
                # 1) Allows keeping the batch creation of tasks
                # 2) Ensure the defaults are correct (and computed once by project),
                # by using default get (instead of _get_default_stage_id or _stage_find),
                if project_id not in default_stage:
                    default_stage[project_id] = self.with_context(
                        default_project_id=project_id
                    ).default_get(['stage_id']).get('stage_id')
                vals["stage_id"] = default_stage[project_id]
            # user_id change: update date_assign
            if vals.get('user_id'):
                vals['date_assign'] = fields.Datetime.now()
            # Stage change: Update date_end if folded stage and date_last_stage_update
            if vals.get('stage_id'):
                vals.update(self.update_date_end(vals['stage_id']))
                vals['date_last_stage_update'] = fields.Datetime.now()
            # recurrence
            rec_fields = vals.keys() & self._get_recurrence_fields()
            if rec_fields and vals.get('recurring_task') is True:
                rec_values = {rec_field: vals[rec_field] for rec_field in rec_fields}
                rec_values['next_recurrence_date'] = fields.Datetime.today()
                recurrence = self.env['project.task.recurrence'].create(rec_values)
                vals['recurrence_id'] = recurrence.id
        tasks = super().create(vals_list)
        for task in tasks:
            if task.project_id.privacy_visibility == 'portal':
                task._portal_ensure_token()
        return tasks

    def write(self, vals):
        now = fields.Datetime.now()
        if 'parent_id' in vals and vals['parent_id'] in self.ids:
            raise UserError(_("Sorry. You can't set a task as its parent task."))
        if 'active' in vals and not vals.get('active') and any(self.mapped('recurrence_id')):
            # TODO: show a dialog to stop the recurrence
            raise UserError(_('You cannot archive recurring tasks. Please, disable the recurrence first.'))
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

        # recurrence fields
        rec_fields = vals.keys() & self._get_recurrence_fields()
        if rec_fields:
            rec_values = {rec_field: vals[rec_field] for rec_field in rec_fields}
            for task in self:
                if task.recurrence_id:
                    task.recurrence_id.write(rec_values)
                elif vals.get('recurring_task'):
                    rec_values['next_recurrence_date'] = fields.Datetime.today()
                    recurrence = self.env['project.task.recurrence'].create(rec_values)
                    task.recurrence_id = recurrence.id

        if 'recurring_task' in vals and not vals.get('recurring_task'):
            self.recurrence_id.unlink()

        tasks = self
        recurrence_update = vals.pop('recurrence_update', 'this')
        if recurrence_update != 'this':
            recurrence_domain = []
            if recurrence_update == 'subsequent':
                for task in self:
                    recurrence_domain = OR([recurrence_domain, ['&', ('recurrence_id', '=', task.recurrence_id.id), ('create_date', '>=', task.create_date)]])
            else:
                recurrence_domain = [('recurrence_id', 'in', self.recurrence_id.ids)]
            tasks |= self.env['project.task'].search(recurrence_domain)

        result = super(Task, tasks).write(vals)
        # rating on stage
        if 'stage_id' in vals and vals.get('stage_id'):
            self.filtered(lambda x: x.project_id.rating_active and x.project_id.rating_status == 'stage')._send_task_rating_mail(force_send=True)
        return result

    def update_date_end(self, stage_id):
        project_task_type = self.env['project.task.type'].browse(stage_id)
        if project_task_type.fold or project_task_type.is_closed:
            return {'date_end': fields.Datetime.now()}
        return {'date_end': False}

    def unlink(self):
        if any(self.mapped('recurrence_id')):
            # TODO: show a dialog to stop the recurrence
            raise UserError(_('You cannot delete recurring tasks. Please, disable the recurrence first.'))
        return super().unlink()

    # ---------------------------------------------------
    # Subtasks
    # ---------------------------------------------------

    @api.depends('parent_id.partner_id', 'project_id.partner_id')
    def _compute_partner_id(self):
        """
        If a task has no partner_id, use the project partner_id if any, or else the parent task partner_id.
        Once the task partner_id has been set:
            1) if the project partner_id changes, the task partner_id is automatically changed also.
            2) if the parent task partner_id changes, the task partner_id remains the same.
        """
        for task in self:
            if task.partner_id:
                if task.project_id.partner_id:
                    task.partner_id = task.project_id.partner_id
            else:
                task.partner_id = task.project_id.partner_id or task.parent_id.partner_id 

    @api.depends('partner_id.email', 'parent_id.email_from')
    def _compute_email_from(self):
        for task in self:
            task.email_from = task.partner_id.email or task.email_from or task.parent_id.email_from

    @api.depends('parent_id.project_id.subtask_project_id')
    def _compute_project_id(self):
        for task in self:
            if not task.project_id:
                task.project_id = task.parent_id.project_id.subtask_project_id

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _track_template(self, changes):
        res = super(Task, self)._track_template(changes)
        test_task = self[0]
        if 'stage_id' in changes and test_task.stage_id.mail_template_id:
            res['stage_id'] = (test_task.stage_id.mail_template_id, {
                'auto_delete_message': True,
                'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            })
        return res

    def _creation_subtype(self):
        return self.env.ref('project.mt_task_new')

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'kanban_state_label' in init_values and self.kanban_state == 'blocked':
            return self.env.ref('project.mt_task_blocked')
        elif 'kanban_state_label' in init_values and self.kanban_state == 'done':
            return self.env.ref('project.mt_task_ready')
        elif 'stage_id' in init_values:
            return self.env.ref('project.mt_task_stage')
        return super(Task, self)._track_subtype(init_values)

    def _notify_get_groups(self):
        """ Handle project users and managers recipients that can assign
        tasks and create new one directly from notification emails. Also give
        access button to portal users and portal customers. If they are notified
        they should probably have access to the document. """
        groups = super(Task, self)._notify_get_groups()

        self.ensure_one()

        project_user_group_id = self.env.ref('project.group_project_user').id

        group_func = lambda pdata: pdata['type'] == 'user' and project_user_group_id in pdata['groups']
        if self.project_id.privacy_visibility == 'followers':
            allowed_user_ids = self.project_id.allowed_internal_user_ids.partner_id.ids
            group_func = lambda pdata: pdata['type'] == 'user' and project_user_group_id in pdata['groups'] and pdata['id'] in allowed_user_ids
        new_group = ('group_project_user', group_func, {})

        if not self.user_id and not self.stage_id.fold:
            take_action = self._notify_get_action_link('assign')
            project_actions = [{'url': take_action, 'title': _('I take it')}]
            new_group[2]['actions'] = project_actions

        groups = [new_group] + groups

        if self.project_id.privacy_visibility == 'portal':
            allowed_user_ids = self.project_id.allowed_portal_user_ids.partner_id.ids
            groups.insert(0, (
                'allowed_portal_users',
                lambda pdata: pdata['type'] == 'portal' and pdata['id'] in allowed_user_ids,
                {}
            ))

        for group_name, group_method, group_data in groups:
            if group_name in ('customer', 'portal_customer', 'user'):
                group_data['has_button_access'] = False

        return groups

    def _notify_get_reply_to(self, default=None, records=None, company=None, doc_names=None):
        """ Override to set alias of tasks to their project if any. """
        aliases = self.sudo().mapped('project_id')._notify_get_reply_to(default=default, records=None, company=company, doc_names=None)
        res = {task.id: aliases.get(task.project_id.id) for task in self}
        leftover = self.filtered(lambda rec: not rec.project_id)
        if leftover:
            res.update(super(Task, leftover)._notify_get_reply_to(default=default, records=None, company=company, doc_names=doc_names))
        return res

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
            'planned_hours': 0.0,
            'partner_id': msg.get('author_id')
        }
        defaults.update(custom_values)

        task = super(Task, self.with_context(create_context)).message_new(msg, custom_values=defaults)
        email_list = task.email_split(msg)
        partner_ids = [p.id for p in self.env['mail.thread']._mail_find_partner_from_emails(email_list, records=task, force_create=False) if p]
        task.message_subscribe(partner_ids)
        return task

    def message_update(self, msg, update_vals=None):
        """ Override to update the task according to the email. """
        email_list = self.email_split(msg)
        partner_ids = [p.id for p in self.env['mail.thread']._mail_find_partner_from_emails(email_list, records=self, force_create=False) if p]
        self.message_subscribe(partner_ids)
        return super(Task, self).message_update(msg, update_vals=update_vals)

    def _message_get_suggested_recipients(self):
        recipients = super(Task, self)._message_get_suggested_recipients()
        for task in self:
            if task.partner_id:
                reason = _('Customer Email') if task.partner_id.email else _('Customer')
                task._message_add_suggested_recipient(recipients, partner=task.partner_id, reason=reason)
            elif task.email_from:
                task._message_add_suggested_recipient(recipients, email=task.email_from, reason=_('Customer Email'))
        return recipients

    def _notify_email_header_dict(self):
        headers = super(Task, self)._notify_email_header_dict()
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
        return super(Task, self)._message_post_after_hook(message, msg_vals)

    def action_assign_to_me(self):
        self.write({'user_id': self.env.user.id})

    # If depth == 1, return only direct children
    # If depth == 3, return children to third generation
    # If depth <= 0, return all children without depth limit
    def _get_all_subtasks(self, depth=0):
        children = self.mapped('child_ids').filtered(lambda children: children.active)
        if not children:
            return self.env['project.task']
        if depth == 1:
            return children
        return children + children._get_all_subtasks(depth - 1)

    def action_open_parent_task(self):
        return {
            'name': _('Parent Task'),
            'view_mode': 'form',
            'res_model': 'project.task',
            'res_id': self.parent_id.id,
            'type': 'ir.actions.act_window',
            'context': dict(self._context, create=False)
        }

    def action_subtask(self):
        action = self.env["ir.actions.actions"]._for_xml_id("project.project_task_action_sub_task")

        # display all subtasks of current task
        action['domain'] = [('id', 'child_of', self.id), ('id', '!=', self.id)]

        # update context, with all default values as 'quick_create' does not contains all field in its view
        if self._context.get('default_project_id'):
            default_project = self.env['project.project'].browse(self.env.context['default_project_id'])
        else:
            default_project = self.project_id.subtask_project_id or self.project_id
        ctx = dict(self.env.context)
        ctx.update({
            'default_name': self.env.context.get('name', self.name) + ':',
            'default_parent_id': self.id,  # will give default subtask field in `default_get`
            'default_company_id': default_project.company_id.id if default_project else self.env.company.id,
        })

        action['context'] = ctx

        return action

    def action_recurring_tasks(self):
        return {
            'name': 'Tasks in Recurrence',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'view_mode': 'tree,form',
            'domain': [('recurrence_id', 'in', self.recurrence_id.ids)],
        }

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

    def rating_apply(self, rate, token=None, feedback=None, subtype_xmlid=None):
        return super(Task, self).rating_apply(rate, token=token, feedback=feedback, subtype_xmlid="project.mt_task_rating")

    def _rating_get_parent_field_name(self):
        return 'project_id'


class ProjectTags(models.Model):
    """ Tags of project's tasks """
    _name = "project.tags"
    _description = "Project Tags"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Name', required=True)
    color = fields.Integer(string='Color', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]
