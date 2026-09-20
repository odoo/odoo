from odoo import api, fields, models


class ResourceAssetMeter(models.Model):
    _name = "resource.asset.meter"
    _description = "Asset Meter"
    _order = "asset_id, sequence, id"

    asset_id = fields.Many2one(
        comodel_name="resource.asset",
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="asset_id.company_id",
    )
    name = fields.Char(
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    kind = fields.Selection(
        selection=[
            ("odometer", "Odometer"),
            ("hours", "Running Hours"),
            ("cycles", "Cycles"),
        ],
        default="odometer",
        required=True,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
    )
    monotonic = fields.Boolean(
        default=True,
        help="A reading below the previous one is rejected: an odometer only goes up.",
    )
    reading_ids = fields.One2many(
        comodel_name="resource.asset.meter.reading",
        inverse_name="meter_id",
    )
    last_reading_id = fields.Many2one(
        comodel_name="resource.asset.meter.reading",
        compute="_compute_last_reading_id",
        store=True,
    )
    value = fields.Float(
        related="last_reading_id.value",
        string="Current Value",
    )
    date = fields.Datetime(
        related="last_reading_id.date",
        string="Read On",
    )

    _asset_kind_uniq = models.Constraint(
        "UNIQUE(asset_id, kind)", "An asset carries one meter of each kind."
    )

    @api.depends("reading_ids.date", "reading_ids.value")
    def _compute_last_reading_id(self):
        for meter in self:
            meter.last_reading_id = meter.reading_ids.sorted(
                key=lambda r: (r.date, r.id), reverse=True
            )[:1]

    def _value_at(self, moment):
        self.check_singleton()
        reading = self.reading_ids.filtered(lambda r: r.date <= moment).sorted(
            key=lambda r: (r.date, r.id), reverse=True
        )[:1]
        return reading.value if reading else 0.0

    def record(self, value, date=None, source=None):
        self.check_singleton()
        return self.env["resource.asset.meter.reading"].create(
            {
                "meter_id": self.id,
                "value": value,
                "date": date or fields.Datetime.now(),
                "source": source or "manual",
            }
        )
