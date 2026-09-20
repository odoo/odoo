from odoo import api, fields, models


class EventTypeBooth(models.Model):
    _inherit = "event.type.booth"

    product_id = fields.Many2one(related="booth_category_id.product_id")
    price = fields.Float(
        related="booth_category_id.price",
    )
    currency_id = fields.Many2one(related="booth_category_id.currency_id")

    @api.model
    def _get_event_booth_fields_whitelist(self):
        res = super()._get_event_booth_fields_whitelist()
        return res + ["product_id", "price"]
