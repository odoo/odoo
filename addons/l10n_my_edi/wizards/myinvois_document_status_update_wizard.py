from odoo import fields, models
from odoo.exceptions import UserError


class MyInvoisStatusUpdateWizard(models.TransientModel):
    _name = "myinvois.document.status.update.wizard"
    _description = "Document Status Update Wizard"

    document_id = fields.Many2one(
        comodel_name="myinvois.document",
        string="Document To Update",
        readonly=True,
        required=True,
    )
    reason = fields.Char(
        help="Reason for updating the document.",
        required=True,
    )
    new_status = fields.Char(
        help="New status to set on the document.",
        readonly=True,
        required=True,
    )

    def button_request_update(self):
        self.check_singleton()
        if not self.reason.strip():
            raise UserError(
                self.env._("You must provide a reason for updating the document.")
            )

        self.document_id._myinvois_update_document(
            status=self.new_status, reason=self.reason
        )
