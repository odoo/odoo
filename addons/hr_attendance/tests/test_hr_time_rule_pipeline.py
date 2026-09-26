# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, date

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('time_rule_pipeline')
class TestTimeRulePipeline(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        att_type = cls.env.company._get_default_attendance_work_entry_type()

        ot_type = cls.env['hr.work.entry.type'].create({
            'name': 'Pipeline Test Overtime',
            'code': 'OT_PIPELINE_TEST',
        })

        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.rule = cls.env['hr.time.rule'].create({
            'name': 'Schedule Overtime (Pipeline Test)',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': ot_type.id,
            'condition_work_entry_type_ids': [(4, att_type.id)],
        })

        # employee with a schedule (default company calendar, Mon-Fri 8-17)
        cls.employee_scheduled = cls.env['hr.employee'].create({
            'name': 'Scheduled Employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'wage': 3000,
        })

        # employee with an undefined calendar -> expected = 0
        flex_calendar = cls.env['resource.calendar'].create({
            'name': 'Undefined Calendar',
            'calendar_type': 'undefined',
        })
        cls.employee_flex = cls.env['hr.employee'].create({
            'name': 'Flexible Employee',
            'tz': 'UTC',
            'resource_calendar_id': flex_calendar.id,
        })

    def test_cross_midnight_break_prorated_across_days(self):
        """Break duration is prorated proportionally to each day's share of the total span.

        Scenario: employee with no schedule works Jun 9 20:00 -> Jun 10 02:00 (6h total)
        with a 3h break.  The pipeline splits the attendance at midnight:
          day 1 (Jun 9): 4h -> prorated break = 4/6 x 3h = 2h -> 2h net overtime
          day 2 (Jun 10): 2h -> prorated break = 2/6 x 3h = 1h -> 1h net overtime

        After the pipeline the source record carries the day-1 share (2h break) and
        a new child record carries the day-2 share (1h break).
        """
        self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 9, 20, 0),
            'check_out': datetime(2026, 6, 10, 2, 0),
            'break_duration': 3.0,
        })

        all_records = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_flex.id),
            ('time_rule_id', '!=', False),
        ], order='check_in asc')

        self.assertEqual(len(all_records), 2, "pipeline must produce two overtime records (one per day)")

        day1, day2 = all_records

        # day 1: source clipped to midnight; prorated break = 4/6 * 3 = 2h
        self.assertAlmostEqual(
            day1.break_duration, 2.0, places=4,
            msg="day-1 break must be 2h (4/6 of the 3h total)",
        )
        self.assertAlmostEqual(
            day1.worked_hours, 2.0, places=4,
            msg="day-1 net work must be 2h (4h gross - 2h break)",
        )

        # day 2: child record for the post-midnight portion; prorated break = 2/6 * 3 = 1h
        self.assertAlmostEqual(
            day2.break_duration, 1.0, places=4,
            msg="day-2 break must be 1h (2/6 of the 3h total)",
        )
        self.assertAlmostEqual(
            day2.worked_hours, 1.0, places=4,
            msg="day-2 net work must be 1h (2h gross - 1h break)",
        )

        # total break conserved
        self.assertAlmostEqual(
            day1.break_duration + day2.break_duration, 3.0, places=4,
            msg="break_duration must be conserved across the two records",
        )

    def test_zero_break_produces_zero_breaks_on_split(self):
        self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 9, 20, 0),
            'check_out': datetime(2026, 6, 10, 2, 0),
            'break_duration': 0.0,
        })
        all_records = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_flex.id),
            ('time_rule_id', '!=', False),
        ], order='check_in asc')
        self.assertEqual(len(all_records), 2, "pipeline must produce two records (one per day)")
        for rec in all_records:
            self.assertAlmostEqual(
                rec.break_duration, 0.0, places=4,
                msg="zero source break must remain zero on every split record",
            )

    def test_three_day_span_break_conserved(self):
        """A 29-hour attendance spanning three days prorates its break cleanly across all pieces.

        Jun 8 22:00 -> Jun 10 03:00 (29h total), 2.9h break:
          day 1 (Jun 8,  2h):  2/29  x 2.9 = 0.2h
          day 2 (Jun 9, 24h): 24/29  x 2.9 = 2.4h
          day 3 (Jun 10, 3h):  3/29  x 2.9 = 0.3h
        Total: 2.9h conserved.

        Jun 8 is a Monday and Jun 10 a Wednesday, so the flex employee (no schedule,
        expected = 0 every day) generates one overtime record per calendar day.
        """
        self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 8, 22, 0),
            'check_out': datetime(2026, 6, 10, 3, 0),
            'break_duration': 2.9,
        })
        all_records = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_flex.id),
            ('time_rule_id', '!=', False),
        ], order='check_in asc')
        self.assertEqual(len(all_records), 3, "must produce three records (one per calendar day)")
        day1, day2, day3 = all_records
        # 2/29 x 2.9 = 0.2  exactly;  24/29 x 2.9 = 2.4  exactly;  3/29 x 2.9 = 0.3  exactly
        self.assertAlmostEqual(day1.break_duration, 0.2, places=4,
            msg="day-1 break: 2/29 x 2.9h = 0.2h")
        self.assertAlmostEqual(day2.break_duration, 2.4, places=4,
            msg="day-2 break: 24/29 x 2.9h = 2.4h")
        self.assertAlmostEqual(day3.break_duration, 0.3, places=4,
            msg="day-3 break: 3/29 x 2.9h = 0.3h")
        self.assertAlmostEqual(
            day1.break_duration + day2.break_duration + day3.break_duration,
            2.9, places=4,
            msg="total break must be conserved across all three records",
        )

    def test_partial_overtime_break_stays_on_source_else_branch(self):
        """
        Scheduled employee (Mon-Fri 8h/day) works 2026-06-09 (Tuesday) 08:00-19:00
        (11h gross) with a 1h break.  Net attended = 10h, scheduled = 8h, excess = 2h.

        The pipeline clips the source to 08:00-17:00 (9h gross) and creates an overtime
        record at 17:00-19:00 (2h gross).  Because the source is a single-day record the
        break stays entirely on the source:

          source   1h break  -> 9h gross - 1h = 8h net
          overtime 0h break  -> 2h gross - 0h = 2h net
          total:   1h break, 10h gross conserved.

        The else branch is the code path where min_out_start_utc > src_start_utc (i.e. the
        overtime portion does not reach back to the beginning of the attendance).
        """
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 9, 8, 0),
            'check_out': datetime(2026, 6, 9, 19, 0),
            'break_duration': 1.0,
        })
        overtime_records = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_scheduled.id),
            ('time_rule_id', '!=', False),
        ], order='check_in asc')
        self.assertEqual(len(overtime_records), 1, "one overtime record for the 2h excess tail")
        ot = overtime_records[0]

        # source record boundaries (clipped at the overtime start)
        self.assertEqual(att.check_in, datetime(2026, 6, 9, 8, 0),
            msg="source check_in must not change")
        self.assertEqual(att.check_out, datetime(2026, 6, 9, 17, 0),
            msg="source check_out must be clipped to the overtime start")

        # overtime record boundaries
        self.assertEqual(ot.check_in, datetime(2026, 6, 9, 17, 0),
            msg="overtime check_in must be the overtime start")
        self.assertEqual(ot.check_out, datetime(2026, 6, 9, 19, 0),
            msg="overtime check_out must be the attendance end")

        # break stays entirely on the source (single day attendance)
        self.assertAlmostEqual(att.break_duration, 1.0, places=4,
            msg="source keeps the full break (single-day: break is in the regular portion)")
        self.assertAlmostEqual(ot.break_duration, 0.0, places=4,
            msg="overtime record carries no break (tail overtime, no break expected there)")
        self.assertAlmostEqual(att.break_duration + ot.break_duration, 1.0, places=4,
            msg="total break must be conserved")

        self.assertAlmostEqual(att.worked_hours, 8.0, places=4,
            msg="source net work = 9h gross - 1h break = 8h")
        self.assertAlmostEqual(ot.worked_hours, 2.0, places=4,
            msg="overtime net work = 2h gross - 0h break = 2h")

    def test_single_day_two_rules_break_stays_on_source(self):
        """Two rules on a single-day attendance: break stays entirely on the source record.

        Scheduled employee Jun 9 08:00-22:00 (14h gross), break=1h, net=13h, schedule=8h.
        Rule 1 (cls.rule): excess 5h net -> OT1 [17:00-22:00].
        Rule 2 (expected=3h of OT1/day -> OT2): further splits the OT1 tail into OT1 + OT2.

        Because the source is a single-day record the break belongs entirely to the regular
        portion [08:00-17:00].  Both output records — regardless of which rule produced them —
        carry no break.  Total break 1h is conserved on the source.
        """
        ot2_type = self.env['hr.work.entry.type'].create({
            'name': 'High Overtime (Pipeline Test)',
            'code': 'OT2_PIPELINE_TEST',
        })
        self.env['hr.time.rule'].create({
            'name': 'High Overtime Rule (Pipeline Test)',
            'calendar_source': False,
            'quantity_period': 'day',
            'expected_hours': 3.0,
            'work_entry_type_id': ot2_type.id,
            'condition_work_entry_type_ids': [(4, self.rule.work_entry_type_id.id)],
            'sequence': 20,
        })
        att = self.env['hr.attendance'].create({
            'employee_id': self.employee_scheduled.id,
            'check_in': datetime(2026, 6, 9, 8, 0),
            'check_out': datetime(2026, 6, 9, 22, 0),
            'break_duration': 1.0,
        })
        output_records = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_scheduled.id),
            ('time_rule_id', '!=', False),
        ], order='check_in asc')
        self.assertEqual(len(output_records), 2, "one OT1 record and one OT2 record")

        # source clipped at overtime start, full break retained (single-day else branch)
        self.assertEqual(att.check_in, datetime(2026, 6, 9, 8, 0),
            msg="source check_in must not change")
        self.assertEqual(att.check_out, datetime(2026, 6, 9, 17, 0),
            msg="source check_out clipped at the start of overtime")
        self.assertAlmostEqual(att.break_duration, 1.0, places=4,
            msg="source keeps the full break (single-day: break is in the regular portion)")

        # both output records carry no break regardless of which rule produced them
        for rec in output_records:
            self.assertAlmostEqual(rec.break_duration, 0.0, places=4,
                msg=f"output {rec.check_in}-{rec.check_out} must carry no break")

        self.assertAlmostEqual(
            att.break_duration + sum(r.break_duration for r in output_records),
            1.0, places=4,
            msg="total break must be conserved",
        )

    def test_multiday_two_rules_break_prorated_across_all_slices(self):
        """Two rules on a cross-midnight attendance: break prorated across all four slices.

        Flex employee Jun 9 20:00 -> Jun 10 04:00 (8h gross), break=2h.
        Rule 1 (cls.rule): all hours overtime from start -> in-place branch, two OT1 slices
          (one per calendar day).
        Rule 2 (expected=2h net of OT1/day -> OT2): further splits each day's OT1 tail.
          Within each 4h OT1 slice, prorated break = 4/8x2=1h -> effective=3h, threshold=2h,
          excess=1h -> OT2 is the last net-1h of each slice.

        Because the source spans two calendar days, the in-place branch is used and break
        is prorated proportionally across all four resulting records:
          OT1 day1 (≈3h gross) -> break ≈ 3/8x2 = 0.75h
          OT2 day1 (≈1h gross) -> break ≈ 1/8x2 = 0.25h
          OT1 day2   (3h gross) -> break   = 3/8x2 = 0.75h
          OT2 day2   (1h gross) -> break   = 1/8x2 = 0.25h
          total: 2h conserved.
        """
        ot2_type = self.env['hr.work.entry.type'].create({
            'name': 'High Overtime (Pipeline Test)',
            'code': 'OT2_PIPELINE_TEST',
        })
        self.env['hr.time.rule'].create({
            'name': 'High Overtime Rule (Pipeline Test)',
            'calendar_source': False,
            'quantity_period': 'day',
            'expected_hours': 2.0,
            'work_entry_type_id': ot2_type.id,
            'condition_work_entry_type_ids': [(4, self.rule.work_entry_type_id.id)],
            'sequence': 20,
        })
        self.env['hr.attendance'].create({
            'employee_id': self.employee_flex.id,
            'check_in': datetime(2026, 6, 9, 20, 0),
            'check_out': datetime(2026, 6, 10, 4, 0),
            'break_duration': 2.0,
        })
        all_records = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_flex.id),
            ('time_rule_id', '!=', False),
        ], order='check_in asc')
        self.assertEqual(len(all_records), 4,
            "four slices: OT1 day1, OT2 day1, OT1 day2, OT2 day2")
        ot1_d1, ot2_d1, ot1_d2, ot2_d2 = all_records

        # clean boundaries (not adjacent to midnight)
        self.assertEqual(ot1_d1.check_in, datetime(2026, 6, 9, 20, 0),
            msg="OT1 day1 must start at attendance check_in")
        self.assertEqual(ot1_d2.check_out, datetime(2026, 6, 10, 3, 0),
            msg="OT1 day2 must end where OT2 day2 starts")
        self.assertEqual(ot2_d2.check_in, datetime(2026, 6, 10, 3, 0),
            msg="OT2 day2 must start 1h before attendance check_out")
        self.assertEqual(ot2_d2.check_out, datetime(2026, 6, 10, 4, 0),
            msg="OT2 day2 must end at attendance check_out")

        # prorated breaks: each slice's gross share of the 8h span x 2h original break.
        # day1 boundary sits at 22:59:59.999999 (datetime.max.time() effect), so ≈ not ==.
        self.assertAlmostEqual(ot1_d1.break_duration, 0.75, places=4,
            msg="OT1 day1: ≈3/8 x 2h")
        self.assertAlmostEqual(ot2_d1.break_duration, 0.25, places=4,
            msg="OT2 day1: ≈1/8 x 2h")
        self.assertAlmostEqual(ot1_d2.break_duration, 0.75, places=4,
            msg="OT1 day2: 3/8 x 2h")
        self.assertAlmostEqual(ot2_d2.break_duration, 0.25, places=4,
            msg="OT2 day2: 1/8 x 2h")
        self.assertAlmostEqual(
            sum(r.break_duration for r in all_records), 2.0, places=4,
            msg="total break must be conserved across all four slices",
        )
