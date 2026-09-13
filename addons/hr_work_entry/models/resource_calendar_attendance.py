from odoo import fields, models


class ResourceCalendarAttendance(models.Model):
    _inherit = "resource.calendar.attendance"

    def _default_work_entry_type_id(self):
        return self.env.ref(
            "hr_work_entry.work_entry_type_attendance", raise_if_not_found=False
        )

    work_entry_type_id = fields.Many2one(
        comodel_name="hr.work.entry.type",
        default=_default_work_entry_type_id,
        groups="hr.group_hr_user",
    )

    def _copy_attendance_vals(self):
        res = super()._copy_attendance_vals()
        res["work_entry_type_id"] = self.work_entry_type_id.id
        return res
