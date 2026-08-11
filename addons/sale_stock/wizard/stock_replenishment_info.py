from odoo import fields, models, api


class StockReplenishmentInfo(models.TransientModel):
    _inherit = 'stock.replenishment.info'
    _description = 'Stock delivery time information'

    sale_delay = fields.Integer(
        "Availability Time", related='product_id.sale_delay', readonly=False, related_sudo=False, required=True,
        help="Choose the maximum number of days within which the product should be available for delivery to a customer or for use in other situations."
    )

    @api.depends('sale_delay')
    def _compute_danger_level(self):
        super()._compute_danger_level()

    def _get_warning_days(self):
        lead_days = super()._get_warning_days()
        return lead_days - self.sale_delay
