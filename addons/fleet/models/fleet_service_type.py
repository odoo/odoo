from odoo import fields, models


class FleetServiceType(models.Model):
    _name = "fleet.service.type"
    _description = "Fleet Service Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    category = fields.Selection(
        [("contract", "Contract"), ("service", "Service")],
        required=True,
        help="Choose whether the service refer to contracts, vehicle services or both",
    )
