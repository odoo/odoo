# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import pytz

from odoo.tests.common import tagged
from odoo.addons.hr_work_entry.tests.common import TestWorkEntryBase


@tagged('work_entry')
class TestWorkEntry(TestWorkEntryBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tz = pytz.timezone(cls.richard_emp.tz)
        cls.start = datetime(2015, 11, 1, 1, 0, 0)
        cls.end = datetime(2015, 11, 30, 23, 59, 59)
        cls.resource_calendar_id = cls.env['resource.calendar'].create({'name': 'My Calendar'})
        cls.richard_emp.create_version({
            'date_version': cls.start.date() - relativedelta(days=5),
            'contract_date_start': cls.start.date() - relativedelta(days=5),
            'contract_date_end': cls.end.date() + relativedelta(days=5),
            'name': 'dodo',
            'resource_calendar_id': cls.resource_calendar_id.id,
            'wage': 1000,
            'date_generated_from': cls.end.date() + relativedelta(days=5),
        })

    def test_no_duplicate(self):
        self.richard_emp.generate_work_entries(self.start, self.end)
        pou1 = self.env['hr.work.entry'].search_count([])
        self.richard_emp.generate_work_entries(self.start, self.end)
        pou2 = self.env['hr.work.entry'].search_count([])
        self.assertEqual(pou1, pou2, "Work entries should not be duplicated")

    def test_work_entry(self):
        self.richard_emp.generate_work_entries(self.start, self.end)
        attendance_nb = len(self.resource_calendar_id._attendance_intervals_batch(self.start.replace(tzinfo=pytz.utc), self.end.replace(tzinfo=pytz.utc))[False])
        work_entry_nb = self.env['hr.work.entry'].search_count([
            ('employee_id', '=', self.richard_emp.id),
            ('date', '>=', self.start),
            ('date', '<=', self.end)])
        self.assertEqual(attendance_nb / 2, work_entry_nb, "One work_entry should be generated for each pair of calendar attendance per day")

    def test_validate_undefined_work_entry(self):
        work_entry1 = self.env['hr.work.entry'].create({
            'name': '1',
            'employee_id': self.richard_emp.id,
            'version_id': self.richard_emp.version_id.id,
            'date': self.start.date(),
            'duration': 4,
        })
        work_entry1.work_entry_type_id = False
        self.assertFalse(work_entry1.action_validate(), "It should not validate work_entries without a type")
        self.assertEqual(work_entry1.state, 'conflict', "It should change to conflict state")
        work_entry1.work_entry_type_id = self.work_entry_type
        self.assertTrue(work_entry1.action_validate(), "It should validate work_entries")

    def test_outside_calendar(self):
        """ Test leave work entries outside schedule are conflicting """
        work_entry_1, work_entry_2 = self.create_work_entries([
            # Outside but not a leave
            (datetime(2018, 10, 13, 3, 0), datetime(2018, 10, 13, 4, 0)),
            # Outside and a leave
            (datetime(2018, 10, 13, 1, 0), datetime(2018, 10, 13, 2, 0), self.work_entry_type_leave),
        ])
        (work_entry_1 | work_entry_2)._mark_leaves_outside_schedule()
        self.assertEqual(work_entry_2.state, 'conflict', "It should conflict")
        self.assertNotEqual(work_entry_1.state, 'conflict', "It should not conflict")

    def test_work_entry_timezone(self):
        """ Test work entries with different timezone """
        hk_resource_calendar_id = self.env['resource.calendar'].create({
            'name': 'HK Calendar',
            'tz': 'Asia/Hong_Kong',
            'hours_per_day': 8,
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 7, 'hour_to': 11, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 7, 'hour_to': 11, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 7, 'hour_to': 11, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 7, 'hour_to': 11, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 7, 'hour_to': 11, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
            ]
        })
        hk_employee = self.env['hr.employee'].create({
            'name': 'HK Employee',
            'resource_calendar_id': hk_resource_calendar_id.id,
            'date_version': datetime(2023, 8, 1),
            'contract_date_start': datetime(2023, 8, 1),
            'contract_date_end': False,
            'wage': 1000,
        })
        self.env['resource.calendar.leaves'].create({
            'date_from': pytz.timezone('Asia/Hong_Kong').localize(datetime(2023, 8, 2, 0, 0, 0)).astimezone(pytz.utc).replace(tzinfo=None),
            'date_to': pytz.timezone('Asia/Hong_Kong').localize(datetime(2023, 8, 2, 23, 59, 59)).astimezone(pytz.utc).replace(tzinfo=None),
            'calendar_id': hk_resource_calendar_id.id,
            'work_entry_type_id': self.work_entry_type_leave.id,
        })
        self.env.company.resource_calendar_id = hk_resource_calendar_id
        hk_employee.generate_work_entries(datetime(2023, 8, 1), datetime(2023, 8, 2))
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', hk_employee.id)])
        self.assertEqual(len(work_entries), 2)
        self.assertEqual(work_entries[0].date, date(2023, 8, 1))
        self.assertEqual(work_entries[0].duration, 8)
        self.assertEqual(work_entries[1].date, date(2023, 8, 2))
        self.assertEqual(work_entries[1].duration, 8)

    def test_separate_overlapping_work_entries_by_type(self):
        calendar = self.env['resource.calendar'].create({'name': 'Calendar', 'tz': 'Europe/Brussels'})
        employee = self.env['hr.employee'].create({
            'name': 'Test',
            'resource_calendar_id': calendar.id,
            'date_version': datetime(2024, 9, 1),
            'contract_date_start': datetime(2024, 9, 1),
            'contract_date_end': datetime(2024, 9, 30),
            'wage': 5000.0,
        })
        calendar.attendance_ids -= calendar.attendance_ids.filtered(lambda attendance: attendance.dayofweek == '0')

        entry_type_1, entry_type_2 = self.env['hr.work.entry.type'].create([
            {'name': 'Work type 1', 'is_leave': False, 'code': 'ENTRY_TYPE1'},
            {'name': 'Work type 2', 'is_leave': False, 'code': 'ENTRY_TYPE2'},
        ])

        self.env['resource.calendar.attendance'].create([
            {
                'calendar_id': calendar.id,
                'dayofweek': '0',
                'name': 'Same type 1',
                'hour_from': 8,
                'hour_to': 11,
                'day_period': 'morning',
                'work_entry_type_id': entry_type_1.id,
            },
            {
                'calendar_id': calendar.id,
                'dayofweek': '0',
                'name': 'Same type 2',
                'hour_from': 11,
                'hour_to': 12,
                'day_period': 'morning',
                'work_entry_type_id': entry_type_1.id,
            },
            {
                'calendar_id': calendar.id,
                'dayofweek': '0',
                'name': 'Different types 1',
                'hour_from': 13,
                'hour_to': 16,
                'day_period': 'afternoon',
                'work_entry_type_id': entry_type_1.id,
            },
            {
                'calendar_id': calendar.id,
                'dayofweek': '0',
                'name': 'Different types 2',
                'hour_from': 16,
                'hour_to': 17,
                'day_period': 'afternoon',
                'work_entry_type_id': entry_type_2.id,
            },
        ])

        employee.generate_work_entries(datetime(2024, 9, 2), datetime(2024, 9, 2))
        result_entries = self.env['hr.work.entry'].search([('employee_id', '=', employee.id)])
        work_entry_types = [entry.work_entry_type_id for entry in result_entries]
        self.assertEqual(len(result_entries), 2, 'A shift should be created for each pair of attendance by day')
        self.assertEqual(work_entry_types, [entry_type_1, entry_type_2])

    def test_work_entry_duration(self):
        """ Test the duration of a work entry is rounded to the nearest minute and correctly calculated """
        vals_list = [{
            'name': 'Test Work Entry',
            'employee_id': self.richard_emp.id,
            'version_id': self.richard_emp.version_id.id,
            'date_start': datetime(2023, 10, 1, 9, 0, 0),
            'date_stop': datetime(2023, 10, 1, 9, 59, 59, 999999),
            'work_entry_type_id': self.work_entry_type.id,
        }]
        vals_list = self.env['hr.version']._generate_work_entries_postprocess(vals_list)
        work_entry = self.env['hr.work.entry'].create(vals_list)
        self.assertEqual(work_entry.duration, 1, "The duration should be 1 hour")

    def test_work_entry_different_calendars(self):
        """ Test work entries are correctly created for employees with versions that have different calendar types. """
        flexible_calendar = self.env['resource.calendar'].create({
            'name': 'flexible calendar',
            'flexible_hours': True,
            'full_time_required_hours': 21,
            'hours_per_day': 3,
        })
        # create 4 employees that have versions corresponding to these 4 cases:
        # flexible calendar then standard calendar
        # standard calendar then flexible calendar
        # no calendar (fully flexible) then standard calendar
        # standard calendar then no calendar (fully flexible)
        # the cases of flexible then fully flexible and fully flexible then flexible are similar in logic to the last 2
        # so they should work if last 2 are working properly
        emp_flex_std, emp_std_flex, emp_fullyflex_std, emp_std_fullyflex = self.env['hr.employee'].create([
            {'name': 'emp flex std'},
            {'name': 'emp std flex'},
            {'name': 'emp fullyflex std'},
            {'name': 'emp fullyflex std'},
        ])
        self.env['hr.version'].create([{
            'employee_id': emp_flex_std.id,
            'resource_calendar_id': flexible_calendar.id,
            'date_version': datetime(2025, 9, 1),
            'contract_date_start': datetime(2025, 9, 1),
            'contract_date_end': datetime(2025, 9, 15),
            'name': 'Flex Contract',
            'wage': 5000.0,
            'active': True,
        },
        {
            'employee_id': emp_flex_std.id,
            'resource_calendar_id': self.resource_calendar_id.id,
            'date_version': datetime(2025, 9, 16),
            'contract_date_start': datetime(2025, 9, 16),
            'contract_date_end': datetime(2025, 9, 30),
            'name': 'Std Contract',
            'wage': 5000.0,
            'active': True,
        },
        {
            'employee_id': emp_std_flex.id,
            'resource_calendar_id': self.resource_calendar_id.id,
            'date_version': datetime(2025, 9, 1),
            'contract_date_start': datetime(2025, 9, 1),
            'contract_date_end': datetime(2025, 9, 15),
            'name': 'Std Contract',
            'wage': 5000.0,
            'active': True,
        },
        {
            'employee_id': emp_std_flex.id,
            'resource_calendar_id': flexible_calendar.id,
            'date_version': datetime(2025, 9, 16),
            'contract_date_start': datetime(2025, 9, 16),
            'contract_date_end': datetime(2025, 9, 30),
            'name': 'Flex Contract',
            'wage': 5000.0,
            'active': True,
        },
        {
            'employee_id': emp_fullyflex_std.id,
            'resource_calendar_id': False,
            'date_version': datetime(2025, 9, 1),
            'contract_date_start': datetime(2025, 9, 1),
            'contract_date_end': datetime(2025, 9, 15),
            'name': 'FullyFlex Contract',
            'wage': 5000.0,
            'active': True,
        },
        {
            'employee_id': emp_fullyflex_std.id,
            'resource_calendar_id': self.resource_calendar_id.id,
            'date_version': datetime(2025, 9, 16),
            'contract_date_start': datetime(2025, 9, 16),
            'contract_date_end': datetime(2025, 9, 30),
            'name': 'Std Contract',
            'wage': 5000.0,
            'active': True,
        },
        {
            'employee_id': emp_std_fullyflex.id,
            'resource_calendar_id': self.resource_calendar_id.id,
            'date_version': datetime(2025, 9, 1),
            'contract_date_start': datetime(2025, 9, 1),
            'contract_date_end': datetime(2025, 9, 15),
            'name': 'Std Contract',
            'wage': 5000.0,
            'active': True,
        },
        {
            'employee_id': emp_std_fullyflex.id,
            'resource_calendar_id': False,
            'date_version': datetime(2025, 9, 16),
            'contract_date_start': datetime(2025, 9, 16),
            'contract_date_end': datetime(2025, 9, 30),
            'name': 'FullyFlex Contract',
            'wage': 5000.0,
            'active': True,
        }])

        half1_date_start = date(2025, 9, 1)
        half1_date_end = date(2025, 9, 15)
        half2_date_start = date(2025, 9, 16)
        half2_date_end = date(2025, 9, 30)

        # generate work entries for the 4 employees between (2025, 9, 1) and (2025, 9, 30)
        # then split them into 2 halves (each half corresponding to the work entries generated by 1 contract)
        # the timezones are considered in the split
        all_work_entries = (emp_flex_std + emp_std_flex + emp_fullyflex_std + emp_std_fullyflex).generate_work_entries(date(2025, 9, 1), date(2025, 9, 30))
        flex_std_work_entries = all_work_entries.filtered(lambda e: e.employee_id == emp_flex_std)
        self.assertEqual(len(flex_std_work_entries), 26)
        half1_entries = flex_std_work_entries.filtered(lambda e:
            e.date >= half1_date_start
            and e.date <= half1_date_end)
        half2_entries = flex_std_work_entries.filtered(lambda e:
            e.date >= half2_date_start
            and e.date <= half2_date_end)
        self.assertEqual(len(half1_entries), 15)  # 1 work entry per day (including weekend)
        self.assertTrue(all(entry.duration == 3 for entry in half1_entries))
        self.assertTrue(all(entry.version_id.name == 'Flex Contract' for entry in half1_entries))
        self.assertEqual(len(half2_entries), 11)  # 1 work entries per day, no work entries for weekend
        self.assertTrue(all(entry.duration == 8 for entry in half2_entries))
        self.assertTrue(all(entry.version_id.name == 'Std Contract' for entry in half2_entries))

        std_flex_work_entries = all_work_entries.filtered(lambda e: e.employee_id == emp_std_flex)
        self.assertEqual(len(std_flex_work_entries), 26)
        half1_entries = std_flex_work_entries.filtered(lambda e:
            e.date >= half1_date_start
            and e.date <= half1_date_end)
        half2_entries = std_flex_work_entries.filtered(lambda e:
            e.date >= half2_date_start
            and e.date <= half2_date_end)
        self.assertEqual(len(half1_entries), 11)  # 1 work entries per day, no work entries for weekend
        self.assertTrue(all(entry.duration == 8 for entry in half1_entries))
        self.assertTrue(all(entry.version_id.name == 'Std Contract' for entry in half1_entries))
        self.assertEqual(len(half2_entries), 15)  # 1 work entry per day (including weekend)
        self.assertTrue(all(entry.duration == 3 for entry in half2_entries))
        self.assertTrue(all(entry.version_id.name == 'Flex Contract' for entry in half2_entries))

        fullyflex_std_work_entries = all_work_entries.filtered(lambda e: e.employee_id == emp_fullyflex_std)
        self.assertEqual(len(fullyflex_std_work_entries), 26)
        half1_entries = fullyflex_std_work_entries.filtered(lambda e:
            e.date >= half1_date_start
            and e.date <= half1_date_end)
        half2_entries = fullyflex_std_work_entries.filtered(lambda e:
            e.date >= half2_date_start
            and e.date <= half2_date_end)
        self.assertEqual(len(half1_entries), 15)  # work entries cover the entire duration
        self.assertTrue(all(entry.duration == 24 for entry in half1_entries))
        self.assertTrue(all(entry.version_id.name == 'FullyFlex Contract' for entry in half1_entries))
        self.assertEqual(len(half2_entries), 11)  # 1 work entries per day, no work entries for weekend
        self.assertTrue(all(entry.duration == 8 for entry in half2_entries))
        self.assertTrue(all(entry.version_id.name == 'Std Contract' for entry in half2_entries))

        std_fullyflex_work_entries = all_work_entries.filtered(lambda e: e.employee_id == emp_std_fullyflex)
        self.assertEqual(len(std_fullyflex_work_entries), 26)
        half1_entries = std_fullyflex_work_entries.filtered(lambda e:
            e.date >= half1_date_start
            and e.date <= half1_date_end)
        half2_entries = std_fullyflex_work_entries.filtered(lambda e:
            e.date >= half2_date_start
            and e.date <= half2_date_end)
        self.assertEqual(len(half1_entries), 11)  # 1 work entries per day, no work entries for weekend
        self.assertTrue(all(entry.duration == 8 for entry in half1_entries))
        self.assertTrue(all(entry.version_id.name == 'Std Contract' for entry in half1_entries))
        self.assertEqual(len(half2_entries), 15)  # work entries cover the entire duration
        self.assertTrue(all(entry.duration == 24 for entry in half2_entries))
        self.assertTrue(all(entry.version_id.name == 'FullyFlex Contract' for entry in half2_entries))
