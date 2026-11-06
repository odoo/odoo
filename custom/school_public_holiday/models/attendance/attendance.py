from odoo import _, api, models
from odoo.exceptions import ValidationError


class UniversityAttendanceSession(models.Model):
    _inherit = "university.attendance.session"

    @api.constrains("date", "section_id")
    def _check_attendance_session_holiday(self):
        if self.env.context.get("skip_holiday_check"):
            return
        PubHoliday = self.env["public.holiday"]
        if PubHoliday._is_holiday_admin():
            return
        for session in self:
            if session.date and PubHoliday.is_holiday(session.date, section=session.section_id):
                holiday = PubHoliday.get_holiday_on(session.date)
                h_name = holiday.name if holiday else _("University Holiday")
                raise ValidationError(
                    _("Cannot record attendance session on %(date)s because it falls on holiday '%(holiday)s'.")
                    % {"date": session.date, "holiday": h_name}
                )


class UniversityAttendance(models.Model):
    _inherit = "university.attendance"

    @api.constrains("date", "section_id")
    def _check_attendance_holiday(self):
        if self.env.context.get("skip_holiday_check"):
            return
        PubHoliday = self.env["public.holiday"]
        if PubHoliday._is_holiday_admin():
            return
        for att in self:
            if att.date and PubHoliday.is_holiday(att.date, section=att.section_id):
                holiday = PubHoliday.get_holiday_on(att.date)
                h_name = holiday.name if holiday else _("University Holiday")
                raise ValidationError(
                    _("Cannot mark attendance on %(date)s because it falls on holiday '%(holiday)s'.")
                    % {"date": att.date, "holiday": h_name}
                )
