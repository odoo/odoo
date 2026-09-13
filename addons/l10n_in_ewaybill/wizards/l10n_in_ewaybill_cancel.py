from odoo import fields, models

from odoo.addons.l10n_in.models.account_invoice import EDI_CANCEL_REASON


class L10nInEwaybillCancel(models.TransientModel):
    _name = "l10n.in.ewaybill.cancel"

    _description = "Cancel Ewaybill"

    l10n_in_ewaybill_id = fields.Many2one(
        comodel_name="l10n.in.ewaybill",
        string="Ewaybill",
        required=True,
    )
    cancel_reason = fields.Selection(
        selection=list(EDI_CANCEL_REASON.items()),
        required=True,
    )
    cancel_remarks = fields.Char()

    def cancel_ewaybill(self):
        self.l10n_in_ewaybill_id.write(
            {
                "cancel_reason": self.cancel_reason,
                "cancel_remarks": self.cancel_remarks,
            }
        )
        self.l10n_in_ewaybill_id._ewaybill_cancel()
