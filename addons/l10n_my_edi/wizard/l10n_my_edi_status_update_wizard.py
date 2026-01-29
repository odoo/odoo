# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class L10nMyEdiStatusUpdateWizard(models.TransientModel):
    _name = 'l10n_my_edi.document.status.update'
    _description = 'Document Status Update Wizard'

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Document To Update',
        required=True,
        readonly=True,
    )
    reason = fields.Char(
        help='Reason for cancelling the document.',
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
            raise UserError(_('You must provide a reason for updating the document.'))

        self.invoice_id._l10n_my_edi_update_document(status=self.new_status, reason=self.reason)
