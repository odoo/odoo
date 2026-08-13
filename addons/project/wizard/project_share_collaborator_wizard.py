# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectSharingCollaboratorWizard(models.TransientModel):
    _name = 'project.share.collaborator.wizard'
    _description = 'Project Sharing Collaborator Wizard'

    parent_wizard_id = fields.Many2one(
        'project.share.wizard',
        export_string_translation=False,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Collaborator',
        required=True,
    )
    access_mode = fields.Selection(
        [('read', 'Read'), ('edit_limited', 'Edit with limited access'), ('edit', 'Edit')],
        default='read',
        required=True,
        help="Read: collaborators can view tasks but cannot edit them.\n"
            "Edit with limited access: collaborators can view and edit tasks they follow in the Kanban view.\n"
            "Edit: collaborators can view and edit all tasks in the Kanban view. Additionally, they can choose which tasks they want to follow."
    )
    send_invitation = fields.Boolean(
        string='Send Invitation',
        compute='_compute_send_invitation',
        store=True,
        readonly=False,
        default=True,
    )

    @api.depends('partner_id', 'access_mode')
    def _compute_send_invitation(self):
        project = self.parent_wizard_id.resource_ref
        for collaborator in self:
            if (
                collaborator.partner_id not in project.message_partner_ids
                or (collaborator.access_mode != 'read' and collaborator.partner_id not in project.collaborator_ids.partner_id)
            ):
                collaborator.send_invitation = True
