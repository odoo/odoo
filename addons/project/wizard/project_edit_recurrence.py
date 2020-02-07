# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ProjectTaskEditRecurrence(models.TransientModel):
    _name = 'project.task.edit.recurrence'
    _description = "Edit task recurrence"

    """
        If the user:
            1) deletes a task
            2) archives a task
            3) edits a field kept when copying a task
            4) edits the recurrency parameters
            5) switches 'recurring task' to false
        Raise a modal so that the user can select whether to delete/archive/modify:
        this task (except for scenario 4)
        this and the following tasks
        all tasks
        For scenario 5, archive the selected tasks
    """

    def _get_editing_style_selection_fields(self):
        if self._context.get('editing_type', False) == 'edit_recurrence_settings':
            return [
                ('all', 'All Tasks'),
                ('future', 'Current and following tasks')
            ]
        if self._context.get('editing_type', False) == 'edit_recurrence':
            return [
                ('all', 'All Tasks')
            ]
        return [
            ('current', 'Current Task'),
            ('all', 'All Tasks'),
            ('future', 'Current and following tasks')
        ]


    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        result['task_id'] = self._context.get('task_id', False)
        result['editing_type'] = self._context.get('editing_type', False)
        if result['editing_type'] == 'edit_recurrence_settings':
            result['editing_style'] = 'future'
        elif result['editing_type'] == 'edit_recurrence':
            result['editing_style'] = 'all'
        else:
            result['editing_style'] = 'current'
        return result

    task_id = fields.Many2one("project.task")
    editing_type = fields.Selection([
        ('unlink', 'Delete'),
        ('archive', 'Archive'),
        ('edit', 'Edit'),
        ('edit_recurrence_settings', 'Edit the recurrence settings')
    ])
    editing_style = fields.Selection(selection=lambda self: self._get_editing_style_selection_fields())

    def action_edit_recurrence(self):
        if self.editing_type == 'unlink':
            if self.editing_style == 'all':
                self.env['project.task'].browse(self.task_id._get_all_tasks_from_this_recurrence()).with_context(force_delete=True).unlink()
            elif self.editing_style == 'future':
                self.env['project.task'].browse(self.task_id._get_all_following_tasks_from_this_recurrence()).with_context(force_delete=True).unlink()
            else:
                self.task_id.with_context(force_delete=True).unlink()
            context = self.env.context.copy()
            del context['task_id']
            del context['editing_type']
            action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]
            action.update({
                'context': context,
                'target': 'main'
            })
            return action
        elif self.editing_type == 'archive':
            active = self.task_id.active
            print(active)
            if self.editing_style == 'all':
                self.env['project.task'].browse(self.task_id._get_all_tasks_from_this_recurrence()).with_context(archive=True).write({'active': not active})
            elif self.editing_style == 'future':
                self.env['project.task'].browse(self.task_id._get_all_following_tasks_from_this_recurrence()).with_context(archive=True).write({'active': not active})
            else:
                self.task_id.with_context(archive=True).write({'active': not active})
            context = self.env.context.copy()
            del context['task_id']
            del context['editing_type']
            action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]
            action.update({
                'context': context,
                'target': 'main'
            })
            return action
        elif self.editing_type == 'edit':
            if self.editing_style == 'all':
                self.env['project.task'].browse(self.task_id._get_all_tasks_from_this_recurrence()).with_context(edit=True).write(self.env.context.get('modified_values'))
            elif self.editing_style == 'future':
                self.env['project.task'].browse(self.task_id._get_all_following_tasks_from_this_recurrence()).with_context(edit=True).write(self.env.context.get('modified_values'))
            else:
                self.task_id.with_context(edit=True).write(self.env.context.get('modified_values'))
            context = self.env.context.copy()
            del context['task_id']
            del context['editing_type']
            del context['modified_values']
            action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]
            action.update({
                'context': context,
                'target': 'main'
            })
            return action
        elif self.editing_type == 'edit_recurrence_settings':
            if self.editing_style == 'all':
                self.env['project.task'].browse(self.task_id._get_all_tasks_from_this_recurrence()).with_context(edit=True).write(self.env.context.get('modified_values'))
            elif self.editing_style == 'future':
                self.env['project.task'].browse(self.task_id._get_all_following_tasks_from_this_recurrence()).with_context(edit=True).write(self.env.context.get('modified_values'))
            # else:
            #     self.task_id.with_context(edit=True).write(self.env.context.get('values'))
            context = self.env.context.copy()
            del context['task_id']
            del context['editing_type']
            del context['modified_values']
            action = self.env.ref('project.act_project_project_2_project_task_all').read()[0]
            action.update({
                'context': context,
                'target': 'main'
            })
            return action
        else:
            raise UserError(_('Please choose one of the options'))
