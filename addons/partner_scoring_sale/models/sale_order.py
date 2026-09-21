from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    tier_id = fields.Many2one(
        comodel_name="partner.tier",
        string="Commercial Tier",
        compute="_compute_tier_id",
        store=True,
        help="The customer's commercial tier: live while the order is a "
        "quotation, the one it was sold under once confirmed.",
    )
    tier_sold_id = fields.Many2one(
        comodel_name="partner.tier",
        string="Tier Sold Under",
        copy=False,
        readonly=True,
        help="The customer's commercial tier at confirmation, frozen so a later "
        "reclassification does not rewrite what was sold to whom.",
    )

    @api.depends("tier_sold_id", "partner_id.commercial_partner_id.tier_id")
    def _compute_tier_id(self):
        for order in self:
            order.tier_id = (
                order.tier_sold_id or order.partner_id.commercial_partner_id.tier_id
            )

    def action_confirm(self):
        result = super().action_confirm()
        for order in self:
            order.tier_sold_id = order.partner_id.commercial_partner_id.tier_id
        return result
