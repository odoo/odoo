# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import api, fields, models


class AccountInvoiceRefund(models.TransientModel):
    _inherit = "account.move.reversal"

    claim_id = fields.Many2one("crm.claim", readonly=True, string="Return")

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        record_id = self._context.get("active_id", False)
        invoice = self.env["account.move"].browse(record_id)
        claim_ids = (
            invoice.invoice_line_ids.mapped("sale_line_ids")
            .mapped("order_id")
            .mapped("so_claim_id")
            .ids
        )
        claim_id = invoice.claim_id.id or claim_ids and claim_ids[0]
        if claim_id:
            res["claim_id"] = claim_id
        return res

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        if self.claim_id:
            res.update({"claim_id": self.claim_id.id})
        return res

    @api.onchange("claim_id")
    def onchange_claim_id(self):
        record_id = self._context.get("active_id", False)
        invoice = self.env["account.move"].browse(record_id)
        if not invoice.claim_id:
            claim_ids = (
                invoice.invoice_line_ids.mapped("sale_line_ids")
                .mapped("order_id")
                .mapped("so_claim_id")
                .ids
            )
            if claim_ids:
                return {"domain": {"claim_id": [("id", "in", claim_ids)]}}

    def compute_refund(self, mode="refund"):
        res = super().compute_refund(mode=mode)
        refund_id = (
            mode != "modify" and isinstance(res, dict) and res.get("domain")[1][2][0]
        ) or False
        if refund_id:
            self.env["account.move"].browse(refund_id).write(
                {"claim_id": self.claim_id.id}
            )
        return res
