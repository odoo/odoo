# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectTaskType(models.Model):
    _name = 'project.task.type'
    _description = 'Task Stage'
    _order = 'sequence, id'

    def _get_default_project_ids(self):
        default_project_id = self.env.context.get('default_project_id')
        return [default_project_id] if default_project_id else None

    def _default_user_id(self):
        return not self.env.context.get('default_project_id', False) and self.env.uid

    active = fields.Boolean('Active', default=True, export_string_translation=False)
    name = fields.Char(string='Name', required=True, translate=True)
    sequence = fields.Integer(default=1)
    project_ids = fields.Many2many('project.project', 'project_task_type_rel', 'type_id', 'project_id', string='Projects',
        default=lambda self: self._get_default_project_ids(),
        help="Projects in which this stage is present. If you follow a similar workflow in several projects,"
            " you can share this stage among them and get consolidated information this way.")
    mail_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain=[('model', '=', 'project.task')],
        help="If set, an email will be automatically sent to the customer when the task reaches this stage.")
    color = fields.Integer(string='Color', export_string_translation=False)
    fold = fields.Boolean(string='Folded')
    rating_template_id = fields.Many2one(
        'mail.template',
        string='Rating Email Template',
        domain=[('model', '=', 'project.task')],
        help="If set, a rating request will automatically be sent by email to the customer when the task reaches this stage. \n"
             "Alternatively, it will be sent at a regular interval as long as the task remains in this stage.")
    auto_validation_state = fields.Boolean('Automatic Kanban Status', default=False,
        help="Automatically modify the state when the customer replies to the feedback for this stage.\n"
            " * Good feedback from the customer will update the state to 'Approved' (green bullet).\n"
            " * Neutral or bad feedback will set the kanban state to 'Changes Requested' (orange bullet).\n")
    rotting_threshold_days = fields.Integer('Days to rot', default=0, help='Day count before tasks in this stage become stale. Set to 0 to disable \
        Changing this parameter will not affect the rotting status/date of resources last updated before this change.')

    user_id = fields.Many2one('res.users', 'Stage Owner', default=_default_user_id, compute='_compute_user_id', store=True, index=True)

    # rating fields
    rating_request_deadline = fields.Datetime(compute='_compute_rating_request_deadline', store=True, export_string_translation=False)
    rating_active = fields.Boolean('Send a customer rating request')
    rating_status = fields.Selection(
        string='Customer Ratings Status',
        selection=[
            ('stage', 'when reaching this stage'),
            ('periodic', 'on a periodic basis'),
        ],
        default='stage',
        required=True,
        help="Collect feedback from your customers by sending them a rating request when a task enters a certain stage. To do so, define a rating email template on the stage.\n"
             "Rating when changing stage: an email will be automatically sent when a task reaches the stage.\n"
             "Periodic rating: an email will be automatically sent at regular intervals as long as the task remains in the stage.",
    )
    rating_status_period = fields.Selection(
        string='Rating Frequency',
        selection=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('bimonthly', 'Twice a Month'),
            ('monthly', 'Once a Month'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
        ],
        default='monthly',
        required=True,
    )

    @api.depends('rating_status', 'rating_status_period')
    def _compute_rating_request_deadline(self):
        periods = {'daily': 1, 'weekly': 7, 'bimonthly': 15, 'monthly': 30, 'quarterly': 90, 'yearly': 365}
        for stage in self:
            stage.rating_request_deadline = fields.Datetime.now() + timedelta(days=periods.get(stage.rating_status_period, 0))

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
        # Hide/Show task rating template when customer rating feature is disabled/enabled
        if 'rating_active' in vals:
            rating_active = vals['rating_active']
            task_types = self.env['project.task.type'].search([('rating_active', '=', True)])
            if (not task_types and rating_active) or (task_types and task_types <= self and not rating_active):
                mt_project_task_rating = self.env.ref('project.mt_project_task_rating')
                mt_project_task_rating.hidden = not rating_active
                mt_project_task_rating.default = rating_active
                self.env.ref('project.mt_task_rating').hidden = not rating_active
                self.env.ref('project.rating_project_request_email_template').active = rating_active
        return super().write(vals)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", task_type.name)) for task_type, vals in zip(self, vals_list)]

    @api.ondelete(at_uninstall=False)
    def _unlink_if_remaining_personal_stages(self):
        """ Prepare personal stages for deletion (i.e. move task to other personal stages) and
            avoid unlink if no remaining personal stages for an active internal user.
        """
        # Personal stages are processed if the user still has at least one personal stage after unlink
        personal_stages = self.filtered('user_id')
        if not personal_stages:
            return
        remaining_personal_stages_all = self.env['project.task.type']._read_group(
            [('user_id', 'in', personal_stages.user_id.ids), ('id', 'not in', personal_stages.ids)],
            groupby=['user_id', 'sequence', 'id'],
            order="user_id,sequence DESC",
        )
        remaining_personal_stages_by_user = defaultdict(list)
        for user, sequence, stage in remaining_personal_stages_all:
            remaining_personal_stages_by_user[user].append({'id': stage.id, 'seq': sequence})

        # For performance issue, project.task.stage.personal records that need to be modified are listed before calling _prepare_personal_stages_deletion
        personal_stages_to_update = self.env['project.task.stage.personal']._read_group([('stage_id', 'in', personal_stages.ids)], ['stage_id'], ['id:recordset'])
        for user in personal_stages.user_id:
            if not user.active or user.share:
                continue
            user_stages_to_unlink = personal_stages.filtered(lambda stage: stage.user_id == user)
            user_remaining_stages = remaining_personal_stages_by_user[user]
            if not user_remaining_stages:
                raise UserError(_("Each user should have at least one personal stage. Create a new stage to which the tasks can be transferred after the selected ones are deleted."))
            user_stages_to_unlink._prepare_personal_stages_deletion(user_remaining_stages, personal_stages_to_update)

    def _prepare_personal_stages_deletion(self, remaining_stages_dict, personal_stages_to_update):
        """ _prepare_personal_stages_deletion prepare the deletion of personal stages of a single user.
            Tasks using that stage will be moved to the first stage with a lower sequence if it exists
            higher if not.
        :param self: project.task.type recordset containing the personal stage of a user
                     that need to be deleted
        :param remaining_stages_dict: list of dict representation of the personal stages of a user that
                                      can be used to replace the deleted ones. Can not be empty.
                                      e.g: [{'id': stage1_id, 'seq': stage1_sequence}, ...]
        :param personal_stages_to_update: project.task.stage.personal recordset containing the records
                                          that need to be updated after stage modification. Is passed to
                                          this method as an argument to avoid to reload it for each users
                                          when this method is called multiple times.
        """
        stages_to_delete_dict = sorted([{'id': stage.id, 'seq': stage.sequence} for stage in self],
                                       key=lambda stage: stage['seq'])
        replacement_stage_id = remaining_stages_dict.pop()['id']
        next_replacement_stage = remaining_stages_dict and remaining_stages_dict.pop()

        personal_stages_by_stage = {
            stage.id: personal_stages
            for stage, personal_stages in personal_stages_to_update
        }
        for stage in stages_to_delete_dict:
            while next_replacement_stage and next_replacement_stage['seq'] < stage['seq']:
                replacement_stage_id = next_replacement_stage['id']
                next_replacement_stage = remaining_stages_dict and remaining_stages_dict.pop()
            if stage['id'] in personal_stages_by_stage:
                personal_stages_by_stage[stage['id']].stage_id = replacement_stage_id

    def action_unarchive(self):
        res = super().action_unarchive()
        stage_active = self.filtered(self._active_name)
        if stage_active and self.env['project.task'].with_context(active_test=False).search_count(
            [('active', '=', False), ('stage_id', 'in', stage_active.ids)], limit=1
        ):
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

    @api.depends('project_ids')
    def _compute_user_id(self):
        """ Fields project_ids and user_id cannot be set together for a stage. It can happen that
            project_ids is set after stage creation (e.g. when setting demo data). In such case, the
            default user_id has to be removed.
        """
        self.sudo().filtered('project_ids').user_id = False

    @api.constrains('user_id', 'project_ids')
    def _check_personal_stage_not_linked_to_projects(self):
        if any(stage.user_id and stage.project_ids for stage in self):
            raise UserError(_('A personal stage cannot be linked to a project because it is only visible to its corresponding user.'))

    # ---------------------------------------------------
    # Rating business
    # ---------------------------------------------------

    # This method should be called once a day by the scheduler
    @api.model
    def _send_rating_all(self):
        stages = self.search([
            ('rating_active', '=', True),
            ('rating_status', '=', 'periodic'),
            ('rating_request_deadline', '<=', fields.Datetime.now())
        ])
        for stage in stages:
            stage.project_ids.task_ids._send_task_rating_mail()
            stage._compute_rating_request_deadline()
            self.env.cr.commit()
