# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install', 'time_rule_day_types', 'time_rule_pipeline')
class TestTimeRuleDayTypes(TransactionCase):
    """Pipeline tests for time rules operating on day and half-day leave types.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.calendar = cls.env['resource.calendar'].create({
            'name': '40h/week UTC',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env.company.resource_calendar_id = cls.calendar

        # source (condition) time type
        cls.day_wet = cls.env['hr.work.entry.type'].create({
            'name': 'Test Day Type',
            'code': 'TESTDAY',
            'request_unit': 'day',
            'requires_allocation': False,
            'count_as': 'absence',
        })
        # target (output) time type after reclassification
        cls.other_day_wet = cls.env['hr.work.entry.type'].create({
            'name': 'Reclassified Day Type',
            'code': 'TESTDAY2',
            'request_unit': 'day',
            'requires_allocation': False,
            'count_as': 'absence',
        })

        cls.comp_wet = cls.env['hr.work.entry.type'].create({
            'name': 'Compensatory Leave',
            'code': 'COMPDAY',
            'request_unit': 'day',
            'requires_allocation': True,
            'count_as': 'absence',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'tz': 'UTC',
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
        })

    def setUp(self):
        super().setUp()
        # disable any pre-existing time rules and create a fresh one per test
        self.env['hr.time.rule'].search([]).write({'active': False})
        self.time_rule = self.env['hr.time.rule'].create({
            'name': 'Reclassify day leave',
            'condition_work_entry_type_ids': [(4, self.day_wet.id)],
            'work_entry_type_id': self.other_day_wet.id,
            # 'day' mode = fixed threshold (not schedule-based); 0.0 means any leave > 0h fires
            'working_hours_mode': 'day',
            'expected_hours': 0.0,
        })

    def _make_day_leave(self, date_from, date_to, wet=None):
        """Create a validated day-unit leave with exact timestamps."""
        wet = wet or self.day_wet
        return self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_skip_date_check=True,
            leave_fast_create=True,
            leave_skip_state_check=True,
            leave_skip_date_from_to_computation=True,
        ).sudo().create({
            'employee_id': self.employee.id,
            'work_entry_type_id': wet.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': date_from.date(),
            'request_date_to': date_to.date(),
            'state': 'validate',
        })

    def test_day_leave_reclassified_in_place(self):
        """A day-unit leave spanning the lunch break is archived; two output children are created.

        The pipeline clips to working intervals, so the morning block (8:00-12:00) and
        afternoon block (13:00-16:00) each become a separate output record.  The lunch gap
        is not a working interval and produces no remainder record.
        """
        # Jan 3 2022 = Monday; 8:00-16:00 spans the 12:00-13:00 lunch gap
        df = datetime(2022, 1, 3, 8, 0)
        dt = datetime(2022, 1, 3, 16, 0)
        source = self._make_day_leave(df, dt)

        outputs = source.output_leave_ids
        self.assertEqual(len(outputs), 2, "Two output records: morning and afternoon blocks")
        outputs = outputs.sorted('date_from')

        morning = outputs[0]
        self.assertEqual(morning.work_entry_type_id, self.other_day_wet)
        self.assertEqual(morning.time_rule_id, self.time_rule)
        self.assertEqual(morning.date_from, df, "Morning output starts at 8:00")
        self.assertEqual(morning.date_to, datetime(2022, 1, 3, 12, 0), "Morning output ends at 12:00")

        afternoon = outputs[1]
        self.assertEqual(afternoon.work_entry_type_id, self.other_day_wet)
        self.assertEqual(afternoon.time_rule_id, self.time_rule)
        self.assertEqual(afternoon.date_from, datetime(2022, 1, 3, 13, 0), "Afternoon starts after lunch gap")
        self.assertEqual(afternoon.date_to, dt, "Afternoon output ends at original leave end")

    def test_day_leave_grants_allocation(self):
        """A day leave fires a rule that also grants a compensatory allocation.

        One 8h working-day leave with rate=1.0 should produce exactly 1 compensatory day.
        The calendar has 08:00-12:00 + 13:00-17:00 = 8 scheduled hours, so the leave must
        span the full wall-clock day (08:00-17:00, including the lunch gap) to capture all
        8 scheduled hours after the pipeline clips to work intervals.
        """
        self.time_rule.write({
            'leave_compensation_rate': 1.0,
            'allocation_type_id': self.comp_wet.id,
        })

        # full wall-clock day: 08:00-17:00 clips to 08:00-12:00 + 13:00-17:00 = 8 scheduled hours
        self._make_day_leave(
            datetime(2022, 1, 3, 8, 0),
            datetime(2022, 1, 3, 17, 0),
        )

        alloc = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee.id),
            ('work_entry_type_id', '=', self.comp_wet.id),
        ], limit=1)
        self.assertTrue(alloc, "A compensatory allocation must be created")
        self.assertAlmostEqual(
            alloc.number_of_days, 1.0, places=5,
            msg="Exactly 1 compensatory day should be granted for one working day",
        )

    def test_half_day_leave_reclassified_in_full(self):
        """A half-day leave is reclassified atomically — source archived, one output child created.

        The pipeline must treat the half-day as an atomic unit and not attempt
        any sub-day splitting.
        """
        half_day_wet = self.env['hr.work.entry.type'].create({
            'name': 'Test Half-Day Type',
            'code': 'TESTHALF',
            'request_unit': 'half_day',
            'requires_allocation': False,
            'count_as': 'absence',
        })
        out_wet = self.env['hr.work.entry.type'].create({
            'name': 'Reclassified Half-Day',
            'code': 'TESTHALF2',
            'request_unit': 'half_day',
            'requires_allocation': False,
            'count_as': 'absence',
        })
        self.env['hr.time.rule'].create({
            'name': 'Reclassify half-day leave',
            'condition_work_entry_type_ids': [(4, half_day_wet.id)],
            'work_entry_type_id': out_wet.id,
            'working_hours_mode': 'day',
            'expected_hours': 0.0,
        })

        # morning half-day: 8:00-12:00 = 4h
        df = datetime(2022, 1, 3, 8, 0)
        dt = datetime(2022, 1, 3, 12, 0)
        source = self._make_day_leave(df, dt, wet=half_day_wet)

        output = source.output_leave_ids
        self.assertEqual(len(output), 1, "One output child for the full half-day")
        self.assertEqual(output.work_entry_type_id, out_wet,
                         "Output WET must be the reclassified type")
        self.assertTrue(output.time_rule_id, "Output must reference the firing rule")
        self.assertAlmostEqual(
            (output.date_to - output.date_from).total_seconds() / 3600,
            4.0, places=5,
            msg="Full 4h half-day span must be reclassified; no sub-day splitting",
        )
        self.assertEqual(output.date_from, df, "Output date_from must match original")
        self.assertEqual(output.date_to, dt, "Output date_to must match original")

    def test_weekly_rule_multi_day_leave_no_duplicate_remainder(self):
        """A week-long leave cut by a weekly rule produces no duplicate remainder.

        Mon-Fri leave of 5 x 8h, the rule fires above 16h per week: Monday and Tuesday
        become remainder children, Wednesday to Friday become outputs. Monday and Tuesday
        are two segments (clipped to the schedule) both kept as remainder: no duplicate
        remainder may be created for Tuesday.
        """
        calendar = self.env['resource.calendar'].create({
            'name': '40h/week UTC continuous',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': 8, 'hour_to': 16})
                for wd in ['0', '1', '2', '3', '4']
            ],
        })
        self.employee.resource_calendar_id = calendar
        self.day_wet.request_unit = 'half_day'
        self.other_day_wet.request_unit = 'half_day'
        self.time_rule.write({
            'working_hours_mode': 'week',
            'expected_hours': 16.0,
        })
        source = self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_skip_date_check=True,
        ).create({
            'employee_id': self.employee.id,
            'work_entry_type_id': self.day_wet.id,
            'request_date_from': '2022-01-03',
            'request_date_to': '2022-01-07',
        })
        source.action_approve()

        self.assertFalse(source.active, "source is archived")
        children = self.env['hr.leave'].search([('source_leave_id', '=', source.id)])
        remainders = children.filtered(lambda l: not l.time_rule_id).sorted('date_from')
        outputs = children.filtered(lambda l: l.time_rule_id).sorted('date_from')
        self.assertEqual(len(remainders), 2, "Monday and Tuesday each get a remainder child")
        self.assertEqual(remainders.work_entry_type_id, self.day_wet)
        self.assertAlmostEqual(sum(remainders.mapped('number_of_hours')), 16.0)
        self.assertEqual(len(outputs), 3)
        self.assertEqual(outputs.work_entry_type_id, self.other_day_wet)
        self.assertEqual(outputs.mapped('date_from'), [
            datetime(2022, 1, 5, 8, 0), datetime(2022, 1, 6, 8, 0), datetime(2022, 1, 7, 8, 0),
        ])
        for output in outputs:
            self.assertAlmostEqual(output.number_of_hours, 8.0)
            self.assertAlmostEqual(output.number_of_days, 1.0)

    def test_output_duration_ignores_source_resource_leave(self):
        """The duration of a time rule output does not deduct the resource leave of its source.

        The outputs are created while the resource leave of the source still spans its original
        dates (it is only recreated afterwards), their duration must not depend on when it is
        computed.
        """
        self.time_rule.active = False
        source = self._make_day_leave(datetime(2022, 1, 3, 8, 0), datetime(2022, 1, 7, 17, 0))
        source._create_resource_leave()
        Leave = self.env['hr.leave'].sudo().with_context(**self.env['hr.leave']._time_rule_write_ctx)
        output = Leave.create(self.time_rule._get_output_leave_vals(
            self.employee, self.time_rule, datetime(2022, 1, 5, 8, 0), datetime(2022, 1, 5, 17, 0), source,
        ))
        self.assertAlmostEqual(output.number_of_hours, 8.0)
        self.assertAlmostEqual(output.number_of_days, 1.0)
