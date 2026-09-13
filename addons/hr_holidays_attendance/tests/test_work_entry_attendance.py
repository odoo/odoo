# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from freezegun import freeze_time

from odoo.tests import tagged

from .common import HrWorkEntryAttendanceCommon


@tagged('-at_install', 'post_install', 'work_entry_attendance')
class TestWorkentryAttendance(HrWorkEntryAttendanceCommon):

    def test_basic_generation(self):
        # Create an attendance for each afternoon of september
        attendance_vals_list = []
        for i in range(1, 31):
            new_date = datetime(2021, 9, i, 13, 0, 0)
            if new_date.weekday() >= 5:
                continue
            attendance_vals_list.append({
                'employee_id': self.employee.id,
                'check_in': new_date,
                'check_out': new_date.replace(hour=17),
            })
        attendances = self.env['hr.attendance'].create(attendance_vals_list)
        work_entries_vals = self.version.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        self.assertEqual(len(attendances), len(work_entries_vals))

    def test_timezones(self):
        """ Basic check that timezones do not cause weird behaviors:
            * check that the date range of ``generate_work_entries`` accounts for timezones.
            * check that times are all stored in utc and are not improperly converted
        """
        self.employee.version_id.tz = 'Asia/Tokyo'
        monday_morning_tokyo = datetime(2024, 10, 20, 22, 0, 0)  # 22:00 sunday utc = 7:00 monday tokyo
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': monday_morning_tokyo,
            'check_out': monday_morning_tokyo.replace(day=21, hour=6),  # 15:00
        })
        work_entries_vals = self.version.generate_work_entries(date(2024, 10, 21), date(2024, 10, 21))
        work_entries_vals = [vals for vals in work_entries_vals if vals['date'] >= monday_morning_tokyo.date()]

        self.assertEqual(len(work_entries_vals), 1)
        self.assertEqual(work_entries_vals[0]['date'], date(2024, 10, 21))
        self.assertEqual(work_entries_vals[0]['duration'], 8)

    def test_attendance_within_period(self):
        # Tests that an attendance created within an already generated period generates a work entry
        boundaries_attendances = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 1, 14, 0, 0),
                'check_out': datetime(2021, 9, 1, 17, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 30, 14, 0, 0),
                'check_out': datetime(2021, 9, 30, 17, 0, 0),
            },
        ])
        work_entries_vals = self.version.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        self.assertEqual(len(work_entries_vals), len(boundaries_attendances))

        inner_attendance = self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 14, 14, 0, 0),
                'check_out': datetime(2021, 9, 14, 17, 0, 0),
            }
        ])
        work_entries_vals = self.version.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        self.assertEqual(len(work_entries_vals), len(boundaries_attendances) + len(inner_attendance))

    @freeze_time("2021-09-01")  # to have the timezone in summer time
    def test_attendance_spanning_days(self):
        # Tests that attendances that cross midnight generate work entries that do not cross midnight
        # or conflict. 2 entries for init, 2 for the first attendance, and 4 for the second due to lunch
        self.version.write({
            'resource_calendar_id': False,
            'tz': 'Europe/Brussels',  # The test is wrongly designed with the timezones, attendances should really span two days WITH the tz applied
        })
        self.env['hr.attendance'].create(
            {
            'employee_id': self.employee.id,
            'check_in': datetime(2021, 9, 10, 22, 0, 0),
            'check_out': datetime(2021, 9, 11, 6, 0, 0),
            }
        )
        self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 11, 22, 0, 0),
                'check_out': datetime(2021, 9, 12, 6, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 13, 22, 0, 0),
                'check_out': datetime(2021, 9, 15, 6, 0, 0),
            },
        ])
        work_entries_vals = self.employee.version_id.generate_work_entries(date(2021, 9, 10), date(2021, 9, 15))
        self.assertEqual(len(work_entries_vals), 4)
        self.assertEqual([vals['duration'] for vals in work_entries_vals], [8.0, 8.0, 24.0, 8.0])

    def test_multiple_attendances_same_day(self):
        """
        Test that multiple attendances on the same day create only one work entry for that day
        with the correct total duration.
        """
        self.env['hr.attendance'].create([
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 15, 8, 0, 0),
                'check_out': datetime(2021, 9, 15, 12, 0, 0),
            },
            {
                'employee_id': self.employee.id,
                'check_in': datetime(2021, 9, 15, 13, 0, 0),
                'check_out': datetime(2021, 9, 15, 17, 0, 0),
            }
        ])

        work_entries_vals = self.version.generate_work_entries(date(2021, 9, 15), date(2021, 9, 15))
        self.assertEqual(len(work_entries_vals), 1)
        self.assertEqual(work_entries_vals[0]['duration'], 8)

    def test_gto_flexible_calendar(self):
        """
        Test when having a public time off and a flexible user has two
        separate attendances in this day what will be the duration of the
        holiday work entries.
        """
        start = datetime(2018, 1, 1, 6, 0, 0)
        end = datetime(2018, 1, 1, 18, 0, 0)
        self.env['resource.calendar.leaves'].create({
            'date_from': start,
            'date_to': end,
            'work_entry_type_id': self.work_entry_type_leave.id,
        })

        self.richard_emp.version_id.write({
            'resource_calendar_id': False,
            'hours_per_week': 40,
            'hours_per_day': 8,
            'attendance_based': True,
            'tz': 'Europe/Brussels',
        })

        self.env['hr.attendance'].create([
            {
                'check_in': datetime(2018, 1, 1, 9, 0, 0),
                'check_out': datetime(2018, 1, 1, 11, 0, 0),
                'employee_id': self.richard_emp.id,
            },
            {
                'check_in': datetime(2018, 1, 1, 13, 0, 0),
                'check_out': datetime(2018, 1, 1, 15, 0, 0),
                'employee_id': self.richard_emp.id,
            }
        ])

        work_entries_vals = self.richard_emp.version_ids.generate_work_entries(start.date(), end.date())
        time_off_entries = [vals for vals in work_entries_vals if vals['work_entry_type_id'].code == 'LEAVETEST100']
        other_entries = [vals for vals in work_entries_vals if vals['work_entry_type_id'].code != 'LEAVETEST100']
        # Since we are now merging similar work entries on the same day
        # we are going to have only one leave entry
        self.assertEqual(len(time_off_entries), 1)
        self.assertEqual(sum(vals['duration'] for vals in time_off_entries), 8)
        self.assertEqual(sum(vals['duration'] for vals in other_entries), 4)

    def test_fully_flexible_employee_overlapping_leaves(self):
        """
        Test Fully Flexible employee with overlapping leaves doesn't cause singleton errors.
        """
        fully_flexible_emp = self.env['hr.employee'].create({
            'name': 'Flexible Employee',
            'date_version': datetime(2025, 6, 1).date(),
            'contract_date_start': datetime(2025, 6, 1).date(),
            'wage': 5000.0,
            'attendance_based': True,
            'resource_calendar_id': False,
        })

        sick_work_entry_type = self.env['hr.work.entry.type'].search([('code', '=', 'LEAVE110')], limit=1)

        self.env['resource.calendar.leaves'].create([
            {
                'name': 'Sick Leave',
                'date_from': datetime(2025, 6, 25),
                'date_to': datetime(2025, 6, 29),
                'resource_id': fully_flexible_emp.resource_id.id,
                'work_entry_type_id': sick_work_entry_type.id,
            },
            {
                'name': 'Public Holiday',
                'date_from': datetime(2025, 6, 27),
                'date_to': datetime(2025, 6, 27, 23, 59, 59),
                'calendar_id': False,
                'work_entry_type_id': self.work_entry_type_leave.id,
            }
        ])

        # This should NOT raise singleton errors
        fully_flexible_emp.generate_work_entries(
            datetime(2025, 6, 25).date(),
            datetime(2025, 6, 29).date()
        )
