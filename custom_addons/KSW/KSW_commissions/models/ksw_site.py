from odoo import fields, models


class KswSite(models.Model):
    """Project / work site used by the driver-commission sub-form.

    Each site carries the trip-tier configuration that drives the
    waterfall commission calculation. Phase A only declares the model
    + tier fields so the schema is stable; the driver sub-form itself
    is implemented in Phase B.
    """
    _name = 'ksw.site'
    _description = 'KSW Work Site'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        help='Optional short code used in driver-commission filenames.',
    )
    active = fields.Boolean(default=True)

    # ------------------------------------------------------------------
    # Trip-tier configuration (Saudi driver commission scheme)
    # ------------------------------------------------------------------
    # Tier 1: required trips for full attendance (no commission earned).
    # Tiers 2-4: fixed-band commission. Tier 5: open-ended at top rate.
    required_trips_full_month = fields.Integer(
        string='Required Trips (full month)', default=50,
        help='Required multiplied-trips for an employee who worked the '
             'full 30 days. Pro-rated for partial-month attendance: '
             'required_trips = round(required_trips_full_month * '
             'worked_days / 30).',
    )
    tier2_trips = fields.Integer(default=40)
    tier3_trips = fields.Integer(default=40)
    tier4_trips = fields.Integer(default=40)
    tier2_rate = fields.Float(default=10.0, digits=(8, 2))
    tier3_rate = fields.Float(default=15.0, digits=(8, 2))
    tier4_rate = fields.Float(default=20.0, digits=(8, 2))
    tier5_rate = fields.Float(default=25.0, digits=(8, 2))
    note = fields.Text()

