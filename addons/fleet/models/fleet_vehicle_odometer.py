from odoo import api, fields, models
from odoo.exceptions import ValidationError


class FleetVehicleOdometer(models.Model):
    _name = "fleet.vehicle.odometer"
    _description = "Odometer log for a vehicle"
    _order = "date desc"

    name = fields.Char(compute="_compute_name", store=True)
    date = fields.Date(default=fields.Date.context_today)
    value = fields.Float("Odometer Value", aggregator="max")
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        required=True,
    )
    unit = fields.Selection(
        related="vehicle_id.odometer_unit",
        string="Unit",
        readonly=True,
    )
    driver_id = fields.Many2one(
        "res.partner",
        compute="_compute_driver_id",
        readonly=False,
        store=True,
    )

    @api.depends("vehicle_id")
    def _compute_driver_id(self):
        for odometer in self:
            if not odometer.driver_id:
                odometer.driver_id = odometer.vehicle_id.driver_id

    @api.depends("vehicle_id", "date")
    def _compute_name(self):
        for record in self:
            name = record.vehicle_id.name
            if not name:
                name = str(record.date)
            elif record.date:
                name += " / " + str(record.date)
            record.name = name

    @api.onchange("vehicle_id")
    def _onchange_vehicle(self):
        if self.vehicle_id:
            self.unit = self.vehicle_id.odometer_unit

    _value_positive = models.Constraint(
        "CHECK(value >= 0)", "An odometer reading cannot be negative."
    )

    @api.constrains("value", "date", "vehicle_id")
    def _check_monotonic(self):
        """An odometer only goes up.

        The rule existed only on ``fleet.vehicle.write({"odometer": ...})``,
        which is one of two ways in and not the one the odometer log view uses:
        creating a ``fleet.vehicle.odometer`` row directly was unguarded, so a
        reading dated after a higher one was accepted and a negative reading
        was accepted too. It also compared against the highest reading rather
        than the neighbouring ones, which is a different question -- see
        ``fleet.vehicle._compute_odometer``.
        """
        readings_by_vehicle = self.search(
            [("vehicle_id", "in", self.vehicle_id.ids)]
        ).grouped("vehicle_id")
        for odometer in self:
            if not odometer.vehicle_id or not odometer.date:
                continue
            neighbours = (
                readings_by_vehicle.get(odometer.vehicle_id, self.browse()) - odometer
            )
            earlier_and_higher = neighbours.filtered(
                lambda other, o=odometer: other.date <= o.date and other.value > o.value
            )
            later_and_lower = neighbours.filtered(
                lambda other, o=odometer: other.date > o.date and other.value < o.value
            )
            if earlier_and_higher or later_and_lower:
                raise ValidationError(
                    self.env._(
                        "%(vehicle)s: a reading of %(value)s on %(date)s would make the"
                        " odometer run backwards.",
                        vehicle=odometer.vehicle_id.display_name,
                        value=odometer.value,
                        date=odometer.date,
                    )
                )
