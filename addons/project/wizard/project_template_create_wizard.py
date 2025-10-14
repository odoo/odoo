from odoo import Command, api, fields, models
from odoo.tools.misc import unquote


class ProjectTemplateCreateWizard(models.TransientModel):
    _name = 'project.template.create.wizard'
    _description = 'Project Template create Wizard'

    def _default_role_to_users_ids(self):
        res = []
        template = self.env['project.project'].browse(self.env.context.get('template_id'))
        if template:
            res = [Command.create({'role_id': role.id}) for role in template.task_ids.role_ids]
        return res

    name = fields.Char(string="Name", required=True)
    date_start = fields.Date(string="Start Date")
    date = fields.Date(string='Expiration Date')
    alias_name = fields.Char(string="Alias Name")
    alias_domain_id = fields.Many2one("mail.alias.domain", string="Alias Domain")
    template_id = fields.Many2one("project.project", default=lambda self: self.env.context.get('template_id'))
    template_has_dates = fields.Boolean(compute="_compute_template_has_dates")
    role_to_users_ids = fields.One2many('project.template.role.to.users.map', 'wizard_id', default=_default_role_to_users_ids)

    @api.depends("template_id")
    def _compute_template_has_dates(self):
        for wizard in self:
            wizard.template_has_dates = wizard.template_id.date_start and wizard.template_id.date

    def _get_template_whitelist_fields(self):
        """
        Whitelist of fields of this wizard that will be used when creating a project from a template.
        """
        return ["name", "date_start", "date", "alias_name", "alias_domain_id"]

    def _create_project_from_template(self):
        # Dictionary with all whitelist fields and their values
        field_values = self._convert_to_write(
            {
                fname: self[fname]
                for fname in self._fields.keys() & self._get_template_whitelist_fields()
            }
        )
        return self.template_id.action_create_from_template(values=field_values, role_to_users_mapping=self.role_to_users_ids)

    def create_project_from_template(self):
        # Opening project task views after creation of project from template
        return self._create_project_from_template().action_view_tasks()

    @api.model
    def action_open_template_view(self):
        view = self.env.ref('project.project_project_view_form_simplified_template', raise_if_not_found=False)
        if not view:
            return {}
        return {
            'name': self.env._('Create a Project from Template %s', self.env.context.get('template_name')),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_model': 'project.template.create.wizard',
            'target': 'new',
            'context': {
                key: value
                for key, value in self.env.context.items()
                if not key.startswith('default_')
            },
        }


class ProjectTemplateRoleToUsersMap(models.TransientModel):
    _name = 'project.template.role.to.users.map'
    _description = 'Project role to users mapping'

    def _domain_user_ids(self):
        return [
            ('share', '=', False),
            ('active', '=', True),
            ('project_role_ids', '=?', unquote('role_id if role_user_ids else False')),
            ('all_group_ids', 'in', self.env.ref('project.group_project_user').ids),
        ]

    wizard_id = fields.Many2one('project.template.create.wizard', export_string_translation=False)
    role_id = fields.Many2one('project.role', string='Project Role', required=True)
    user_ids = fields.Many2many(
        'res.users',
        string='Assignees',
        domain=lambda self: str(self._domain_user_ids()),
    )
    role_user_ids = fields.Many2many(related='role_id.user_ids', export_string_translation=False)
