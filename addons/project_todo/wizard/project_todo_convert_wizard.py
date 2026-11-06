from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class ProjectTodoConvertWizard(models.TransientModel):
    _name = 'project.todo.convert.wizard'
    _description = 'Convert To-Do to Task'

    task_id = fields.Many2one('project.task', string='To-Do', required=True)
    company_id = fields.Many2one('res.company')
    project_id = fields.Many2one('project.project', string='Project', required=True,
        domain="[('is_template', '=', False), '|', ('company_id', '=', False), ('company_id', '=?', company_id)]")
    project_sharing_portal_user_ids = fields.Many2many(
        'res.users',
        string='Assignable Portal Users',
        compute='_compute_project_sharing_portal_user_ids',
    )
    user_ids = fields.Many2many('res.users', string='Assignees',
        domain=lambda self: f"""[
            '|',
                '&',
                    ('share', '=', False),
                    ('all_group_ids', 'in', [{self.env.ref('project.group_project_user').id}]),
                ('id', 'in', project_sharing_portal_user_ids),
            ('active', '=', True),
            '|',
                ('company_id', '=?', company_id),
                ('company_ids', 'in', company_id),
        ]""",
    )
    tag_ids = fields.Many2many('project.tags', string='Tags')

    @api.model
    def default_get(self, fields):
        values = super().default_get(fields)
        task_id = values.get('task_id') or self.env.context.get('default_task_id')
        if not task_id and self.env.context.get('active_model') == 'project.task':
            task_id = self.env.context.get('active_id')

        if not task_id:
            return values

        task = self.env['project.task'].browse(task_id).exists()
        if not task:
            return values

        users = self._filter_assignees(
            task.user_ids,
            task.company_id.id,
            [],
        )
        defaults = {
            'task_id': task.id,
            'company_id': task.company_id.id,
            'user_ids': [Command.set(users.ids)],
            'tag_ids': [Command.set(task.tag_ids.ids)],
        }
        values.update({
            name: value
            for name, value in defaults.items()
            if name in fields
        })
        return values

    @api.depends(
        'project_id',
        'project_id.collaborator_ids.access_mode',
        'project_id.collaborator_ids.partner_id.user_ids',
        'project_id.collaborator_ids.partner_id.user_ids.share',
    )
    def _compute_project_sharing_portal_user_ids(self):
        for wizard in self:
            collaborators = wizard.project_id.sudo().collaborator_ids.filtered(
                lambda collaborator: collaborator.access_mode in ('edit', 'advanced_edit')
            )
            wizard.project_sharing_portal_user_ids = (
                collaborators.partner_id.user_ids.filtered('share')
            )

    @api.model
    def _filter_assignees(self, users, company_id, portal_user_ids):
        domain = [
            '|',
                '&',
                    ('share', '=', False),
                    ('all_group_ids', 'in', [self.env.ref('project.group_project_user').id]),
                ('id', 'in', portal_user_ids),
            ('active', '=', True),
            '|',
                ('company_id', '=?', company_id),
                ('company_ids', 'in', company_id),
        ]
        return users.filtered_domain(domain)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        if self.project_id:
            self.company_id = self.project_id.company_id
        else:
            self.company_id = self.task_id.company_id

        self.user_ids = self._filter_assignees(
            self.user_ids,
            self.company_id.id,
            self.project_sharing_portal_user_ids.ids,
        )

    def action_convert_to_task(self):
        self.ensure_one()

        task = self.task_id.exists()
        if not task:
            raise UserError(self.env._("The to-do no longer exists."))
        if task.project_id:
            raise UserError(self.env._(
                "This to-do has already been converted into a task."
            ))

        company = self.project_id.company_id
        users = self._filter_assignees(
            self.user_ids,
            company.id,
            self.project_sharing_portal_user_ids.ids,
        )

        task.write({
            'project_id': self.project_id.id,
            'user_ids': [Command.set(users.ids)],
            'tag_ids': [Command.set(self.tag_ids.ids)],
            'company_id': company.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': task.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
