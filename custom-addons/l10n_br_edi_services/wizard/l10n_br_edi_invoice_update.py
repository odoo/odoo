# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _
from odoo.exceptions import UserError


class L10nBrEDIInvoiceUpdate(models.TransientModel):
    _inherit = "l10n_br_edi.invoice.update"

    is_service_invoice = fields.Boolean(
        "Is Service Invoice",
        related="move_id.l10n_br_is_service_transaction",
        help='Technical field used to hide the "reason" field.',
    )

    def default_get(self, fields):
        # Hack to get around the required=True "reason" field which is invisible
        # TODO JOV: move required=True on reason to the view in master
        res = super().default_get(fields)
        move_id = self._context.get("default_move_id")
        if move_id and self.env["account.move"].browse(move_id).l10n_br_is_service_transaction:
            res["reason"] = "unused"
        return res

    def action_submit(self):
        move = self.move_id
        if not move.l10n_br_is_service_transaction:
            return super().action_submit()

        if self.mode != "cancel":
            raise UserError(_("Service invoices can only be cancelled."))

        # Cancel without an API request. Avalara's cancellation API only supports
        # select cities. Customers will instead cancel through their city's portal.
        move.with_context(no_new_invoice=True).message_post(
            body=_("E-invoice cancelled in Odoo, make sure to also cancel it in your city's portal."),
        )
        move.l10n_br_last_edi_status = "cancelled"
        move.button_cancel()
