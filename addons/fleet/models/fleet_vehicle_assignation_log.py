from odoo import api, fields, models


class FleetVehicleAssignationLog(models.Model):
    _name = "fleet.vehicle.assignation.log"
    _description = "Drivers history on a vehicle"
    _order = "create_date desc, date_start desc"

    vehicle_id = fields.Many2one(
        comodel_name="fleet.vehicle",
        index=True,
        required=True,
    )
    driver_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
    )
    date_start = fields.Date(string="Start Date")
    date_end = fields.Date(string="End Date")

    @api.depends("driver_id", "vehicle_id")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.vehicle_id.name} - {rec.driver_id.name}"
