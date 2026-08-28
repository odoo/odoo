# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('-at_install', 'post_install', 'work_entry_pipeline')
class TestTimeRuleAllocationLog(TransactionCase):
    """Allocation log creation, source routing, and reversal for attendance-side rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.calendar = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env.company.resource_calendar_id = cls.calendar
        cls.att_type = cls.env.company._get_default_attendance_work_entry_type()
        cls.env.company.attendance_work_entry_type_id = cls.att_type
        cls.overtime_type = cls.env.ref('hr_work_entry.generic_work_entry_type_overtime')

        cls.env['hr.time.rule'].search([]).write({'active': False})

        # compensatory leave type used across tests
        cls.comp_type = cls.env['hr.work.entry.type'].create({
            'name': 'Compensatory Rest',
            'code': 'COMPLOG',
            'requires_allocation': True,
            'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })

        cls.emp = cls.env['hr.employee'].create({
            'name': 'Log Employee',
            'tz': 'UTC',
            'attendance_based': False,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3000,
            'resource_calendar_id': cls.calendar.id,
        })

    # helpers
    def _make_rule(self, **kw):
        defaults = {
            'name': 'Test Rule',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': self.overtime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
            'leave_compensation_rate': 1.0,
            'allocation_type_id': self.comp_type.id,
        }
        defaults.update(kw)
        return self.env['hr.time.rule'].create(defaults)

    def _make_att(self, check_in, check_out):
        return self.env['hr.attendance'].create({
            'employee_id': self.emp.id,
            'check_in': check_in,
            'check_out': check_out,
        })

    def _alloc(self):
        return self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.emp.id),
            ('work_entry_type_id', '=', self.comp_type.id),
        ])

    def _logs(self):
        return self.env['hr.time.rule.allocation.log'].sudo().search([
            ('allocation_id', 'in', self._alloc().ids),
        ])

    # log source routing
    def test_log_source_inplace(self):
        """In-place case: source IS the overtime record -> log must reference the source att."""
        self._make_rule()
        # Saturday: 0h scheduled -> all 4h excess -> in-place (source becomes OT record)
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        att.invalidate_recordset()

        # no child output: source was repurposed in-place
        self.assertFalse(att.overtime_attendance_ids,
                         "In-place scenario must not produce child output records")

        logs = self._logs()
        self.assertEqual(len(logs), 1, "Exactly one log entry expected")
        self.assertEqual(logs.source_model, 'hr.attendance')
        self.assertEqual(logs.source_id, att.id,
                         "Log source must point to the (in-place) source record itself")
        self.assertAlmostEqual(logs.days, 0.5, places=5,
                               msg="4h * 100% / 8h = 0.5 days")

    def test_log_source_subsequent_output(self):
        """Subsequent-output case: child att created -> log must reference the OUTPUT child, not source."""
        self._make_rule()
        # Monday 08:00-19:00: schedule is 08:00-17:00 (8h) -> engine sees 11h worked, 8h expected,
        # 3h excess (lunch gap 12:00-13:00 + post-17:00 both counted as excess).
        # Child att created for the excess portion; source trimmed to scheduled span.
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 19))
        att.invalidate_recordset()

        children = att.overtime_attendance_ids
        self.assertEqual(len(children), 1, "Subsequent case must produce one child output (prerequisite)")

        logs = self._logs()
        self.assertEqual(len(logs), 1, "Exactly one log entry expected")
        self.assertEqual(logs.source_model, 'hr.attendance')
        self.assertEqual(logs.source_id, children.id,
                         "Log source must point to the OUTPUT child, not the source att")
        self.assertAlmostEqual(logs.days, 3 / 8, places=5,
                               msg="3h excess (11h worked - 8h expected) * 100% / 8h = 0.375 days")

    def test_log_source_pponly(self):
        """PP-only rule (no output WET): no child att created -> log references the source."""
        self._make_rule(work_entry_type_id=False)
        # Saturday: 0h scheduled -> 4h excess, all pp-only (source annotated, no child)
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        att.invalidate_recordset()
        self.assertFalse(att.overtime_attendance_ids, "PP-only must not create child records")

        logs = self._logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.source_id, att.id,
                         "PP-only log source must be the source attendance")

    def test_log_source_acc_displaced(self):
        """Acc-displaced credit: R1 tagged by R2 -> R1's credit log references the SOURCE."""
        # R1: allocate-only (no WET), Saturday, no threshold -> tags all Saturday time
        # R2: output WET, Saturday -> displaces R1 (R1 goes to acc)
        alloc_r1 = self.env['hr.work.entry.type'].create({
            'name': 'Acc R1', 'code': 'ACCR1',
            'requires_allocation': True, 'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        ot_r2 = self.env['hr.work.entry.type'].create({
            'name': 'OT R2', 'code': 'OTR2LOG',
            'requires_allocation': False,
            'request_unit': 'hour',   # must match condition WET's unit (att_type is 'hour')
        })

        r1 = self.env['hr.time.rule'].create({
            'name': 'R1 Acc Alloc', 'sequence': 10,
            'work_entry_type_id': False,
            'leave_compensation_rate': 1.0, 'allocation_type_id': alloc_r1.id,
            'condition_work_entry_type_ids': [self.att_type.id],
            'apply_monday': False, 'apply_tuesday': False, 'apply_wednesday': False,
            'apply_thursday': False, 'apply_friday': False,
            'apply_saturday': True, 'apply_sunday': False,
        })
        r2 = self.env['hr.time.rule'].create({
            'name': 'R2 OT', 'sequence': 20,
            'work_entry_type_id': ot_r2.id,
            'leave_compensation_rate': 0.0,
            'condition_work_entry_type_ids': [self.att_type.id],
            'apply_monday': False, 'apply_tuesday': False, 'apply_wednesday': False,
            'apply_thursday': False, 'apply_friday': False,
            'apply_saturday': True, 'apply_sunday': False,
        })

        # Saturday 4h: R1 tags first, R2 displaces R1 -> R1 enters acc
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        att.invalidate_recordset()

        log_r1 = self.env['hr.time.rule.allocation.log'].sudo().search([
            ('allocation_id.work_entry_type_id', '=', alloc_r1.id),
        ])
        self.assertEqual(len(log_r1), 1, "R1 acc credit must produce one log entry")
        self.assertEqual(log_r1.source_model, 'hr.attendance')
        self.assertEqual(log_r1.source_id, att.id,
                         "Acc-displaced credit must log against the SOURCE, not any output")
        self.assertAlmostEqual(log_r1.days, 0.5, places=5,
                               msg="4h * 100% / 8h = 0.5 days for acc-displaced R1")
        r1.unlink()
        r2.unlink()

    # reversal on output delete
    def test_output_unlink_reverses_allocation(self):
        """Deleting the output attendance child reverses its credited allocation days."""
        self._make_rule()
        # Monday 08:00-19:00 -> 3h excess (11h worked - 8h expected), child output created
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 19))
        att.invalidate_recordset()
        child = att.overtime_attendance_ids
        self.assertEqual(len(child), 1, "Prerequisite: subsequent output child must exist")

        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, 3 / 8, places=5,
                               msg="3h * 100% / 8h = 0.375d allocated before delete")

        child.unlink()

        alloc.invalidate_recordset()
        self.assertAlmostEqual(alloc.number_of_days, 0.0, places=5,
                               msg="Deleting the output child must reverse its allocation credit")
        self.assertFalse(self._logs(), "Log entries must be cleaned up after reversal")

    # reversal on source delete
    def test_source_unlink_inplace_reverses_allocation(self):
        """Deleting an in-place source (log against source) reverses its credit."""
        self._make_rule()
        # Saturday: in-place -> log against source
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, 0.5, places=5,
                               msg="0.5d allocated before delete")

        att.unlink()

        alloc.invalidate_recordset()
        self.assertAlmostEqual(alloc.number_of_days, 0.0, places=5,
                               msg="Deleting in-place source must reverse its allocation credit")

    def test_source_unlink_does_not_reverse_output_logged_credit(self):
        """Deleting the SOURCE leaves output-logged credits intact (outputs remain valid).

        Design choice: when a source is deleted without cascading output deletion,
        the output records are still valid overtime records. Their allocation credits stay.
        """
        self._make_rule()
        # Monday 08:00-19:00 -> 3h excess (11h worked - 8h expected), child output created
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 19))
        att.invalidate_recordset()
        child = att.overtime_attendance_ids
        self.assertEqual(len(child), 1, "Prerequisite")

        expected_days = 3 / 8
        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, expected_days, places=5)

        # delete source (NOT output); output and its credit should survive
        att.with_context(skip_time_rules=True).unlink()

        alloc.invalidate_recordset()
        self.assertAlmostEqual(
            alloc.number_of_days, expected_days, places=5,
            msg="Output-logged credit must survive source deletion (output record still valid)",
        )
        self.assertTrue(self._logs(), "Log entry for output must still exist")

    # reversal on source write
    def test_source_write_reverses_inplace_credit(self):
        self._make_rule()
        # Saturday (in-place case): all 4h is overtime, no output children created.
        # Log is against the source itself; source credit = 0.5d.
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, 0.5, places=5,
                               msg="Before write: 4h * 1.0 / 8h = 0.5d")
        self.assertFalse(att.overtime_attendance_ids,
                         "In-place case: no output children exist")

        # shorten check_out: source credit reversed -> allocation drops to 0
        att.write({'check_out': datetime(2022, 12, 10, 10)})

        alloc.invalidate_recordset()
        self.assertAlmostEqual(
            alloc.number_of_days, 0.0, places=5,
            msg="After write: source credit reversed; engine skips (WET mismatch) -> 0d",
        )

    def test_source_write_no_change_when_non_time_field(self):
        """Writing a non-time field must NOT trigger reversal (allocation stays)."""
        self._make_rule()
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        alloc = self._alloc()
        days_before = alloc.number_of_days

        # write a non-time field
        att.write({'in_mode': 'kiosk'})

        alloc.invalidate_recordset()
        self.assertAlmostEqual(
            alloc.number_of_days, days_before, places=5,
            msg="Non-time-field write must not trigger reversal",
        )

    # multi-source selective reversal
    def test_two_sources_independent_reversal(self):
        """Two Saturday attendances both credit the same allocation; deleting one reverses only its share."""
        self._make_rule()
        att1 = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))   # 4h Sat
        self._make_att(datetime(2022, 12, 17, 8), datetime(2022, 12, 17, 16))  # 8h next Sat

        alloc = self._alloc()
        # 4h + 8h excess, all in-place -> 0.5d + 1.0d = 1.5d total
        self.assertAlmostEqual(alloc.number_of_days, 1.5, places=5,
                               msg="Both attendances must credit the same allocation")

        logs = self._logs()
        self.assertEqual(len(logs), 2, "One log entry per source attendance")

        att1.unlink()

        alloc.invalidate_recordset()
        self.assertAlmostEqual(
            alloc.number_of_days, 1.0, places=5,
            msg="Only att1's 0.5d must be reversed; att2's 1.0d stays",
        )

    # leave-source reversal
    def test_leave_source_refuse_reverses_allocation(self):
        """Refusing a source leave that had triggered allocation credits must reverse those credits."""
        leave_type = self.env['hr.work.entry.type'].create({
            'name': 'On Call', 'code': 'ONCALL',
            'time_off_selectable': True, 'requires_allocation': False,
            'leave_validation_type': 'no_validation',
        })
        leave_alloc_type = self.env['hr.work.entry.type'].create({
            'name': 'On Call Comp', 'code': 'ONCCMP',
            'requires_allocation': True, 'time_off_selectable': True,
            'leave_validation_type': 'no_validation',
        })
        # rule: when an on-call leave is created, allocate 100% compensation
        on_call_rule = self.env['hr.time.rule'].create({
            'name': 'On Call Compensation',
            'work_entry_type_id': False,
            'leave_compensation_rate': 1.0,
            'allocation_type_id': leave_alloc_type.id,
            'condition_work_entry_type_ids': [leave_type.id],
        })

        leave = self.env['hr.leave'].with_context(leave_fast_create=True, leave_skip_state_check=True).create({
            'employee_id': self.emp.id,
            'work_entry_type_id': leave_type.id,
            'date_from': datetime(2022, 12, 12, 8),
            'date_to': datetime(2022, 12, 12, 12),
            'state': 'validate',
        })

        alloc = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.emp.id),
            ('work_entry_type_id', '=', leave_alloc_type.id),
        ])
        self.assertEqual(len(alloc), 1, "Allocation must be created after leave validation")
        days_before = alloc.number_of_days
        self.assertGreater(days_before, 0, "Allocation must have days > 0")

        leave.action_refuse()

        alloc.invalidate_recordset()
        self.assertAlmostEqual(
            alloc.number_of_days, 0.0, places=5,
            msg="Refusing the source leave must reverse the allocation credit",
        )
        on_call_rule.unlink()

    # reversal blocked when it would go negative
    def test_reversal_blocked_when_would_go_negative(self):
        """reversal that would push virtual remaining below the floor raises validationerror."""
        self._make_rule()
        # most recent saturday: no schedule -> all 8h are excess -> engine credits 1.0d (8h)
        today = datetime.now().date()
        last_sat = today - timedelta(days=(today.weekday() + 2) % 7)
        att = self._make_att(datetime.combine(last_sat, datetime.min.time().replace(hour=8)),
                             datetime.combine(last_sat, datetime.min.time().replace(hour=16)))
        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, 1.0, places=5)

        # allocation date_from defaults to today
        alloc.date_from = '2020-01-01'
        last_friday = last_sat - timedelta(days=1)
        self.env['hr.leave'].sudo().with_context(leave_fast_create=True, leave_skip_state_check=True).create({
            'employee_id': self.emp.id,
            'work_entry_type_id': self.comp_type.id,
            'request_date_from': last_friday,
            'request_date_to': last_friday,
            'state': 'validate',
        })

        # unlink att -> tries to reverse 1.0d; virtual_remaining = 0 - 1.0 = -1.0 < 0 -> blocked
        with self.assertRaises(ValidationError):
            att.unlink()

        alloc.invalidate_recordset()
        self.assertAlmostEqual(alloc.number_of_days, 1.0, places=5,
                               msg="allocation unchanged after blocked reversal")
        self.assertTrue(self._logs(), "log entry must still exist after blocked reversal")
