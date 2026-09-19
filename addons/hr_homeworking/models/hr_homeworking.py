from odoo import api, fields, models, tools

PLAIN_IM_STATUSES = ("online", "away", "busy", "offline")

DAYS = [
    "monday_location_id",
    "tuesday_location_id",
    "wednesday_location_id",
    "thursday_location_id",
    "friday_location_id",
    "saturday_location_id",
    "sunday_location_id",
]


class MixinWorkLocationAssignment(models.AbstractModel):
    _name = "mixin.work.location.assignment"
    _description = "One Employee at One Work Location on One Day"

    work_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Location",
        required=True,
        check_company=True,
    )
    work_location_name = fields.Char(
        related="work_location_id.name",
        string="Location name",
    )
    work_location_type = fields.Selection(related="work_location_id.location_type")
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        default=lambda self: self.env.user.employee_id,
        required=True,
        ondelete="cascade",
    )
    employee_name = fields.Char(related="employee_id.name")
    date = fields.Date()
    day_week_string = fields.Char(compute="_compute_day_week_string")

    @api.depends("date")
    def _compute_day_week_string(self):
        for record in self:
            record.day_week_string = tools.format_date(
                record.env, record.date, date_format="EEEE"
            )


class HrEmployeeLocation(models.Model):
    _name = "hr.employee.location"
    _inherit = ["mixin.work.location.assignment"]
    _description = "Employee Location"
    _order = "date desc, employee_id"
    _rec_name = "work_location_name"

    company_id = fields.Many2one(
        comodel_name="res.company",
        related="employee_id.company_id",
    )
    date = fields.Date(required=True)

    _uniq_exceptional_per_day = models.UniqueIndex(
        "(employee_id, date)",
        "An employee has at most one exceptional work location per day.",
    )

    @api.depends("employee_name", "work_location_name", "date")
    def _compute_display_name(self):
        for record in self:
            record.display_name = (
                f"{record.employee_name} - {record.work_location_name} ({record.date})"
            )
