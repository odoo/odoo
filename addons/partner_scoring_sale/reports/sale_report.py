from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    tier_id = fields.Many2one(
        comodel_name="partner.tier",
        string="Commercial Tier",
        readonly=True,
    )

    def _get_fields_select(self) -> dict:
        return {**super()._get_fields_select(), "tier_id": "o.tier_id"}

    def _get_fields_group_by(self) -> list:
        return [*super()._get_fields_group_by(), "o.tier_id"]
