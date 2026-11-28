from datetime import timedelta
from odoo import _, fields, models


class UniversityTimetableGenerationWizard(models.TransientModel):
    _inherit = "university.timetable.generation.wizard"

    skip_public_holidays = fields.Boolean(
        string="Skip Public Holidays",
        default=True,
        help="Automatically skip scheduling sessions on public holiday dates.",
    )
    skipped_holidays_count = fields.Integer(
        string="Skipped Holiday Dates",
        default=0,
        readonly=True,
    )

    def _is_holiday(self, date_check):
        """Helper to determine if a given date falls on an active holiday."""
        return self.env["public.holiday"].is_holiday(date_check, section=self.section_ids[:1])

    def _get_excluded_dates(self, date_start, date_end):
        excluded = super()._get_excluded_dates(date_start, date_end)
        if not self.skip_public_holidays:
            return excluded

        d_start = fields.Date.to_date(date_start)
        d_end = fields.Date.to_date(date_end)
        if not d_start or not d_end:
            return excluded

        PubHoliday = self.env["public.holiday"]
        cur = d_start
        while cur <= d_end:
            if PubHoliday.is_holiday(cur, section=self.section_ids[:1]):
                excluded.add(cur)
            cur += timedelta(days=1)
        return excluded

    def action_generate_timetable(self):
        res = super().action_generate_timetable()
        if self.skip_public_holidays:
            week_start = fields.Date.to_date(self.start_date)
            monday = week_start - timedelta(days=week_start.weekday())
            end_date = monday + timedelta(days=self.week_count * 7)
            excluded = self._get_excluded_dates(monday, end_date)
            self.skipped_holidays_count = len(excluded)
            if isinstance(res, dict) and "name" in res and self.skipped_holidays_count > 0:
                res["name"] = f"{res['name']} ({self.skipped_holidays_count} Holiday Dates Skipped)"

        # Check if any generated slots fall on a holiday and report conflicts/warnings
        created_slot_ids = []
        if isinstance(res, dict) and "domain" in res:
            for clause in res.get("domain", []):
                if len(clause) == 3 and clause[0] == "id" and clause[1] == "in":
                    created_slot_ids = clause[2]
        if created_slot_ids:
            holiday_slots = self.env["university.timetable.slot"].browse(created_slot_ids).filtered(lambda s: s.on_holiday)
            if holiday_slots:
                conflict_names = ", ".join(sorted(set(s.holiday_name for s in holiday_slots if s.holiday_name)))
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Public Holiday Conflicts Detected"),
                        "message": _(
                            "%d generated session(s) fall on public holidays (%s). Please review and reschedule them."
                        ) % (len(holiday_slots), conflict_names),
                        "type": "warning",
                        "sticky": True,
                        "next": res,
                    },
                }
        return res
