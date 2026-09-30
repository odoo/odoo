# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class MailActivityTodoCreate(models.TransientModel):
    _name = 'mail.activity.todo.create'
    _description = 'Create activity and todo at the same time'

    summary = fields.Char()
    date_deadline = fields.Date('Due Date', index=True, required=True, default=fields.Date.context_today)
    user_id = fields.Many2one('res.users', 'Assigned to', default=lambda self: self.env.user, required=True, readonly=True)
    note = fields.Html(sanitize_style=True)

    def create_todo_activity(self):
        todo = self.env['project.task'].create({
            'name': self.summary,
            'description': self.note,
            'date_deadline': self.date_deadline,
            'user_ids': self.user_id.ids,
        })
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get('project.task').id,
            'res_id': todo.id,
            'summary': self.summary,
            'user_id': self.user_id.id,
            'date_deadline': self.date_deadline,
            'activity_type_id': self.env['mail.activity']._default_activity_type_for_model('project.task').id,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Your to-do has been successfully added to your pipeline."),
            },
        }
