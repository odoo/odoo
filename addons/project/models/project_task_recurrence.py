# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class ProjectTaskRecurrence(models.Model):
    _name = 'project.task.recurrence'
    _recurrent_model = 'project.task'
    _inherit = 'recurrence.mixin'
    _description = 'Task Recurrence'

    recurrence_left = fields.Integer(string="Number of Tasks Left to Create", copy=False)
    recurrent_template_id = fields.Many2one(_recurrent_model)
    recurrent_ids = fields.One2many(_recurrent_model, 'recurrence_id')

    @api.model
    def _get_recurrent_fields_to_copy(self):
        return super()._get_recurrent_fields_to_copy() + [
            'message_partner_ids',
            'company_id',
            'description',
            'displayed_image_id',
            'email_cc',
            'parent_id',
            'partner_email',
            'partner_id',
            'partner_phone',
            'planned_hours',
            'project_id',
            'display_project_id',
            'project_privacy_visibility',
            'sequence',
            'tag_ids',
            'name',
            'analytic_account_id',
            'user_ids'
        ]

    @api.model
    def _get_recurrent_fields_to_postpone(self):
        return super()._get_recurrent_fields_to_postpone() + ['date_deadline']

    def _create_occurence_values(self, occurence_from, to_template=False):
        create_values = super()._create_occurence_values(occurence_from, to_template=to_template)
        create_values['active'] = not to_template
        return create_values


    def _create_subtasks(self, task_from, task_to, depth=3, to_template=False):
        self.ensure_one()
        if not depth or not task_from.with_context(active_test=False).child_ids:
            return
        children = []
        # copy the subtasks of the original task
        for child_from in task_from.with_context(active_test=False).child_ids:
            child_values = self._new_task_values(child_from, to_template=to_template)
            child_values['parent_id'] = task_to.id
            if child_from.with_context(active_test=False).child_ids and depth > 1:
                # If child has childs in the following layer and we will have to copy layer, we have to
                # first create the child_to record in order to have a new parent_id reference for the
                # "grandchildren" tasks
                child_to = self.env['project.task'].sudo().create(child_values)
                self._create_subtasks(child_from, child_to, depth=depth - 1, to_template=to_template)
            else:
                children.append(child_values)
        self.env['project.task'].sudo().create(children)

    def _create_occurence(self, occurence_from=False):
        self.ensure_one()
        to_template = bool(occurence_from)
        occurence_from = occurence_from or self.recurrent_template_id
        create_values = self._create_occurence_values(occurence_from, to_template=to_template)
        task_to = self.env['project.task'].sudo().create(create_values)
        self._create_subtasks(occurence_from, task_to, to_template=to_template)
        if to_template:
            self.recurrent_template_id.unlink_task_and_subtasks_recursively()
            self.recurrent_template_id = task_to

    @api.model
    def _cron_create_occurences(self):
        if not self.env.user.has_group('project.group_project_recurring_tasks'):
            return
        today = fields.Date.today()
        recurring_today = self.search([('next_recurrence_date', '<=', today)])
        for recurrence in recurring_today:
            recurrence._create_occurence()
            if recurrence.repeat_type == 'number':
                recurrence.recurrence_left -= 1
        recurring_today._set_next_occurrence_date()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('repeat_number'):
                vals['recurrence_left'] = vals.get('repeat_number')
        recurrences = super().create(vals_list)
        recurrences._set_next_occurrence_date()
        return recurrences

    def write(self, vals):
        if vals.get('repeat_number'):
            vals['recurrence_left'] = vals.get('repeat_number')

        res = super(ProjectTaskRecurrence, self).write(vals)

        if 'next_occurrence_date' not in vals:
            self._set_next_occurrence_date()
        return res

    def unlink(self):
        self.recurrent_template_id.unlink_task_and_subtasks_recursively()
        return super().unlink()

