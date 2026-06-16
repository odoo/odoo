# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, date

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('hr_attendance_overtime')
class TestOvertimeRuleRegression(TransactionCase):
    """Regression: working exactly the scheduled hours must not produce overtime output."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        att_type = cls.env.ref('hr_work_entry.attendance_work_entry_type')
        cls.env.company.attendance_work_entry_type_id = att_type

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
                ('is_time_rule_output', '=', True),
            ])
        )
        self.assertAlmostEqual(
            output_hours, 0.0, places=2,
            msg="Working exactly the scheduled hours must not produce overtime output.",
        )
