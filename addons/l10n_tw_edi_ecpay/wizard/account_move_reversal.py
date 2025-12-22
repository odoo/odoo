# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMoveReversal(models.TransientModel):
    _inherit = "account.move.reversal"

    l10n_tw_edi_refund_agreement_type = fields.Selection(
        selection=[("offline", "Offline"), ("online", "Online")],
        string="Agreement Type",
    )
    l10n_tw_edi_allowance_notify_way = fields.Selection(
        selection=[("email", "Email"), ("phone", "Phone")],
        string="Allowance Notify Way",
    )
    l10n_tw_edi_ecpay_invoice_id = fields.Char(compute="_compute_from_moves")
    l10n_tw_edi_is_b2b = fields.Boolean(compute="_compute_from_moves")

    def _compute_from_moves(self):
        super()._compute_from_moves()
        for record in self:
            move_ids = record.move_ids._origin
            record.l10n_tw_edi_ecpay_invoice_id = len(move_ids) == 1 and move_ids.l10n_tw_edi_ecpay_invoice_id or False
            record.l10n_tw_edi_is_b2b = len(move_ids) == 1 and move_ids.l10n_tw_edi_is_b2b or False

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        res.update({
            "l10n_tw_edi_ecpay_invoice_id": move.l10n_tw_edi_ecpay_invoice_id,
            "l10n_tw_edi_invoice_create_date": move.l10n_tw_edi_invoice_create_date,
            "l10n_tw_edi_refund_agreement_type": self.l10n_tw_edi_refund_agreement_type,
            "l10n_tw_edi_allowance_notify_way": self.l10n_tw_edi_allowance_notify_way,
            "l10n_tw_edi_invalidate_reason": self.reason,
        })
        return res

    def reverse_moves(self, is_modify=False):
        moves = self.move_ids
        if is_modify:
            for move in moves.filtered(lambda m: m.l10n_tw_edi_ecpay_invoice_id):
                move.l10n_tw_edi_invalidate_reason = self.reason
                move._l10n_tw_edi_run_invoice_invalid()
        return super().reverse_moves(is_modify)
