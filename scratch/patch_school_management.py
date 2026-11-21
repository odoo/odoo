with open('custom/school_management/models/staff_attendance.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''    @api.depends("date", "faculty_id")
    def _compute_is_holiday(self):
        for rec in self:
            if not rec.date:
                rec.is_holiday = False
                rec.holiday_name = False
                continue'''

replacement = '''    def _is_non_working_day(self, day):
        """Hook to determine if a given date is a non-working day (e.g. holiday)."""
        return False

    def _get_day_label(self, day):
        """Hook to get display label for a non-working day."""
        return False

    @api.depends("date", "faculty_id")
    def _compute_is_holiday(self):
        for rec in self:
            if not rec.date:
                rec.is_holiday = False
                rec.holiday_name = False
                continue
            if rec._is_non_working_day(rec.date):
                rec.is_holiday = True
                rec.holiday_name = rec._get_day_label(rec.date) or _("Non-Working Day")
                continue'''

assert target in content, 'Target not found in staff_attendance.py'
new_content = content.replace(target, replacement, 1)
with open('custom/school_management/models/staff_attendance.py', 'w', encoding='utf-8') as f:
    f.write(new_content)
print('staff_attendance.py patched')

with open('custom/school_management/models/timetable.py', 'r', encoding='utf-8') as f:
    tt_content = f.read()

tt_target = '''            if conflicts:
                raise ValidationError(
                    _("Timetable conflict detected:\\n• %s") % "\\n• ".join(conflicts)
                )'''

tt_replacement = '''            if conflicts:
                raise ValidationError(
                    _("Timetable conflict detected:\\n• %s") % "\\n• ".join(conflicts)
                )

    def _get_holiday_conflict(self):
        """Hook for holiday modules to detect conflicts with holidays."""
        return False

    @api.constrains("start_time", "section_id")
    def _check_holiday_conflict(self):
        for slot in self:
            conflict = slot._get_holiday_conflict()
            if conflict:
                raise ValidationError(
                    _("Session '%(session)s' conflicts with holiday '%(holiday)s'.")
                    % {
                        "session": slot.name or slot.section_id.name,
                        "holiday": getattr(conflict, "name", str(conflict)),
                    }
                )'''

assert tt_target in tt_content, 'Target not found in timetable.py'
new_tt_content = tt_content.replace(tt_target, tt_replacement, 1)
with open('custom/school_management/models/timetable.py', 'w', encoding='utf-8') as f:
    f.write(new_tt_content)
print('timetable.py patched')
