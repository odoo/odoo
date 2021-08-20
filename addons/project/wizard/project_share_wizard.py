# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError, UserError

from ..models.project_sharing_access import PROJECT_SHARING_ACCESS_MODE


class ProjectShareWizard(models.TransientModel):
    _name = 'project.share.wizard'
    _inherit = 'portal.share'
    _description = 'Project Share'

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if result['res_model'] and result['res_id']:
            project = self.env[result['res_model']].browse(result['res_id'])
            result.update(
                line_ids=[
                    Command.create(
                        {'user_id': access.user_id, 'access_mode': access.access_mode}
                    ) for access in project.project_sharing_access_ids
                ],
            )
        return result

    partner_ids = fields.Many2many(compute="_compute_partner_ids", readonly=False, store=True, required=False)
    line_ids = fields.One2many('project.share.wizard.line', 'project_share_id')
    has_access_changed = fields.Boolean(compute='_compute_has_access_changed')

    @api.depends('line_ids.user_id')
    def _compute_partner_ids(self):
        for project_share_wizard in self:
            project_share_wizard.partner_ids |= project_share_wizard.line_ids.user_id.partner_id

    @api.depends('line_ids.user_id', 'line_ids.access_mode')
    def _compute_has_access_changed(self):
        project_sharing_access_read = self.env['project.sharing.access'].search_read([('project_id', '=', self.res_id)], ['user_id', 'access_mode'])
        project_sharing_access_dict = {res['user_id'][0]: res['access_mode'] for res in project_sharing_access_read}
        for project_share in self:
            if len(project_share.line_ids) != len(project_sharing_access_dict):
                project_share.has_access_changed = True
                continue
            has_access_changed = False
            for line in project_share.line_ids:
                access_mode = project_sharing_access_dict.get(line.user_id.id)
                if not access_mode or access_mode != line.access_mode:
                    has_access_changed = True
                    break
            project_share.has_access_changed = has_access_changed

    def action_send_mail_and_confirm_access(self):
        if not self.partner_ids:
            raise UserError(_('Impossible to send email, no recipients are mentionned.'))
        self.action_confirm_access()
        return self.action_send_mail()

    def action_confirm_access(self):
        project = self.env[self.res_model].browse(self.res_id)
        if not project or not project.exists():
            raise ValidationError(_('Impossible to confirm the project sharing access, the project is not found or project sharing is disabled for this project.'))
        project_sharing_access_dict = {access.user_id.id: access for access in project.project_sharing_access_ids}
        project_sharing_access_vals_list = [
            Command.delete(access.id)
            for user_id, access in project_sharing_access_dict.items()
            if user_id not in self.line_ids.user_id.ids
        ]
        for share_access in self.line_ids:
            project_sharing_access = project_sharing_access_dict.get(share_access.user_id.id)
            if not project_sharing_access:
                project_sharing_access_vals_list.append(
                    Command.create(
                        {'user_id': share_access.user_id.id, 'access_mode': share_access.access_mode}
                    )
                )
            elif project_sharing_access.access_mode != share_access.access_mode:
                project_sharing_access_vals_list.append(Command.update(project_sharing_access.id, {'access_mode': share_access.access_mode}))
        project.write({'project_sharing_access_ids': project_sharing_access_vals_list})
        project.message_subscribe(self.line_ids.user_id.partner_id.ids)
        return {'type': 'ir.actions.act_window_close'}


class ProjectShareAccessWizard(models.TransientModel):
    _name = 'project.share.wizard.line'
    _description = 'Project Share Access'

    project_share_id = fields.Many2one('project.share.wizard', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Portal Users', domain=lambda self: [('groups_id', 'in', self.env.ref('base.group_portal').id)], required=True)
    access_mode = fields.Selection(PROJECT_SHARING_ACCESS_MODE, string='Access Mode', required=True)

    _sql_constraints = [
        ('uniqueness_user', 'UNIQUE(project_share_id, user_id)', 'An user cannot be selected more than once in the project sharing access. Please remove duplicate(s) and try again.'),
    ]
