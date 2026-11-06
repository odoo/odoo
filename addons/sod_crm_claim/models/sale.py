# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details)

from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    claim_id = fields.Many2one("crm.claim", readonly=True, string="Return")
    #     so_claim_id = fields.Many2one('crm.claim', readonly=True, string='Claim')
    so_claim_id = fields.One2many("crm.claim", "sale_id", string="Returns")
    claims_count = fields.Integer(compute="_compute_claim_count")
    is_fully_return_refund = fields.Boolean("Is Fully Return/Refund", copy=False)

    def _compute_claim_count(self):
        for record in self:
            record.claims_count = self.env["crm.claim"].search_count(
                [("sale_id", "=", record.id)]
            )

    def _prepare_invoice(self):
        self.ensure_one()
        res = super()._prepare_invoice()
        linked_claims = self.mapped("so_claim_id.id")
        res["claim_id"] = self.claim_id.id or linked_claims and linked_claims[0]
        return res

    def open_claims(self):
        self.ensure_one()
        claim_ids = self.env["crm.claim"].search([("sale_id", "=", self.id)]).ids
        action = (
            self.env.ref("sod_crm_claim.crm_claim_category_claim0").sudo().read()[0]
        )
        list_view_id = self.env.ref("sod_crm_claim.crm_case_claims_tree_view").id
        form_view_id = self.env.ref("sod_crm_claim.crm_case_claims_form_view").id
        context = {
            "from_defaults": True,
            "default_claim_type": "customer",
            "default_partner_id": self.partner_id.id,
            "default_sale_id": self.id,
        }
        action["domain"] = [("id", "in", claim_ids)]
        action["views"] = [[list_view_id, "tree"], [form_view_id, "form"]]
        action["context"] = context
        return action


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        res = super()._action_launch_stock_rule(
            previous_product_uom_qty=previous_product_uom_qty
        )
        orders = list({x.order_id for x in self})
        for order in orders:
            if order.claim_id:
                order.picking_ids.write({"claim_id": order.claim_id.id})
        return res
