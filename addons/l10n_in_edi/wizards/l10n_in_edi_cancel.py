from odoo import fields, models

from odoo.addons.l10n_in.models.account_invoice import EDI_CANCEL_REASON


class L10n_In_EdiCancel(models.TransientModel):
    _name = "l10n_in_edi.cancel"

    _description = "Cancel E-Invoice"

    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Invoice",
        required=True,
    )
    cancel_reason = fields.Selection(
        selection=list(EDI_CANCEL_REASON.items()),
        required=True,
    )
    cancel_remarks = fields.Char(required=True)

    def cancel_l10n_in_edi_move(self):
        self.move_id.write(
            {
                "l10n_in_edi_cancel_reason": self.cancel_reason,
                "l10n_in_edi_cancel_remarks": self.cancel_remarks,
            }
        )
        self.move_id._l10n_in_edi_cancel_invoice()
