# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import api, fields, models, _
from odoo.tools import html2plaintext
from odoo.exceptions import ValidationError


class Stage(models.Model):

    _name = "project.task.type"
    _description = "Task Stage"
    _order = 'sequence'

    def _get_default_user_id(self):
        todo_stage = self.env.context.get('default_todo_stage', False)
        if todo_stage:
            return self.env.uid

    name = fields.Char('Stage Name', translate=True, required=True)
    sequence = fields.Integer(default=1)
    user_id = fields.Many2one('res.users', string='Stage Owner', index=True, ondelete='cascade', default=_get_default_user_id) #TODO: default should only be set if no project_id assigned to the task
    fold = fields.Boolean(string='Folded in Kanban',
        help='If enabled, this stage will be displayed as folded in the Kanban view of your tasks. Tasks in a folded stage are considered as closed.')
    todo_stage = fields.Boolean(default=False, help='If enabled, this stage will be used to manage display of tasks in the To-Do app.')

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

    def remove_personal_stage(self): # NOTE: could it be merged with the unlink method ? (why separate method to deal with personal stage and other stage ?? # TODO: Import ValidationError # Why is it really needed ? task with no stage should be assigned one in the compute method of personal_stage
        """
        Remove a personal stage, tasks using that stage will move to the first
        stage with a lower priority if it exists higher if not.
        This method will not allow to delete the last personal stage.
        Having no personal_stage_type_id makes the task not appear when grouping by personal stage.
        """
        self.ensure_one()
        assert self.user_id == self.env.user or self.env.su

        users_personal_stages = self.env['project.task.type']\
            .search([('user_id', '=', self.user_id.id), ('todo_stage', '=', self.todo_stage)], order='sequence DESC')
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
        })#Search on a computed field ?? Easier to do the search on the M2M (ids) with a 'in' ?
        self.unlink()


class Tag(models.Model): # TODO- address functional security questions related to tags (see notes in odoo)

    _name = "project.tags"
    _description = "Task Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color', default=_get_default_color, #Move default_color here or adapt logic for note ??
        help="Transparent tags are not visible in kanban views.")#NOTE: to update
    todo_tag = fields.Boolean(default=False, help='If enabled, this tag will be used to add information to a note in the To-Do app.')
    task_ids = fields.Many2many('project.task', string='Tasks')

    _sql_constraints = [ #TO UPDATE (can be duplicated if todo_tags is different
        ('name_uniq', 'unique (name, todo_tag)', "A tag with the same name already exists."),
    ]

class Task(models.Model):

    # ---------------------------------------- Private Attributes ---------------------------------

    _name = 'project.task'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']
    _description = "Task"
    _order = 'sequence, id desc'

    # ---------------------------------------- Default Methods ------------------------------------

    @api.model
    def _default_personal_stage_type_id(self):
        todo_display = self.env.context.get('default_is_todo', False)
        return self.env['project.task.type'].search([('user_id', '=', self.env.user.id), ('todo_stage', '=', todo_display)], limit=1)



    # --------------------------------------- Fields Declaration ----------------------------------

    name = fields.Char(string='Title', tracking=True, required=True, index='trigram')
    company_id = fields.Many2one('res.company') #TODO: to update (see project)
    user_id = fields.Many2one('res.users', string='Owner', default=lambda self: self.env.uid)
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
        help="You can only see tags that are already present in your project. If you try creating a tag that is already existing in other projects, it won't generate any duplicates.") #UPDATE STRING ??

    # modifying property of ``mail.thread`` field
    message_partner_ids = fields.Many2many(compute_sudo=True)

    is_todo = fields.Boolean(default=False, required=True)

    # ---------------------------------------- Compute methods ------------------------------------
    @api.depends_context('uid')
    def _compute_personal_stage_type_id(self):
        default_user_stage = self.env['project.task.type'].search([('user_id', '=', self.env.uid), ('todo_stage', '=', True)], limit=1)
        # Only computing personal stage for followers or note owner
        for task in self.filtered(lambda t: t.user_id.id == self.env.uid or self.env.user.partner_id in t.message_partner_ids):
            for personal_stage in task.personal_stage_type_ids.filtered(lambda stage: stage.user_id == self.env.user and stage.todo_stage):
                task.personal_stage_type_id = personal_stage
                break
            if not task.personal_stage_type_id:
                task.personal_stage_type_id = default_user_stage

    def _inverse_personal_stage_type_id(self): #TODO: override in project
        for task in self.filtered('personal_stage_type_id'):
            task.personal_stage_type_ids = task.personal_stage_type_id + task.personal_stage_type_ids.filtered(lambda stage: stage.user_id != self.env.user or stage.todo_stage != task.is_todo)


    # ----------------------------------- Constrains and Onchanges --------------------------------

    # ------------------------------------------ CRUD Methods -------------------------------------

    # def write(self, vals): # !!!!!!!!!   WARNING: A part of the write/CREATE method should probably be moved here (see below) !!!!!!!!!!!!
    #     #breakpoint()
    #     #if "personal_stage_type_id" in vals and not vals['personal_stage_type_id']:
    #     #    del vals['personal_stage_type_id']

    #     result = super(Task, self).write(vals)

    #     #if 'user_ids' in vals:
    #     #    tasks._populate_missing_personal_stages()

    #     if 'message_partner_ids' in vals:
    #         breakpoint()

    #     #message_partner_ids', '=', user.partner_id.id
    #     return result


    # ---------------------------------------- Action Methods -------------------------------------

    # ----------------------------------------- Other Methods -------------------------------------

    @api.model
    def _read_group_personal_stage_type_ids(self, stages, domain, order):
        todo_display = self.env.context.get('default_is_todo', False)
        return stages.search(['|', ('id', 'in', stages.ids), ('user_id', '=', self.env.user.id), ('todo_stage', '=', todo_display)])

    def _get_todo_default_personal_stage_create_vals(self, user_id):
        return [
            {'sequence': 1, 'name': _('New'), 'user_id': user_id, 'fold': False, 'todo_stage': True},
            {'sequence': 2, 'name': _('Meeting Minutes'), 'user_id': user_id, 'fold': False, 'todo_stage': True},
            {'sequence': 3, 'name': _('Notes'), 'user_id': user_id, 'fold': False, 'todo_stage': True},
            {'sequence': 4, 'name': _('Todo'), 'user_id': user_id, 'fold': False, 'todo_stage': True},
        ]

    def _ensure_todo_personal_stages(self):
        user = self.env.user
        ProjectTaskTypeSudo = self.env['project.task.type'].sudo()
        # In the case no stages have been found, we create the default stages for the user
        if not ProjectTaskTypeSudo.search_count([('user_id', '=', user.id), ('todo_stage', '=', True)], limit=1):
            ProjectTaskTypeSudo.with_context(lang=user.lang, default_project_id=False).create(
                self.with_context(lang=user.lang)._get_todo_default_personal_stage_create_vals(user.id)
            )

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        # Missing personal stages are attributed at reading by the affected user and not at writing anymore (which can be lengthy if a lot of followers/assignees are added) --> Like an inbox
        # Change in behavior: if an assignee is removed from a task and then assigned to it again, it goes back in the original personal stage --> TODO: move to the commit message
        if groupby and groupby[0] == "personal_stage_type_ids" and (len(groupby) == 1 or lazy): #To update personal...ids # TODO: populates personal stages if it does not exist for the user
            self._ensure_todo_personal_stages()
            todo_display = self.env.context.get('default_is_todo', False)
            stages = self.env['project.task.type'].search([('user_id', '=', self.env.uid), ('todo_stage', '=', todo_display)])
            # task without user's personal stage
            nb_tasks_ws = self.env['project.task'].search(domain + [('personal_stage_type_ids', 'not in', stages.ids)])
            if nb_tasks_ws:
                for task in nb_tasks_ws:
                    task.sudo().personal_stage_type_ids |= stages[0]
        return super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

# TO DO: SQL check that todo tasks are only related to todo stages (and inversly)
# TODO : add a word about security of every models in the commit message
