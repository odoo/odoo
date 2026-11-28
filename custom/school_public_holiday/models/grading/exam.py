from odoo import _, api, models


class UniversityExam(models.Model):
    _inherit = "university.exam"

    @api.onchange("exam_date", "section_id")
    def _onchange_exam_date_holiday_warning(self):
        if self.exam_date and self.env["public.holiday"].is_holiday(self.exam_date, section=self.section_id):
            holiday = self.env["public.holiday"].get_holiday_on(self.exam_date)
            holiday_name = holiday.name if holiday else _("University Holiday")
            return {
                "warning": {
                    "title": _("Exam on Holiday Warning"),
                    "message": _(
                        "The selected exam date (%(date)s) falls on holiday '%(holiday)s'. "
                        "Please verify whether exams should be held on this date."
                    ) % {
                        "date": self.exam_date,
                        "holiday": holiday_name,
                    },
                }
            }
