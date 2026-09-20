from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResourceAssetMeterReading(models.Model):
    _name = "resource.asset.meter.reading"
    _description = "Asset Meter Reading"
    _order = "date desc, id desc"

    meter_id = fields.Many2one(
        comodel_name="resource.asset.meter",
        index=True,
        required=True,
        ondelete="cascade",
    )
    asset_id = fields.Many2one(
        related="meter_id.asset_id",
    )
    company_id = fields.Many2one(
        related="meter_id.company_id",
    )
    date = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        required=True,
    )
    value = fields.Float(required=True)
    source = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("telemetry", "Telemetry"),
            ("service", "Service"),
        ],
        default="manual",
        required=True,
    )
    note = fields.Char()

    _meter_date_idx = models.Index("(meter_id, date)")
    _value_positive = models.Constraint(
        "CHECK(value >= 0)", "A meter reading cannot be negative."
    )

    @api.constrains("value", "date", "meter_id")
    def _check_monotonic(self):
        if self.env.context.get("skip_meter_monotonic"):
            return
        for reading in self.filtered("meter_id.monotonic"):
            neighbours = reading.meter_id.reading_ids - reading
            date, value = reading.date, reading.value
            before = neighbours.filtered(
                lambda r, d=date, v=value: r.date <= d and r.value > v
            )
            after = neighbours.filtered(
                lambda r, d=date, v=value: r.date > d and r.value < v
            )
            if before or after:
                raise ValidationError(
                    self.env._(
                        "%(meter)s: a reading of %(value)s on %(date)s would make the meter run backwards.",
                        meter=reading.meter_id.display_name,
                        value=reading.value,
                        date=reading.date,
                    )
                )
