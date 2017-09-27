# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProjectTaskMergeWizard(models.TransientModel):
    _name = 'project.task.merge.wizard'

    task_ids = fields.Many2many('project.task', string="Tasks to Merge", required=True)
    user_id = fields.Many2one('res.users', string="Assigned to")
    create_new_task = fields.Boolean('Create a new task')
    target_task_name = fields.Char('New task name')
    target_project_id = fields.Many2one('project.project', string="Target Project")
    target_task_id = fields.Many2one('project.task', string="Merge into an existing task")

    @api.multi
    def merge_tasks(self):
        values = {
            'user_id': self.user_id.id,
            'description': self.merge_description(),
        }
        if self.create_new_task:
            values.update({
                'name': self.target_task_name,
                'project_id': self.target_project_id.id
            })
            self.target_task_id = self.env['project.task'].create(values)
        else:
            self.target_task_id.write(values)
        self.merge_followers()
        self.target_task_id.message_post_with_view(
            self.env.ref('project.mail_template_task_merge'),
            values={'target': True, 'tasks': self.task_ids - self.target_task_id},
            subtype_id=self.env.ref('mail.mt_comment').id
        )
        (self.task_ids - self.target_task_id).message_post_with_view(
            self.env.ref('project.mail_template_task_merge'),
            values={'target': False, 'task': self.target_task_id},
            subtype_id=self.env.ref('mail.mt_comment').id
        )
        (self.task_ids - self.target_task_id).write({'active': False})
        return {
            "type": "ir.actions.act_window",
            "res_model": "project.task",
            "views": [[False, "form"]],
            "res_id": self.target_task_id.id,
        }

    @api.multi
    def merge_description(self):
        return '<br/>'.join(self.task_ids.mapped(lambda task: "Description from task <b>%s</b>:<br/>%s" % (task.name, task.description or 'No description')))

    @api.multi
    def merge_followers(self):
        self.target_task_id.message_subscribe(
            partner_ids=(self.task_ids - self.target_task_id).mapped('message_partner_ids').ids,
            channel_ids=(self.task_ids - self.target_task_id).mapped('message_channel_ids').ids,
        )

    @api.model
    def default_get(self, fields):
        result = super(ProjectTaskMergeWizard, self).default_get(fields)
        selected_tasks = self.env['project.task'].browse(self.env.context.get('active_ids', False))
        assigned_tasks = selected_tasks.filtered(lambda task: task.user_id)
        result.update({
            'task_ids': selected_tasks.ids,
            'user_id': assigned_tasks and assigned_tasks[0].user_id.id or False,
            'target_project_id': selected_tasks[0].project_id.id,
            'target_task_id': selected_tasks[0].id
        })
        return result
