import uuid

from odoo import api, fields, models
from odoo.libs.web import urljoin as url_join


class HrAttendanceConfig(models.Model):
    _name = "hr_attendance.config"
    _description = "A company's hr attendance configuration"
    _inherit = ["mixin.company.config"]

    _attendance_kiosk_key_unique = models.Constraint(
        "UNIQUE(attendance_kiosk_key)",
        "Two companies cannot share a kiosk key.",
    )

    # `float_to_time` raises outside [0, 24], and the cron reads this straight
    # into it once per open attendance: a 25.0 stored here would not surface as
    # a bad setting but as a cron that dies for every employee in the company.
    _auto_check_out_specific_time_in_day = models.Constraint(
        """CHECK (
            auto_check_out_mode IS DISTINCT FROM 'specific_time'
            OR (auto_check_out_specific_time >= 0
                AND auto_check_out_specific_time < 24)
        )""",
        "The automatic check-out time must fall within the day, "
        "between 0:00 and 23:59.",
    )

    hr_attendance_display_overtime = fields.Boolean(string="Display Extra Hours")
    attendance_kiosk_mode = fields.Selection(
        selection=[
            ("barcode", "Barcode / RFID"),
            ("barcode_manual", "Barcode / RFID and Manual Selection"),
            ("manual", "Manual Selection"),
        ],
        string="Attendance Mode",
        default="barcode_manual",
    )
    attendance_barcode_source = fields.Selection(
        selection=[
            ("scanner", "Scanner"),
            ("front", "Front Camera"),
            ("back", "Back Camera"),
        ],
        string="Barcode Source",
        default="front",
    )
    attendance_kiosk_delay = fields.Integer(default=10)
    attendance_kiosk_key = fields.Char(
        default=lambda s: uuid.uuid4().hex,
        copy=False,
        required=True,
        groups="hr_attendance.group_hr_attendance_user",
    )
    attendance_kiosk_url = fields.Char(compute="_compute_attendance_kiosk_url")
    attendance_kiosk_use_pin = fields.Boolean(string="Employee PIN Identification")
    attendance_from_systray = fields.Boolean(default=False)
    attendance_overtime_validation = fields.Selection(
        selection=[
            ("no_validation", "Automatically Approved"),
            ("by_manager", "Approved by Manager"),
        ],
        string="Extra Hours Validation",
        default="no_validation",
    )
    auto_check_out = fields.Boolean(
        string="Automatic Check Out",
        default=False,
    )
    auto_check_out_mode = fields.Selection(
        selection=[
            ("tolerance", "Tolerance"),
            ("specific_time", "Specific Time"),
        ],
        string="Automatic Check Out Based On",
        default="tolerance",
        required=True,
    )
    auto_check_out_tolerance = fields.Float(
        export_string_translation=False,
        default=2,
    )
    auto_check_out_specific_time = fields.Float(
        export_string_translation=False,
        default=20.0,
    )
    absence_management = fields.Boolean(default=False)
    attendance_device_tracking = fields.Boolean(
        string="Device & Location Tracking",
        default=False,
    )

    @api.depends("attendance_kiosk_key")
    def _compute_attendance_kiosk_url(self):
        for company in self:
            company.attendance_kiosk_url = url_join(
                self.env["res.company"].get_base_url(),
                "/hr_attendance/%s" % company.attendance_kiosk_key,
            )

    def _get_new_attendance_kiosk_key(self):
        # `.hex` to match the field default and `_regenerate_attendance_kiosk_key`;
        # a configuration whose key is back-filled at column-init must not end up
        # with a differently shaped token from every other one's.
        return uuid.uuid4().hex

    def _init_column(self, column_name, *, new_column=False):
        if column_name != "attendance_kiosk_key":
            super()._init_column(column_name, new_column=new_column)
        else:
            self.env.cr.execute(
                "SELECT id FROM %s WHERE attendance_kiosk_key IS NULL" % self._table
            )
            attendance_ids = self.env.cr.dictfetchall()
            values_args = [
                (attendance_id["id"], self._get_new_attendance_kiosk_key())
                for attendance_id in attendance_ids
            ]
            query = f"""
                UPDATE {self._table}
                SET attendance_kiosk_key = vals.token
                FROM (VALUES %s) AS vals(id, token)
                WHERE {self._table}.id = vals.id
            """
            self.env.cr.execute_values(query, values_args)

    def _regenerate_attendance_kiosk_key(self):
        self.check_singleton()
        self.write({"attendance_kiosk_key": uuid.uuid4().hex})
