from odoo import fields, models


class HrLeaveMandatoryDay(models.Model):
    _name = "hr.leave.mandatory.day"
    _inherit = ["mixin.color"]
    _description = "Mandatory Day"
    _order = "start_date desc, end_date desc"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    color = fields.Integer(default=lambda self: self._default_color())
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Working Hours",
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    department_ids = fields.Many2many(
        comodel_name="hr.department",
        string="Departments",
    )
    job_ids = fields.Many2many(
        comodel_name="hr.job",
        string="Job Position",
    )

    _date_from_after_day_to = models.Constraint(
        "CHECK(start_date <= end_date)",
        "The start date must be anterior than the end date.",
    )
