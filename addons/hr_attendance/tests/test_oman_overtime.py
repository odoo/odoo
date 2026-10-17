# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, date, UTC
from zoneinfo import ZoneInfo

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('hr_attendance_overtime')
class TestOvertimeRuleRegression(TransactionCase):
    """Regression: working exactly the scheduled hours must not produce overtime output."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        att_type = cls.env.company._get_default_attendance_work_entry_type()

        ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Overtime',
            'code': 'OT_REGR_TEST',
        })

        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.env['hr.time.rule'].create({
            'name': 'Schedule Overtime (Test)',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': ot_type.id,
            'condition_work_entry_type_ids': [(4, att_type.id)],
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'wage': 3000,
        })

    def test_standard_hours_no_accidental_overtime(self):
        """Working exactly the scheduled 8h in a day must not generate any overtime output."""
        # 2026-06-09 is a Tuesday; default calendar is Mon-Fri 8-12 + 13-17 = 8h
        # raw attendance = 8h to match exactly the scheduled hours
        self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': datetime(2026, 6, 9, 8, 0),
            'check_out': datetime(2026, 6, 9, 16, 0),
        })

        output_hours = sum(
            a.worked_hours
            for a in self.env['hr.attendance'].search([
                ('employee_id', '=', self.employee.id),
                ('time_rule_id', '!=', False),
            ])
        )
        self.assertAlmostEqual(
            output_hours, 0.0, places=2,
            msg="Working exactly the scheduled hours must not produce overtime output.",
        )

    def test_overtime_near_local_midnight_non_utc_employee(self):
        """Tests that extra hours logged between local midnight and UTC midnight correctly produce overtime.

        The day is evaluated in the employee's timezone, so the evaluation window should cover the whole local day and not the UTC day.
        """
        for tz_name, extra_start, extra_stop in [
            ('Europe/Brussels', datetime(2026, 10, 9, 0, 30), datetime(2026, 10, 9, 1, 30)),    # UTC+2 -> local day start at 22:00 UTC the day before
            ('America/Bogota', datetime(2026, 10, 9, 22, 30), datetime(2026, 10, 9, 23, 30)),  # UTC-5 -> local day ends at 05:00 UTC the day after
        ]:
            with self.subTest(tz=tz_name):
                tz = ZoneInfo(tz_name)

                def to_utc(dt, tz=tz):
                    return dt.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)

                employee = self.env['hr.employee'].create({
                    'name': f'Employee in {tz_name}',
                    'tz': tz_name,
                    'date_version': date(2026, 1, 1),
                    'contract_date_start': date(2026, 1, 1),
                    'wage': 3000,
                })
                # logged the full 8 scheduled hours
                self.env['hr.attendance'].create({
                    'employee_id': employee.id,
                    'check_in': to_utc(datetime(2026, 10, 9, 8, 0)),
                    'check_out': to_utc(datetime(2026, 10, 9, 16, 0)),
                })
                # one extra hour on the same local day, but on another UTC day
                self.env['hr.attendance'].create({
                    'employee_id': employee.id,
                    'check_in': to_utc(extra_start),
                    'check_out': to_utc(extra_stop),
                })

                outputs = self.env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('time_rule_id', '!=', False),
                ])
                self.assertAlmostEqual(
                    sum(outputs.mapped('worked_hours')), 1.0, places=2,
                    msg="The extra hour on the same local day must be recorded as overtime"
                )
