from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    subscription_ids = fields.One2many(
        comodel_name="sale.subscription",
        inverse_name="partner_id",
        string="Subscriptions",
    )
    subscription_count = fields.Integer(compute="_compute_subscription_count")

    @api.depends("subscription_ids")
    def _compute_subscription_count(self):
        grouped = self.env["sale.subscription"].read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id"],
            ["partner_id"],
        )
        mapping = {row["partner_id"][0]: row["partner_id_count"] for row in grouped}
        for partner in self:
            partner.subscription_count = mapping.get(partner.id, 0)

    def action_view_subscription_ids(self):
        self.ensure_one()
        action = self.env.ref(
            "sale_subscription.sale_subscription_action", raise_if_not_found=False
        )
        if action:
            values = action.read()[0]
        else:
            values = {
                "type": "ir.actions.act_window",
                "name": "Subscriptions",
                "res_model": "sale.subscription",
                "view_mode": "list,form",
            }
        values["domain"] = [("partner_id", "=", self.id)]
        values["context"] = {"default_partner_id": self.id}
        return values

