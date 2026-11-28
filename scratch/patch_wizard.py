with open("custom/school_management/wizard/timetable_generation_wizard.py", "r", encoding="utf-8") as f:
    content = f.read()

target1 = '''    def _find_holiday(self, target_date, holidays, section=None):'''

replacement1 = '''    def _get_excluded_dates(self, date_start, date_end):
        """Hook for extension modules (e.g. school_public_holiday) to exclude dates from timetable generation."""
        return set()

    def _find_holiday(self, target_date, holidays, section=None):'''

assert target1 in content, "target1 not found"
content = content.replace(target1, replacement1, 1)

target2 = '''    def _create_series(self, base_vals, timeslot, monday, holidays=None, section=None, subject=None):
        Slot = self.env["university.timetable.slot"]
        try:
            with self.env.cr.savepoint():
                records = Slot
                holiday_skips = []
                for week in range(self.week_count):
                    target_date = monday + timedelta(days=int(timeslot.day_of_week) + week * 7)
                    holiday = self._find_holiday(target_date, holidays, section)'''

replacement2 = '''    def _create_series(self, base_vals, timeslot, monday, holidays=None, section=None, subject=None, excluded_dates=None):
        Slot = self.env["university.timetable.slot"]
        if excluded_dates is None:
            date_end = monday + timedelta(days=self.week_count * 7)
            excluded_dates = self._get_excluded_dates(monday, date_end)
        try:
            with self.env.cr.savepoint():
                records = Slot
                holiday_skips = []
                for week in range(self.week_count):
                    target_date = monday + timedelta(days=int(timeslot.day_of_week) + week * 7)
                    if target_date in excluded_dates:
                        subj_name = subject.display_name if subject else "Session"
                        sec_name = section.display_name if section else ""
                        holiday_skips.append(
                            f"{sec_name} / {subj_name} on {target_date} skipped (Public Holiday)"
                        )
                        continue
                    holiday = self._find_holiday(target_date, holidays, section)'''

assert target2 in content, "target2 not found"
content = content.replace(target2, replacement2, 1)

target3 = '''        holidays = self.env["university.holiday"].search([
            ("academic_year_id", "=", self.academic_year_id.id),
        ])'''

replacement3 = '''        holidays = self.env["university.holiday"].search([
            ("academic_year_id", "=", self.academic_year_id.id),
        ])

        date_start = monday
        date_end = monday + timedelta(days=self.week_count * 7)
        excluded_dates = self._get_excluded_dates(date_start, date_end)'''

assert target3 in content, "target3 not found"
content = content.replace(target3, replacement3, 1)

target4 = '''                        records, err, holiday_skips = self._create_series(
                            base_vals, candidate_slot, monday,
                            holidays=holidays, section=section, subject=subject
                        )'''

replacement4 = '''                        records, err, holiday_skips = self._create_series(
                            base_vals, candidate_slot, monday,
                            holidays=holidays, section=section, subject=subject,
                            excluded_dates=excluded_dates
                        )'''

assert target4 in content, "target4 not found"
content = content.replace(target4, replacement4, 1)

with open("custom/school_management/wizard/timetable_generation_wizard.py", "w", encoding="utf-8") as f:
    f.write(content)
print("timetable_generation_wizard.py successfully patched")
