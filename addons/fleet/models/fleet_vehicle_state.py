from odoo import fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class FleetVehicleState(models.Model):
    _name = "fleet.vehicle.state"
    _order = "sequence asc"
    _description = "Vehicle Status"

    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer()
    fold = fields.Boolean(string="Folded in Kanban")

    _name_src_uniq = name_uniq_index(
        message="State name already exists",
    )
