# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.exceptions import UserError


class L10nTwEDIInvoiceCancel(models.TransientModel):
    _name = "l10n_tw_edi.invoice.cancel"
    _description = "Implements cancelling an ecpay invoice."

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Document To Cancel",
        required=True,
        readonly=True,
    )
    reason = fields.Char(
        help="Reason for cancelling the document.",
        required=True,
    )

    def button_request_cancel(self):
        self.ensure_one()
        if not self.reason.strip():
            raise UserError(self.env._("You must provide a reason for canceling the invoice."))

        self.invoice_id.l10n_tw_edi_invalidate_reason = self.reason
        self.invoice_id._l10n_tw_edi_run_invoice_invalid()
        self.invoice_id.button_cancel()
