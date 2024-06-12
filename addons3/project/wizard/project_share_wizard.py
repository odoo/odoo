# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ProjectShareWizard(models.TransientModel):
    _name = 'project.share.wizard'
    _inherit = 'portal.share'
    _description = 'Project Sharing'

    @api.model
    def default_get(self, fields):
        # The project share action could be called in `project.collaborator`
        # and so we have to check the active_model and active_id to use
        # the right project.
        active_model = self._context.get('active_model', '')
        active_id = self._context.get('active_id', False)
        if active_model == 'project.collaborator':
            active_model = 'project.project'
            active_id = self._context.get('default_project_id', False)
        result = super(ProjectShareWizard, self.with_context(active_model=active_model, active_id=active_id)).default_get(fields)
        if not result.get('access_mode'):
            result.update(
                access_mode='read',
                display_access_mode=True,
            )
        return result

    @api.model
    def _selection_target_model(self):
        project_model = self.env['ir.model']._get('project.project')
        return [(project_model.model, project_model.name)]

    access_mode = fields.Selection([('read', 'Readonly'), ('edit', 'Edit')])
    display_access_mode = fields.Boolean()

    @api.depends('res_model', 'res_id')
    def _compute_resource_ref(self):
        for wizard in self:
            if wizard.res_model and wizard.res_model == 'project.project':
                wizard.resource_ref = '%s,%s' % (wizard.res_model, wizard.res_id or 0)
            else:
                wizard.resource_ref = None

    def action_share_record(self):
        # Confirmation dialog is only opened if new portal user(s) need to be created in a 'on invitation' website
        self.ensure_one()
        on_invite = self.env['res.users']._get_signup_invitation_scope() == 'b2b'
        new_portal_user = self.partner_ids.filtered(lambda p: not p.user_ids) and on_invite
        if not new_portal_user:
            return self.action_send_mail()
        return {
            'name': _('Confirmation'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [(self.env.ref('project.project_share_wizard_confirm_form').id, 'form')],
            'res_model': 'project.share.wizard',
            'res_id': self.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_send_mail(self):
        if self.access_mode == 'edit':
            portal_partners = self.partner_ids.filtered('user_ids')
            self.resource_ref._add_collaborators(self.partner_ids)
            self._send_public_link(portal_partners)
            self._send_signup_link(partners=self.with_context({'signup_valid': True}).partner_ids - portal_partners)
            self.resource_ref.message_subscribe(partner_ids=self.partner_ids.ids)
            return {'type': 'ir.actions.act_window_close'}
        return super().action_send_mail()
