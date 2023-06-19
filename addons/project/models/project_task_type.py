# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProjectTaskType(models.Model):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence, id'

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    def _default_user_id(self):
        return 'default_project_id' not in self.env.context and self.env.uid
    
    active = fields.Boolean('Active', default=True)
    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=1)
    project_ids = fields.Many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', string='Projects',
        default=_get_default_project_ids,
        help="Projects in which this stage is present. If you follow a similar workflow in several projects,"
            " you can share this stage among them and get consolidated information this way.")
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'project.task')],
        help="If set, an email will be automatically sent to the customer when the task reaches this stage.")
    fold = fields.Boolean(string='Folded in Kanban')
    rating_template_id = fields.Many2one(
        'mail.template',
        string='Rating Email Template',
        domain=[('model', '=', 'project.task')],
        help="If set, a rating request will automatically be sent by email to the customer when the task reaches this stage. \n"
             "Alternatively, it will be sent at a regular interval as long as the task remains in this stage, depending on the configuration of your project. \n"
             "To use this feature make sure that the 'Customer Ratings' option is enabled on your project.")
    auto_validation_state = fields.Boolean('Automatic Kanban Status', default=False,
        help="Automatically modify the state when the customer replies to the feedback for this stage.\n"
            " * Good feedback from the customer will update the state to 'Approved' (green bullet).\n"
            " * Neutral or bad feedback will set the kanban state to 'Changes Requested' (orange bullet).\n")
    disabled_rating_warning = fields.Text(compute='_compute_disabled_rating_warning')

    user_id = fields.Many2one('res.users', 'Stage Owner', default=_default_user_id, compute='_compute_user_id', store=True, index=True)

    def unlink_wizard(self, stage_view=False):
        self = self.with_context(active_test=False)
        # retrieves all the projects with a least 1 task in that stage
        # a task can be in a stage even if the project is not assigned to the stage
        readgroup = self.with_context(active_test=False).env['project.task']._read_group([('stage_id', 'in', self.ids)], ['project_id'])
        project_ids = list(set([project.id for [project] in readgroup] + self.project_ids.ids))

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

    def copy(self, default=None):
        default = dict(default or {})
        if not default.get('name'):
            default['name'] = _("%s (copy)") % (self.name)
        return super().copy(default)

    def unlink(self): # TODO: write test for deleting stages in batch (+ for multiple user in sudo)
        # 1. All non-personal stages are processed
        stages_to_unlink = self.filtered(lambda stage: not stage.user_id)

        # 2. Personal stages are processed if the user still has at least one personal stage after unlink
        raise_personal_stage_error = False
        remaining_personal_stages = self.env['project.task.type'].search([('user_id', 'in', self.user_id.ids), ('id', 'not in', self.ids)], order='sequence DESC')
        for user in self.user_id:
            user_stages_to_unlink = self.filtered(lambda stage: stage.user_id == user)
            user_remaining_stages = remaining_personal_stages.filtered(lambda stage: stage.user_id == user)
            if len(user_remaining_stages):
                stages_to_unlink |= user_stages_to_unlink
                self._prepare_personal_stages_deletion(user_stages_to_unlink, user_remaining_stages)
            else:
                raise_personal_stage_error = True

        result =  super(ProjectTaskType, stages_to_unlink).unlink()
        if raise_personal_stage_error:
            raise ValidationError(_("Each user should at least have one personal stage. Create a new stage to which the tasks can be transferred after the selected one(s) is deleted."))
        return result

    def _prepare_personal_stages_deletion(self, stages_to_delete, remaining_stages):
        """
        _prepare_personal_stages_deletion prepare the deletion of personal stages of a single user.
        Tasks using that stage will be moved to the first stage with a lower priority if it exists
        higher if not. remaining_stages recordset can not be empty.
        """
        remaining_stages_dict = [{'id': stage.id, 'seq': stage.sequence, 'to_delete': False} for stage in remaining_stages]
        stage_mapping = {}
        stages_to_delete_dict = sorted([{'id': stage.id, 'seq': stage.sequence, 'to_delete': False} for stage in stages_to_delete],
                                       key=lambda stage: stage['seq'])
        replacement_stage_id = remaining_stages_dict.pop()['id']
        next_replacement_stage = remaining_stages_dict.pop() if len(remaining_stages_dict) else False

        for stage in stages_to_delete_dict:
            while next_replacement_stage and next_replacement_stage['seq'] < stage['seq']:
                replacement_stage_id = next_replacement_stage['id']
                next_replacement_stage = remaining_stages_dict.pop() if len(remaining_stages_dict) else False
            self.env['project.task'].with_context({'active_test': False}).search([('personal_stage_type_ids', 'in', [stage['id']])]).personal_stage_type_id = replacement_stage_id #with_user needed ????

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

    @api.depends('project_ids', 'project_ids.rating_active')
    def _compute_disabled_rating_warning(self):
        for stage in self:
            disabled_projects = stage.project_ids.filtered(lambda p: not p.rating_active)
            if disabled_projects:
                stage.disabled_rating_warning = '\n'.join('- %s' % p.name for p in disabled_projects)
            else:
                stage.disabled_rating_warning = False

    @api.depends('project_ids')
    def _compute_user_id(self):
        # If project_ids is set after stage creation (e.g. when setting demo data), the default user_id has to be removed
        for stage in self.sudo():
            if stage.project_ids:
                stage.user_id = False

    @api.constrains('user_id', 'project_ids')
    def _check_personal_stage_not_linked_to_projects(self):
        if any(stage.user_id and stage.project_ids for stage in self):
            raise UserError(_('A personal stage cannot be linked to a project because it is only visible to its corresponding user.'))
