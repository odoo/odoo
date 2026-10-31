from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.tests import tagged, TransactionCase


@tagged('post_install', '-at_install')
class TestHrAttendanceAutomaticRules(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        belgium = cls.env.ref('base.be')
        cls.env.company.country_id = belgium
        cls.env.company.partner_id.country_id = belgium
        cls.env.company.tz = "Europe/Brussels"

        cls.dep_rd = cls.env['hr.department'].create({
            'name': 'Research & Development - Test',
        })

        # Load Belgian Work Entry Types
        cls.attendance_wet = cls.env.ref('hr_work_entry.be_work_entry_type_attendance')
        cls.overtime_wet = cls.env.ref('hr_work_entry.generic_work_entry_type_overtime')

        cls.env.company.attendance_work_entry_type_id = cls.attendance_wet

        cls.calendar_40h = cls.env['resource.calendar'].create({
            'name': 'Standard 40h/week',
            'calendar_type': 'fixed',
            'attendance_ids': [
                (0, 0, {
                    'dayofweek': weekday,
                    'hour_from': hour,
                    'hour_to': hour + 4,
                })
                for weekday in ['0', '1', '2', '3', '4']
                for hour in [8, 13]
            ],
        })
        cls.env.company.resource_calendar_id = cls.calendar_40h

        cls.start = datetime(2026, 11, 1, 1, 0, 0)
        cls.end = datetime(2026, 11, 30, 23, 59, 59)

        # Create employee with an active version/contract covering November 2026
        cls.belgian_emp = cls.env['hr.employee'].create({
            'name': 'Richard',
            'sex': 'male',
            'birthday': '1984-05-01',
            'country_id': belgium.id,
            'department_id': cls.dep_rd.id,
            'wage': 5000.0,
            'attendance_based': True,
            'date_version': cls.start.date() - relativedelta(days=5),
            'contract_date_start': cls.start.date() - relativedelta(days=5),
            'contract_date_end': cls.end.date() + relativedelta(days=5),
            'resource_calendar_id': cls.calendar_40h.id,
        })

    def _create_attendance(self, check_in, check_out):
        return self.env['hr.attendance'].create({
            'employee_id': self.belgian_emp.id,
            'check_in': check_in,
            'check_out': check_out,
            'work_entry_type_id': self.attendance_wet.id,
        })

    def test_automatic_overtime_rule(self):
        """Fixed calendar (40h/week, 8h/day): working 10h generates 8h attendance and 2h overtime."""
        # Monday Nov 2, 2026: 08:00 to 18:00 (10h)
        self._create_attendance(
            datetime(2026, 11, 2, 8, 0, 0),
            datetime(2026, 11, 2, 18, 0, 0),
        )

        attendances = self.env['hr.attendance'].search([('employee_id', '=', self.belgian_emp.id)])
        self.assertEqual(len(attendances), 2)

        reg_att = attendances.filtered(lambda a: a.work_entry_type_id == self.attendance_wet)
        ot_att = attendances.filtered(lambda a: a.work_entry_type_id == self.overtime_wet)

        self.assertEqual(len(reg_att), 1)
        self.assertEqual(len(ot_att), 1)
        self.assertAlmostEqual(reg_att.worked_hours, 8.0)
        self.assertAlmostEqual(ot_att.worked_hours, 2.0)

    def test_automatic_overtime_rule_fully_flexible_calendar(self):
        """Fully flexible calendar (undefined, 0h/w, 0d/w): _is_fully_flexible() is True.

        The employee has no baseline schedule, so the rule is skipped and no overtime is created.
        """
        calendar = self.env['resource.calendar'].create({
            'name': 'Fully Flexible Calendar (0 h/w)',
            'calendar_type': 'undefined',
            'hours_per_week': 0.0,
            'days_per_week': 7,
            'attendance_ids': [(5, 0, 0)],
        })
        self.belgian_emp.version_id.resource_calendar_id = calendar

        self.assertTrue(self.belgian_emp.version_id._is_flexible())
        self.assertTrue(self.belgian_emp.version_id._is_fully_flexible())

        # Monday Nov 2, 2026: 08:00 to 18:00 (10h)
        self._create_attendance(
            datetime(2026, 11, 2, 8, 0, 0),
            datetime(2026, 11, 2, 18, 0, 0),
        )

        attendances = self.env['hr.attendance'].search([('employee_id', '=', self.belgian_emp.id)])
        self.assertEqual(len(attendances), 1)
        self.assertEqual(attendances.work_entry_type_id, self.attendance_wet)
        self.assertAlmostEqual(attendances.worked_hours, 10.0)
