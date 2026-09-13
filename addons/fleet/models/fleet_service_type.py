from odoo import fields, models


class FleetServiceType(models.Model):
    _name = "fleet.service.type"
    _description = "Fleet Service Type"
    _order = "name"

    name = fields.Char(
        translate=True,
        required=True,
    )
    category = fields.Selection(
        selection=[("contract", "Contract"), ("service", "Service")],
        required=True,
        help="Choose whether the service refer to contracts, vehicle services or both",
    )
