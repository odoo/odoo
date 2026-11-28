from odoo import api, fields, models
from odoo.exceptions import ValidationError


class UniversityResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    university_name = fields.Char(
        string="University Name",
        related="company_id.name",
        readonly=False,
        help="Official name of the university.",
    )
    university_logo = fields.Binary(
        string="University Logo",
        related="company_id.logo",
        readonly=False,
        help="Official university logo displayed on dashboards, academic reports, and student portals.",
    )
    current_academic_year_id = fields.Many2one(
        "university.academic.year",
        string="Current Academic Year",
        config_parameter="school_management.current_academic_year_id",
        domain=[("active", "=", True)],
        help="Academic year currently used by the University application.",
    )
    current_semester_id = fields.Many2one(
        "university.semester",
        string="Current Semester",
        config_parameter="school_management.current_semester_id",
        domain="[('active', '=', True), ('academic_year_id', '=', current_academic_year_id)]",
        help="Semester currently used by the University application.",
    )
    min_teaching_weeks = fields.Float(
        string="Minimum Teaching Weeks",
        config_parameter="school_management.min_teaching_weeks",
        default=14.0,
        help="Minimum required teaching weeks per department term.",
    )
    staff_expected_check_in = fields.Float(
        string="Expected Check-In",
        config_parameter="school_management.staff_expected_check_in",
        default=8.0,
        help="Standard university check-in time (e.g., 8.0 = 08:00 AM).",
    )
    staff_expected_check_out = fields.Float(
        string="Expected Check-Out",
        config_parameter="school_management.staff_expected_check_out",
        default=17.0,
        help="Standard university check-in time (e.g., 17.0 = 05:00 PM).",
    )
    staff_late_grace_minutes = fields.Integer(
        string="Late Grace Period (Minutes)",
        config_parameter="school_management.staff_late_grace_minutes",
        default=15,
        help="Minutes after expected check-in before an arrival is flagged as late.",
    )
    risk_gpa_threshold = fields.Float(
        string="Risk GPA Threshold",
        config_parameter="school_management.risk_gpa_threshold",
        default=2.0,
        help="Students with a cumulative GPA below this threshold are flagged as academic risk.",
    )
    risk_attendance_threshold = fields.Float(
        string="Risk Attendance Threshold (%)",
        config_parameter="school_management.risk_attendance_threshold",
        default=75.0,
        help="Students with an attendance rate below this percentage are flagged as attendance risk.",
    )
    attendance_edit_window_days = fields.Integer(
        string="Attendance Editing Window (Days)",
        config_parameter="school_management.attendance_edit_window_days",
        default=7,
        help="Number of days after an attendance date during which teachers may still "
             "record or correct attendance.",
    )
    transcript_hold_min_balance = fields.Float(
        string="Transcript Hold Minimum Balance",
        config_parameter="school_management.transcript_hold_min_balance",
        default=0.0,
        help="Minimum overdue balance required to trigger a financial hold on transcript requests.",
    )

    @api.onchange("current_academic_year_id")
    def _onchange_current_academic_year_id(self):
        if (
            self.current_semester_id
            and self.current_semester_id.academic_year_id != self.current_academic_year_id
        ):
            self.current_semester_id = False

    @api.constrains("current_academic_year_id", "current_semester_id")
    def _check_current_period(self):
        for settings in self:
            if not settings.current_academic_year_id:
                raise ValidationError("Current Academic Year is required.")
            if not settings.current_semester_id:
                raise ValidationError("Current Semester is required.")
            if (
                settings.current_semester_id.academic_year_id
                != settings.current_academic_year_id
            ):
                raise ValidationError(
                    "The current semester must belong to the selected academic year."
                )

    def set_values(self):
        super().set_values()

        academic_years = self.env["university.academic.year"].sudo().with_context(
            active_test=False
        )
        selected_year = self.current_academic_year_id.sudo()
        academic_years.search([("current", "=", True)]).write({"current": False})
        if selected_year:
            selected_year.write({"current": True})
