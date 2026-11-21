from odoo import fields, models


class UniversityCapability(models.Model):
    _name = "university.capability"
    _description = "University System Capability"
    _order = "sort_order, id"

    _unique_capability_name = models.Constraint(
        "unique (name)",
        "A capability with this name already exists.",
    )

    name = fields.Char(string="Capability", required=True)
    category = fields.Selection(
        [
            ("structure", "Academic Structure"),
            ("students", "Students"),
            ("staff", "Academic Staff"),
            ("academic", "Academic Operations"),
            ("finance", "Finance"),
            ("system", "System"),
        ],
        string="Category",
        default="system",
        required=True,
    )
    status = fields.Selection(
        [
            ("active", "Active"),
            ("beta", "Beta"),
            ("development", "In Development"),
            ("planned", "Planned"),
        ],
        string="Status",
        default="planned",
        required=True,
    )
    phase = fields.Integer(string="Phase", default=1)
    release_version = fields.Char(string="Released / Target Version")
    released_on = fields.Date(string="Release Date")
    icon = fields.Char(string="Icon", default="fa-cube")
    description = fields.Text(string="Description")
    sort_order = fields.Integer(string="Sort Order", default=10)
    active = fields.Boolean(string="Active", default=True)