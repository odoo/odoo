# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    claim_id = fields.Many2one("crm.claim", readonly=True, string="Return")

    def action_view_invoice(self, invoices=False):
        res = super().action_view_invoice(invoices=invoices)
        if self.claim_id and "context" in res:
            res["context"] = safe_eval(res["context"])
            res["context"]["default_claim_id"] = self.claim_id.id
        return res
