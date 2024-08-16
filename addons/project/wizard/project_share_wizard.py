# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator

from odoo import Command, api, fields, models, _


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
        if result['res_model'] and result['res_id']:
            project = self.env[result['res_model']].browse(result['res_id'])
            collaborator_vals_list = []
            collaborator_ids = []
            for collaborator in project.collaborator_ids:
                collaborator_ids.append(collaborator.partner_id.id)
                collaborator_vals_list.append({
                    'partner_id': collaborator.partner_id.id,
                    'partner_name': collaborator.partner_id.display_name,
                    'access_mode': 'edit_limited' if collaborator.limited_access else 'edit',
                })
            for follower in project.message_partner_ids:
                if follower.partner_share and follower.id not in collaborator_ids:
                    collaborator_vals_list.append({
                        'partner_id': follower.id,
                        'partner_name': follower.display_name,
                        'access_mode': 'read',
                    })
            if collaborator_vals_list:
                collaborator_vals_list.sort(key=operator.itemgetter('partner_name'))
                result['collaborator_ids'] = [
                    Command.create({'partner_id': collaborator['partner_id'], 'access_mode': collaborator['access_mode'], 'send_invitation': False})
                    for collaborator in collaborator_vals_list
                ]
        return result

    @api.model
    def _selection_target_model(self):
        project_model = self.env['ir.model']._get('project.project')
        return [(project_model.model, project_model.name)]

    share_link = fields.Char("Public Link", help="Anyone with this link can access the project in read mode.")
    collaborator_ids = fields.One2many('project.share.collaborator.wizard', 'parent_wizard_id', string='Collaborators')
    existing_partner_ids = fields.Many2many('res.partner', compute='_compute_existing_partner_ids', export_string_translation=False)

    @api.depends('res_model', 'res_id')
    def _compute_resource_ref(self):
        for wizard in self:
            if wizard.res_model and wizard.res_model == 'project.project':
                wizard.resource_ref = '%s,%s' % (wizard.res_model, wizard.res_id or 0)
            else:
                wizard.resource_ref = None

    @api.depends('collaborator_ids')
    def _compute_existing_partner_ids(self):
        for wizard in self:
            wizard.existing_partner_ids = wizard.collaborator_ids.partner_id

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            collaborator_ids_to_add = []
            collaborator_ids_to_add_with_limited_access = []
            collaborator_ids_vals_list = []
            project = wizard.resource_ref
            project_collaborator_ids_to_remove = [
                c.id
                for c in project.collaborator_ids
                if c.partner_id not in wizard.collaborator_ids.partner_id
            ]
            project_followers = project.message_partner_ids
            project_followers_to_add = []
            project_followers_to_remove = [
                partner.id
                for partner in project_followers
                if partner not in wizard.collaborator_ids.partner_id
            ]
            project_collaborator_per_partner_id = {c.partner_id.id: c for c in project.collaborator_ids}
            for collaborator in wizard.collaborator_ids:
                partner_id = collaborator.partner_id.id
                project_collaborator = project_collaborator_per_partner_id.get(partner_id, self.env['project.collaborator'])
                if collaborator.access_mode in ("edit", "edit_limited"):
                    limited_access = collaborator.access_mode == "edit_limited"
                    if not project_collaborator:
                        if limited_access:
                            collaborator_ids_to_add_with_limited_access.append(partner_id)
                        else:
                            collaborator_ids_to_add.append(partner_id)
                    elif project_collaborator.limited_access != limited_access:
                        collaborator_ids_vals_list.append(
                            Command.update(
                                project_collaborator.id,
                                {'limited_access': limited_access},
                            )
                        )
                elif project_collaborator:
                    project_collaborator_ids_to_remove.append(project_collaborator.id)
                if partner_id not in project_followers.ids:
                    project_followers_to_add.append(partner_id)
            if collaborator_ids_to_add:
                partners = project._get_new_collaborators(self.env['res.partner'].browse(collaborator_ids_to_add))
                collaborator_ids_vals_list.extend(Command.create({'partner_id': partner_id}) for partner_id in partners.ids)
            if collaborator_ids_to_add_with_limited_access:
                partners = project._get_new_collaborators(self.env['res.partner'].browse(collaborator_ids_to_add_with_limited_access))
                collaborator_ids_vals_list.extend(
                    Command.create({'partner_id': partner_id, 'limited_access': True}) for partner_id in partners.ids
                )
            if project_collaborator_ids_to_remove:
                collaborator_ids_vals_list.extend(Command.delete(collaborator_id) for collaborator_id in project_collaborator_ids_to_remove)
            project_vals = {}
            if collaborator_ids_vals_list:
                project_vals['collaborator_ids'] = collaborator_ids_vals_list
            if project_vals:
                project.write(project_vals)
            if project_followers_to_add:
                project._add_followers(self.env['res.partner'].browse(project_followers_to_add))
            if project_followers_to_remove:
                project.message_unsubscribe(project_followers_to_remove)
        return wizards

    def action_share_record(self):
        # Confirmation dialog is only opened if new portal user(s) need to be created in a 'on invitation' website
        self.ensure_one()
        on_invite = self.env['res.users']._get_signup_invitation_scope() == 'b2b'
        new_portal_user = self.collaborator_ids.filtered(lambda c: c.send_invitation and not c.partner_id.user_ids) and on_invite
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
        self.env['project.project'].browse(self.res_id).privacy_visibility = 'portal'
        result = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': _("Project shared with your collaborators."),
                'next': {'type': 'ir.actions.act_window_close'},
            }}
        partner_ids_in_readonly_mode = []
        partner_ids_in_edit_mode = []
        for collaborator in self.collaborator_ids:
            if not collaborator.send_invitation:
                continue
            if collaborator.access_mode == 'read':
                partner_ids_in_readonly_mode.append(collaborator.partner_id.id)
            else:
                partner_ids_in_edit_mode.append(collaborator.partner_id.id)
        if partner_ids_in_edit_mode:
            new_collaborators = self.env['res.partner'].browse(partner_ids_in_edit_mode)
            portal_partners = new_collaborators.filtered('user_ids')
            # send mail to users
            self._send_public_link(portal_partners)
            self._send_signup_link(partners=new_collaborators.with_context({'signup_valid': True}) - portal_partners)
        if partner_ids_in_readonly_mode:
            self.partner_ids = self.env['res.partner'].browse(partner_ids_in_readonly_mode)
            super().action_send_mail()
        return result
