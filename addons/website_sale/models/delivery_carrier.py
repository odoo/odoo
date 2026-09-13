from odoo import fields, models


class DeliveryCarrier(models.Model):
    _name = "delivery.carrier"
    _inherit = ["delivery.carrier", "mixin.website.published.multi"]

    website_description = fields.Text(
        related="product_id.description_sale",
        string="Description for Online Quotations",
        readonly=False,
    )
