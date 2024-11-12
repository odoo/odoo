# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class L10n_Vn_Edi_ViettelCancellation(models.TransientModel):
    _name = 'l10n_vn_edi_viettel.cancellation'
    _description = 'E-invoice cancellation wizard'

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Invoice to cancel',
    )
    reason = fields.Char(
        string='Reason',
        required=True,
    )
    agreement_document_name = fields.Char(
        string='Agreement Name',
    )
    agreement_document_date = fields.Datetime(
        string='Agreement Date',
    )

    def button_request_cancel(self):
        self.invoice_id._l10n_vn_edi_cancel_invoice(
            self.reason,
            self.agreement_document_name or 'NA',
            self.agreement_document_date or fields.Datetime.now(),
        )
