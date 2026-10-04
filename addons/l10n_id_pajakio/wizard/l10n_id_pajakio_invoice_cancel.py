# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.exceptions import UserError


class L10nIdPajakioInvoiceCancel(models.TransientModel):
    _name = "l10n_id_pajakio.invoice.cancel"
    _description = "Implements cancelling a Pajak.io invoice."

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

        document = self.invoice_id.l10n_id_coretax_document
        document.l10n_id_pajakio_cancel_reason = self.reason
        document._l10n_id_pajakio_cancel_request()
        self.invoice_id.button_cancel()
