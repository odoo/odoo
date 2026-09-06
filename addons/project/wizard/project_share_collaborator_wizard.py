# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectShareCollaboratorWizard(models.TransientModel):
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
        [('view', 'View'), ('edit', 'Edit'), ('advanced_edit', 'Advanced Edit')],
        default='view',
        string="Access",
        required=True,
        help="View: can access tasks and send messages.\n"
            "Edit: can create and update tasks.\n"
            "Advanced Edit: can create and update tasks, change task priority, and update task stages."
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
            if (collaborator.partner_id not in project.collaborator_ids.partner_id):
                collaborator.send_invitation = True
