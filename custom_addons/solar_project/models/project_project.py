from odoo import fields, models

SOLAR_STAGE_SELECTION = [
    ("survey", "Survey"),
    ("design", "Design"),
    ("procurement", "Procurement"),
    ("installation", "Installation"),
    ("handover", "Handover"),
    ("maintenance", "Maintenance"),
]

ROOF_TYPE_SELECTION = [
    ("metal", "Metal / Profiled Sheet"),
    ("tile", "Tile"),
    ("flat", "Flat / Soft Roof"),
    ("ground", "Ground Mount"),
    ("other", "Other"),
]

GRID_TYPE_SELECTION = [
    ("on_grid", "On-Grid"),
    ("off_grid", "Off-Grid"),
    ("hybrid", "Hybrid"),
]


class ProjectProjectSolar(models.Model):
    _inherit = "project.project"

    solar_kw_capacity = fields.Float(
        string="System Capacity (kWp)",
        digits=(10, 2),
        help="Peak power capacity of the solar array in kilowatts-peak.",
    )
    solar_battery_kwh = fields.Float(
        string="Battery Storage (kWh)",
        digits=(10, 2),
        help="Total energy storage capacity of battery bank.",
    )
    solar_roof_type = fields.Selection(
        selection=ROOF_TYPE_SELECTION,
        string="Roof / Mount Type",
    )
    solar_grid_type = fields.Selection(
        selection=GRID_TYPE_SELECTION,
        string="Grid Connection",
    )

    solar_latitude = fields.Float(string="Latitude", digits=(9, 6))
    solar_longitude = fields.Float(string="Longitude", digits=(9, 6))
    solar_address = fields.Char(string="Site Address")

    solar_stage = fields.Selection(
        selection=SOLAR_STAGE_SELECTION,
        string="Project Stage",
        default="survey",
        required=True,
        tracking=True,
    )

    solar_budget_usd = fields.Monetary(
        string="Estimated Budget (USD)",
        currency_field="currency_id",
    )
    solar_estimated_roi_years = fields.Float(
        string="Estimated ROI (years)",
        digits=(5, 1),
        compute="_compute_roi",
        store=True,
    )

    solar_document_ids = fields.One2many(
        comodel_name="solar.document",
        inverse_name="project_id",
        string="Project Documents",
    )
    solar_document_count = fields.Integer(
        compute="_compute_document_count",
        string="Documents",
    )

    def _compute_roi(self):
        for rec in self:
            if rec.solar_kw_capacity and rec.solar_budget_usd:
                annual_yield_usd = rec.solar_kw_capacity * 1200 * 0.05
                rec.solar_estimated_roi_years = (
                    rec.solar_budget_usd / annual_yield_usd if annual_yield_usd else 0
                )
            else:
                rec.solar_estimated_roi_years = 0

    def _compute_document_count(self):
        for rec in self:
            rec.solar_document_count = len(rec.solar_document_ids)
