# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('-at_install', 'post_install', 'work_entry_pipeline', 'time_rule_pipeline')
class TestTimeRuleAllocationLog(TransactionCase):
    """Allocation log creation, source routing, and reversal for attendance-side rules."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.country_id = cls.env.ref('base.us')
        cls.calendar = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env.company.resource_calendar_id = cls.calendar
        # the time rules see the attendances as Work
        cls.att_type = cls.env.ref('hr_work_entry.generic_work_entry_type_attendance')
        cls.overtime_type = cls.env.ref('hr_work_entry.be_work_entry_type_overtime')

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
            'work_entry_source': 'attendance',
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
        """Whole attendance is excess: the output time off covers it -> log must reference the source att."""
        self._make_rule()
        # Saturday: 0h scheduled -> all 4h excess
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        att.invalidate_recordset()

        output = att.related_leave_ids
        self.assertEqual((output.date_from, output.date_to), (att.check_in, att.check_out),
                         "The output time off covers the whole attendance")

        logs = self._logs()
        self.assertEqual(len(logs), 1, "Exactly one log entry expected")
        self.assertEqual(logs.res_model, 'hr.attendance')
        self.assertEqual(logs.res_id, att.id,
                         "Log source must point to the source attendance")
        self.assertAlmostEqual(logs.days, 0.5, places=5,
                               msg="4h * 100% / 8h = 0.5 days")

    def test_log_source_subsequent_output(self):
        """Output over part of the attendance: the log references the source attendance, not the output."""
        self._make_rule()
        # Monday 08:00-19:00: schedule is 08:00-17:00 (8h) -> engine sees 11h worked, 8h expected,
        # 3h excess (lunch gap 12:00-13:00 + post-17:00 both counted as excess).
        # The output time off is 16:00-19:00, the attendance is unchanged.
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 19))
        att.invalidate_recordset()

        outputs = att.related_leave_ids
        self.assertEqual(len(outputs), 1, "Subsequent case must produce one output (prerequisite)")

        logs = self._logs()
        self.assertEqual(len(logs), 1, "Exactly one log entry expected")
        self.assertEqual(logs.res_model, 'hr.attendance')
        self.assertEqual(logs.res_id, att.id,
                         "Log source must point to the source attendance, not the output")
        self.assertAlmostEqual(logs.days, 3 / 8, places=5,
                               msg="3h excess (11h worked - 8h expected) * 100% / 8h = 0.375 days")

    def test_log_source_pponly(self):
        """PP-only rule (no output WET): no output time off created -> log references the source."""
        self._make_rule(work_entry_type_id=False)
        # Saturday: 0h scheduled -> 4h excess, all pp-only (no output)
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        att.invalidate_recordset()
        self.assertFalse(att.related_leave_ids, "PP-only must not create output time off")

        logs = self._logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs.res_id, att.id,
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
        self.assertEqual(log_r1.res_model, 'hr.attendance')
        self.assertEqual(log_r1.res_id, att.id,
                         "Acc-displaced credit must log against the SOURCE, not any output")
        self.assertAlmostEqual(log_r1.days, 0.5, places=5,
                               msg="4h * 100% / 8h = 0.5 days for acc-displaced R1")
        r1.unlink()
        r2.unlink()

    # reversal on source delete
    def test_source_unlink_inplace_reverses_allocation(self):
        """Deleting an attendance whose whole span is excess reverses its credit."""
        self._make_rule()
        # Saturday: all excess -> log against source
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, 0.5, places=5,
                               msg="0.5d allocated before delete")

        att.unlink()

        alloc.invalidate_recordset()
        self.assertAlmostEqual(alloc.number_of_days, 0.0, places=5,
                               msg="Deleting in-place source must reverse its allocation credit")

    def test_source_unlink_reverses_output_credit(self):
        """Deleting the SOURCE deletes its outputs and reverses their credits (the log is against the source)."""
        self._make_rule()
        # Monday 08:00-19:00 -> 3h excess (11h worked - 8h expected), output time off created
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 19))
        att.invalidate_recordset()
        child = att.related_leave_ids
        self.assertEqual(len(child), 1, "Prerequisite")

        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, 3 / 8, places=5)

        att.unlink()

        alloc.invalidate_recordset()
        self.assertFalse(child.exists(), "The output time off follows the attendance")
        self.assertAlmostEqual(
            alloc.number_of_days, 0.0, places=5,
            msg="The credit must be reversed with the source deletion",
        )
        self.assertFalse(self._logs(), "Log entries must be cleaned up after reversal")

    # reversal on source write
    def test_source_write_reverses_inplace_credit(self):
        self._make_rule()
        # Saturday: all 4h is overtime. Log is against the source; source credit = 0.5d.
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, 0.5, places=5,
                               msg="Before write: 4h * 1.0 / 8h = 0.5d")

        # shorten check_out: source credit reversed, then credited again for the 2h left
        att.write({'check_out': datetime(2022, 12, 10, 10)})

        alloc.invalidate_recordset()
        self.assertAlmostEqual(
            alloc.number_of_days, 0.25, places=5,
            msg="After write: 2h * 1.0 / 8h = 0.25d, the previous credit is reversed",
        )

    def test_employee_break_edit_reverses_credit(self):
        """An employee who changes the break of their reviewed attendance sends it back to To Review, so its credit
        is reversed until a manager reviews it again."""
        self._make_rule()
        self.emp.user_id = new_test_user(
            self.env, login='log_employee', groups='base.group_user,hr_attendance.group_hr_attendance_own',
        )
        att = self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        alloc = self._alloc()
        self.assertAlmostEqual(alloc.number_of_days, 0.5, places=5)
        # the attendance holds the credit
        att.with_user(self.emp.user_id).write({'break_duration': 1})

        self.assertEqual(att.state, 'draft')
        alloc.invalidate_recordset()
        self.assertAlmostEqual(alloc.number_of_days, 0.0, places=5)

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
        # 4h + 8h excess -> 0.5d + 1.0d = 1.5d total
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

    def test_second_attendance_same_day_keeps_previous_credit(self):
        """a second attendance on the same day must add to the existing credit, not replace it."""
        self._make_rule()
        # saturday: no schedule, all time worked is excess
        self._make_att(datetime(2022, 12, 10, 8), datetime(2022, 12, 10, 12))
        self.assertAlmostEqual(self._alloc().number_of_days, 0.5, places=5,
                               msg="4h excess / 8h = 0.5d")
        self._make_att(datetime(2022, 12, 10, 13), datetime(2022, 12, 10, 15))
        alloc = self._alloc()
        alloc.invalidate_recordset()
        self.assertAlmostEqual(alloc.number_of_days, 0.75, places=5,
                               msg="(4h + 2h) excess / 8h = 0.75d, not 0.25d")

    def _make_deficit_rule(self, undertime_type, **kw):
        defaults = {
            'name': 'Undertime Rule',
            'threshold_operator': 'less_than',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': undertime_type.id,
            'condition_work_entry_type_ids': [self.att_type.id],
            'leave_compensation_rate': 1.0,
            'allocation_type_id': self.comp_type.id,
        }
        defaults.update(kw)
        return self.env['hr.time.rule'].create(defaults)

    def _make_deficit_allocation(self, days=2.0):
        alloc = self.env['hr.leave.allocation'].sudo().create({
            'employee_id': self.emp.id,
            'work_entry_type_id': self.comp_type.id,
            'number_of_days': days,
            'date_to': False,
        })
        return alloc

    def test_deficit_output_log_keyed_to_source_attendance(self):
        undertime_type = self.env['hr.work.entry.type'].create({
            'name': 'Undertime', 'code': 'ULMLOG',
            'requires_allocation': False,
        })
        self._make_deficit_rule(undertime_type)
        alloc = self._make_deficit_allocation(days=2.0)

        # Monday 08:00-14:00 (6h worked, 8h expected) -> 2h deficit
        # output attendance created for the missing 2h slot; allocation deducted 2/8 = 0.25d
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
        att.invalidate_recordset()

        output = att.related_leave_ids
        self.assertEqual(len(output), 1, "Deficit rule must create one output time off")

        logs = self.env['hr.time.rule.allocation.log'].sudo().search([
            ('allocation_id', '=', alloc.id),
        ])
        self.assertEqual(len(logs), 1, "Exactly one log entry for the deficit output")
        self.assertEqual(logs.res_model, 'hr.attendance')
        self.assertEqual(logs.res_id, att.id,
                         "Deficit log source must point to the source attendance")
        self.assertAlmostEqual(logs.days, -2 / 8, places=5,
                               msg="2h deficit * 100% / 8h = -0.25 days (deduction)")

    def test_deficit_source_unlink_restores_allocation(self):
        undertime_type = self.env['hr.work.entry.type'].create({
            'name': 'Undertime', 'code': 'ULMREV',
            'requires_allocation': False,
        })
        self._make_deficit_rule(undertime_type)
        alloc = self._make_deficit_allocation(days=2.0)
        days_before = alloc.number_of_days  # 2.0

        # Monday 08:00-14:00 (6h worked, 8h expected) -> 2h deficit -> 0.25d deducted
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
        att.invalidate_recordset()

        output = att.related_leave_ids
        self.assertEqual(len(output), 1, "Prerequisite: deficit output must be created")

        alloc.invalidate_recordset()
        self.assertAlmostEqual(alloc.number_of_days, days_before - 2 / 8, places=5,
                               msg="Allocation must be reduced by 0.25d after deficit output creation")

        # delete the source attendance (it deletes the output) -> allocation must be restored
        att.unlink()

        alloc.invalidate_recordset()
        self.assertFalse(output.exists())
        self.assertAlmostEqual(alloc.number_of_days, days_before, places=5,
                               msg="Deleting the source of the deficit output must restore the deducted days")
        logs = self.env['hr.time.rule.allocation.log'].sudo().search([
            ('allocation_id', '=', alloc.id),
        ])
        self.assertFalse(logs, "Log entry must be removed after reversal")
