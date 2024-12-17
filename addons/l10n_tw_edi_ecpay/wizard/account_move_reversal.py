# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    l10n_tw_edi_refund_agreement_type = fields.Selection(
        [("offline", "Offline"), ("online", "Online")],
        default="offline",
        string="Agreement Type",
        required=True,
        help="Refund invoice agreement type",
    )

    def reverse_moves(self, is_modify=False):
        action = super(AccountMoveReversal, self).reverse_moves(is_modify)
        context = dict(self._context or {})

        origin_invoice = self.env["account.move"].browse(context.get("active_ids"))
        if not origin_invoice:
            raise UserError(_("Error. Cannot found origin invoice!"))

        if is_modify:
            origin_invoice._l10n_tw_edi_run_invoice_invalid()
            origin_invoice.l10n_tw_edi_state = "invalid"
        else:
            refund_invoice = self.env["account.move"].browse(action["res_id"])
            refund_invoice.l10n_tw_edi_origin_invoice_number = origin_invoice
            refund_invoice.l10n_tw_edi_ecpay_invoice_id = origin_invoice.l10n_tw_edi_ecpay_invoice_id
            refund_invoice.l10n_tw_edi_invoice_create_date = origin_invoice.l10n_tw_edi_invoice_create_date
            if not refund_invoice:
                raise UserError(_("Error. Cannot found created refund invoice!"))
            refund_invoice.l10n_tw_edi_refund_agreement_type = self.l10n_tw_edi_refund_agreement_type
            refund_invoice.l10n_tw_edi_is_refund = True
        return action
