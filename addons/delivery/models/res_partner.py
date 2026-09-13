from odoo import fields, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_delivery_carrier_id = fields.Many2one(
        comodel_name="delivery.carrier",
        string="Delivery Method",
        company_dependent=True,
        help="Used in sales orders.",
    )
    is_pickup_location = fields.Boolean()  # Whether it is a pickup point address.

    def _get_domain_delivery_address(self):
        return super()._get_domain_delivery_address() & Domain(
            "is_pickup_location", "=", False
        )
