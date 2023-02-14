# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models, Command, _
from odoo.osv import expression
from odoo.tools import html2plaintext
from odoo.addons.web_editor.controllers.main import handle_history_divergence
from odoo.exceptions import ValidationError


class ProjectTaskType(models.Model):

    _name = "project.task.type"
    _description = "Task Stage"
    _order = 'sequence'

    name = fields.Char('Stage Name', translate=True, required=True)
    sequence = fields.Integer(default=1)
    user_id = fields.Many2one('res.users', string='Stage Owner', index=True, ondelete='cascade')
    fold = fields.Boolean(string='Folded in Kanban',
        help='If enabled, this stage will be displayed as folded in the Kanban view of your tasks. Tasks in a folded stage are considered as closed.')

    def copy(self, default=None):
        default = dict(default or {})
        if not default.get('name'):
            default['name'] = _("%s (copy)") % (self.name)
        return super().copy(default)

    def toggle_active(self):
        res = super().toggle_active()
        stage_active = self.filtered('active')
        inactive_tasks = self.env['project.task'].with_context(active_test=False).search(
            [('active', '=', False), ('stage_id', 'in', stage_active.ids)], limit=1)
        if stage_active and inactive_tasks:
            wizard = self.env['project.task.type.delete.wizard'].create({
                'stage_ids': stage_active.ids,
            })
            return {
                'name': _('Unarchive Tasks'),
                'view_mode': 'form',
                'res_model': 'project.task.type.delete.wizard',
                'views': [(self.env.ref('project.view_project_task_type_unarchive_wizard').id, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': wizard.id,
                'target': 'new',
            }
        return res

    def remove_personal_stage(self):
        """
        Remove a personal stage, tasks using that stage will move to the first
        stage with a lower priority if it exists higher if not.
        This method will not allow to delete the last personal stage.
        Having no personal_stage_type_id makes the task not appear when grouping by personal stage.
        """
        self.ensure_one()
        assert self.user_id == self.env.user or self.env.su

        users_personal_stages = self.env['project.task.type']\
            .search([('user_id', '=', self.user_id.id)], order='sequence DESC')
        if len(users_personal_stages) == 1:
            raise ValidationError(_("You should at least have one personal stage. Create a new stage to which the tasks can be transferred after this one is deleted."))

        # Find the most suitable stage, they are already sorted by sequence
        new_stage = self.env['project.task.type']
        for stage in users_personal_stages:
            if stage == self:
                continue
            if stage.sequence > self.sequence:
                new_stage = stage
            elif stage.sequence <= self.sequence:
                new_stage = stage
                break

        self.env['project.task'].search([('personal_stage_type_id', '=', self.id)]).write({
            'personal_stage_type_id': new_stage.id,
        })
        self.unlink()


class Tag(models.Model):

    _name = "project.tags"
    _description = "Task Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color,
                           help="Transparent tags are not visible in kanban views.")
    task_ids = fields.Many2many('project.task', string='Tasks')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "A tag with the same name already exists."),
    ]

    @api.model
    def name_create(self, name):
        existing_tag = self.search([('name', '=ilike', name.strip())], limit=1)
        if existing_tag:
            return existing_tag.name_get()[0]
        return super().name_create(name)


class Task(models.Model):

    # ---------------------------------------- Private Attributes ---------------------------------

    _name = 'project.task'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = "Task"
    _order = 'sequence, id desc'

    # ---------------------------------------- Default Methods ------------------------------------

    @api.model
    def _default_personal_stage_type_id(self):
        default_id = self.env.context.get('default_personal_stage_type_ids')
        if default_id:
            return self.env['project.task.type'].search([('id', '=', default_id[0])])
        return self.env['project.task.type'].search([('user_id', '=', self.env.user.id)], limit=1)

    @api.model
    def _default_company_id(self):
        return self.env.company



    # --------------------------------------- Fields Declaration ----------------------------------

    name = fields.Char(string='Title', tracking=True, required=True, index='trigram')
    company_id = fields.Many2one('res.company', default=_default_company_id)
    description = fields.Html(string='Description')
    sequence = fields.Integer('Sequence', default=10)
    personal_stage_type_ids = fields.Many2many('project.task.type', 'project_task_stage_rel', column1='task_id', column2='stage_id',
        ondelete='restrict', default=_default_personal_stage_type_id, domain="[('user_id', '=', user.id)]", string='Personal Stage', group_expand='_read_group_personal_stage_type_ids')
    personal_stage_type_id = fields.Many2one('project.task.type', string='Personal User Stage',
        compute='_compute_personal_stage_type_id', inverse='_inverse_personal_stage_type_id', store=False,
        search='_search_personal_stage_type_id', default=_default_personal_stage_type_id,
        help="The current user's personal task stage.")
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color Index')
    tag_ids = fields.Many2many('project.tags', string='Tags',
        help="You can only see tags that are already present in your project. If you try creating a tag that is already existing in other projects, it won't generate any duplicates.")
    user_ids = fields.Many2many('res.users', string='Assignees', relation='project_task_user_rel', column1='task_id', column2='user_id',
                                context={'active_test': False}, tracking=True)
    date_assign = fields.Datetime(string='Assigning Date', copy=False, readonly=True,
                                  help="Date on which this task was last assigned (or unassigned). Based on this, you can get statistics on the time it usually takes to assign tasks.")


    # ----------------------------------- Compute and search methods ------------------------------

    @api.depends_context('uid')
    def _compute_personal_stage_type_id(self):
        # Setting personal_stage for task without stage
        default_user_stage = self.env['project.task.type'].search([('user_id', '=', self.env.uid)], limit=1)
        # Only computing personal stage for assignees
        for task in self.filtered(lambda task: self.env.uid in task.user_ids.ids):
            for personal_stage in task.sudo().personal_stage_type_ids.filtered(lambda stage: stage.user_id.id == self.env.uid):
                task.personal_stage_type_id = personal_stage
                break
            if not task.personal_stage_type_id:
                task.personal_stage_type_id = default_user_stage

    def _inverse_personal_stage_type_id(self):
        for task in self.filtered(lambda task: task.personal_stage_type_id):
            if (not task.personal_stage_type_id.user_id or task.personal_stage_type_id.user_id.id != self.env.uid) and self.env.uid != 1:
                # Do not assign personal stage if the user of the stage doesn't match the current user
                continue
            task.personal_stage_type_ids = task.personal_stage_type_id + task.personal_stage_type_ids.filtered(lambda stage: stage.user_id != self.env.user)

    @api.model
    def _search_personal_stage_type_id(self, operator, value):
        return [('personal_stage_type_ids', operator, value)]

    # ----------------------------------- Constrains and Onchanges --------------------------------

    # ------------------------------------------ CRUD Methods -------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Add current user to the assignees for to-do's/private tasks
            if self.env.user.id != 1 and not self.env.context.get('onboarding_todo_creation'): # Do not add OdooBot as assignee
                self._add_default_task_assignees_in_list(vals)
            # user_ids change: update date_assign
            if vals.get('user_ids'):
                vals['date_assign'] = fields.Datetime.now()
        tasks = super(Task, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        self._task_message_auto_subscribe_notify({task: task.user_ids - self.env.user for task in tasks})
        return tasks

    def write(self, vals):
        if len(self) == 1:
            handle_history_divergence(self, 'description', vals)
        # Prevent deletion of personal stage for a to-do/a task
        if "personal_stage_type_id" in vals and not vals['personal_stage_type_id']:
            del vals['personal_stage_type_id']

        if 'user_ids' in vals and 'date_assign' not in vals:
            # prepare update of date_assign after super call
            task_ids_without_user_set = {task.id for task in self if not task.user_ids}

        # Track user_ids to send assignment notifications
        old_user_ids = {t: t.user_ids for t in self}

        result = super().write(vals)

        # user_ids change: update date_assign
        if 'user_ids' in vals:
            for task in self:
                if not task.user_ids and task.date_assign:
                    task.date_assign = False
                elif 'date_assign' not in vals and task.id in task_ids_without_user_set:
                    task.date_assign = fields.Datetime.now()

        self._task_message_auto_subscribe_notify({task: task.user_ids - old_user_ids[task] - self.env.user for task in self})

        return result

    # ---------------------------------------- Action Methods -------------------------------------

    # ----------------------------------------- Other Methods -------------------------------------

    @api.model
    def _read_group_personal_stage_type_ids(self, stages, domain, order):
        return stages.search(['|', ('id', 'in', stages.ids), ('user_id', '=', self.env.user.id)])

    def _add_default_task_assignees_in_list(self, create_vals):
        """ Add the current user to the list of assignees when the task is created.
            Having an isolated method allows to override this behavior in Project.
        """
        user_ids = self._fields['user_ids'].convert_to_cache(create_vals.get('user_ids', []), self)
        if self.env.user.id not in user_ids:
            create_vals['user_ids'] = [Command.set(list(user_ids) + [self.env.user.id])]

    @api.model
    def _get_default_personal_stage_create_vals(self, user_id):
        return [
            {'sequence': 1, 'name': _('Inbox'), 'user_id': user_id, 'fold': False},
            {'sequence': 2, 'name': _('Today'), 'user_id': user_id, 'fold': False},
            {'sequence': 3, 'name': _('This Week'), 'user_id': user_id, 'fold': False},
            {'sequence': 4, 'name': _('This Month'), 'user_id': user_id, 'fold': False},
            {'sequence': 5, 'name': _('Later'), 'user_id': user_id, 'fold': False},
            {'sequence': 6, 'name': _('Done'), 'user_id': user_id, 'fold': True},
            {'sequence': 7, 'name': _('Canceled'), 'user_id': user_id, 'fold': True},
        ]

    def _ensure_personal_stages(self):
        user = self.env.user
        ProjectTaskTypeSudo = self.env['project.task.type'].sudo()
        # In case no personal stages have been found, we create the default stages for the user
        if not ProjectTaskTypeSudo.search_count([('user_id', '=', user.id)], limit=1):
            ProjectTaskTypeSudo.with_context(lang=user.lang).create(
                self.with_context(lang=user.lang)._get_default_personal_stage_create_vals(user.id)
            )

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if groupby and groupby[0] == "personal_stage_type_ids" and (len(groupby) == 1 or lazy):
            self._ensure_personal_stages()
            stages = self.env['project.task.type'].search([('user_id', '=', self.env.uid)])
            # task without user's personal stage
            nb_tasks_ws = self.env['project.task'].search(expression.AND([domain, [('personal_stage_type_ids', 'not in', stages.ids)]]))
            if nb_tasks_ws:
                for task in nb_tasks_ws:
                    task.sudo().personal_stage_type_ids |= stages[0]
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    @api.model
    def _task_message_auto_subscribe_notify(self, users_per_task):
        if self.env.context.get('mail_auto_subscribe_no_notify'):
            return
        # Utility method to send assignation notification upon writing/creation.
        template_id = self.env['ir.model.data']._xmlid_to_res_id('note.todo_message_user_assigned', raise_if_not_found=False)
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
                assignation_msg = self.env['ir.qweb']._render('note.todo_message_user_assigned', values, minimal_qcontext=True)
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
