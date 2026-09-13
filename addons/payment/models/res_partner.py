from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    payment_token_ids = fields.One2many(
        comodel_name="payment.token",
        inverse_name="partner_id",
        string="Payment Tokens",
    )
    payment_token_count = fields.Integer(compute="_compute_payment_token_count")

    @api.depends("payment_token_ids")
    def _compute_payment_token_count(self):
        payments_data = self.env["payment.token"]._read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id"],
            ["__count"],
        )
        partners_data = {partner.id: count for partner, count in payments_data}
        for partner in self:
            partner.payment_token_count = partners_data.get(partner.id, 0)
