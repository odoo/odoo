import uuid

from odoo import api, fields, models
from odoo.libs.web import urljoin as url_join


class ResCompany(models.Model):
    _inherit = "res.company"

    def _get_new_attendance_kiosk_key(self):
        # `.hex` to match the field default and `_regenerate_attendance_kiosk_key`;
        # a company whose key is back-filled at column-init must not end up with a
        # differently shaped token from every other company's.
        return uuid.uuid4().hex

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
    auto_check_out_tolerance = fields.Float(
        export_string_translation=False,
        default=2,
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

    _attendance_kiosk_key_unique = models.Constraint(
        "UNIQUE(attendance_kiosk_key)",
        "Two companies cannot share a kiosk key.",
    )

    def _regenerate_attendance_kiosk_key(self):
        self.check_singleton()
        self.write({"attendance_kiosk_key": uuid.uuid4().hex})

    def _check_hr_presence_control(self, at_install):
        for company in self.env["res.company"].sudo().search([]):
            if at_install and company.hr_presence_control_login:
                company.hr_presence_control_attendance = True
            if not at_install and company.hr_presence_control_attendance:
                company.hr_presence_control_login = True

    def _action_view_kiosk_mode(self):
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": f"/hr_attendance/kiosk_mode_menu/{self.env.company.id}",
        }
