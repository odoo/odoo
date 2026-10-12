# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.exceptions import UserError


class MyInvoisStatusUpdateWizard(models.TransientModel):
    _name = 'myinvois.document.status.update.wizard'
    _description = 'Document Status Update Wizard'

    document_id = fields.Many2one(
        comodel_name='myinvois.document',
        string='Document To Update',
        required=True,
        readonly=True,
    )
    reason = fields.Char(
        help='Reason for updating the document.',
        required=True,
    )
    new_status = fields.Char(
        help='New status to set on the document.',
        required=True,
        readonly=True,
    )

    def button_request_update(self):
        self.ensure_one()
        if not self.reason.strip():
            raise UserError(self.env._('You must provide a reason for updating the document.'))

        self.document_id._myinvois_update_document(status=self.new_status, reason=self.reason)
