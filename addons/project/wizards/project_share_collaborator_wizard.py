from odoo import api, fields, models

from ..tools import debug_log as dbg


class ProjectShareCollaboratorWizard(models.TransientModel):
    _name = "project.share.collaborator.wizard"
    _description = "Project Sharing Collaborator Wizard"

    parent_wizard_id = fields.Many2one(
        comodel_name="project.share.wizard",
        export_string_translation=False,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Collaborator",
        required=True,
    )
    access_mode = fields.Selection(
        selection=[
            ("view", "View"),
            ("edit", "Edit"),
            ("advanced_edit", "Advanced Edit"),
        ],
        default="view",
        required=True,
        help="View: read the tasks and write in their chatter.\n"
        "Edit: also create and update tasks.\n"
        "Advanced Edit: also move tasks between steps and change their priority.",
    )
    send_invitation = fields.Boolean(
        compute="_compute_send_invitation",
        default=True,
        store=True,
        readonly=False,
    )

    @api.depends("partner_id", "access_mode")
    def _compute_send_invitation(self) -> None:
        project = self.parent_wizard_id.resource_ref
        for collaborator in self:
            if collaborator.partner_id not in project.collaborator_ids.partner_id:
                dbg.logic.debug(
                    "share collaborator: partner %s mode=%s is new to project %s -> "
                    "send_invitation",
                    collaborator.partner_id.id,
                    collaborator.access_mode,
                    project.id,
                )
                collaborator.send_invitation = True
