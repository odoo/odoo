# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, freeze_time


@tagged('-at_install', 'post_install', 'time_rule_pipeline', 'regenerate_wizard')
class TestRegenerateWizard(TransactionCase):
    """Tests for hr.time.rule.regenerate.wizard

    Wizard semantics:
    - line_ids after action_find = active records (outputs or fresh candidates)
    - is_output=True -> active output produced by the rule (has source_*_id set)
    - is_output=False -> active virgin candidate with no output yet
    - After action_restore: line_ids = restored original sources (were archived now active)
    - removed_line_ids = what was deleted during restore
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['hr.time.rule'].search([]).write({'active': False})

        cls.att_type = cls.env.company._get_default_attendance_work_entry_type()
        cls.env.company.attendance_work_entry_type_id = cls.att_type
        cls.ot_type = cls.env.ref('hr_work_entry.generic_work_entry_type_overtime')

        cls.calendar = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [
                (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                for wd in ['0', '1', '2', '3', '4']
                for h in [8, 13]
            ],
        })
        cls.env.company.resource_calendar_id = cls.calendar

        cls.att_rule = cls.env['hr.time.rule'].create({
            'name': 'Attendance OT Rule',
            'calendar_source': 'employee',
            'quantity_period': 'day',
            'work_entry_type_id': cls.ot_type.id,
            'condition_work_entry_type_ids': [cls.att_type.id],
        })

        cls.leave_excess_src_type = cls.env['hr.work.entry.type'].create({
            'name': 'Leave Excess Src Regen', 'code': 'LESRG',
            'count_as': 'absence', 'requires_allocation': False,
            'time_off_selectable': False, 'request_unit': 'hour',
        })
        cls.leave_out_type = cls.env['hr.work.entry.type'].create({
            'name': 'Leave Out Regen', 'code': 'LORG',
            'count_as': 'absence', 'requires_allocation': False,
            'time_off_selectable': False, 'request_unit': 'hour',
        })
        cls.leave_excess_rule = cls.env['hr.time.rule'].create({
            'name': 'Leave Excess Rule',
            'working_hours_mode': 'day',
            'threshold_operator': 'exceed',
            'expected_hours': 4.0,
            'work_entry_type_id': cls.leave_out_type.id,
            'condition_work_entry_type_ids': [cls.leave_excess_src_type.id],
        })

        # deficit leave rule - uses a separate source type to avoid cross-firing with excess rule
        cls.leave_deficit_src_type = cls.env['hr.work.entry.type'].create({
            'name': 'Leave Deficit Src Regen', 'code': 'LDSRG',
            'count_as': 'absence', 'requires_allocation': False,
            'time_off_selectable': False, 'request_unit': 'hour',
        })
        cls.deficit_out_type = cls.env['hr.work.entry.type'].create({
            'name': 'Under Time Regen', 'code': 'UTRG',
            'count_as': 'absence', 'requires_allocation': False,
            'time_off_selectable': False, 'request_unit': 'hour',
        })
        cls.deficit_rule = cls.env['hr.time.rule'].create({
            'name': 'Leave Deficit Rule',
            'working_hours_mode': 'day',
            'threshold_operator': 'less_than',
            'expected_hours': 8.0,
            'work_entry_type_id': cls.deficit_out_type.id,
            'condition_work_entry_type_ids': [cls.leave_deficit_src_type.id],
        })

        # legacy alias used in a few generic tests that don't care which src type
        cls.leave_src_type = cls.leave_excess_src_type

        cls.emp = cls.env['hr.employee'].create({
            'name': 'Regen Emp',
            'tz': 'UTC',
            'attendance_based': False,
            'resource_calendar_id': cls.calendar.id,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3500,
        })
        cls.emp2 = cls.env['hr.employee'].create({
            'name': 'Regen Emp2',
            'tz': 'UTC',
            'attendance_based': False,
            'resource_calendar_id': cls.calendar.id,
            'date_version': '2020-01-01',
            'contract_date_start': '2020-01-01',
            'wage': 3500,
        })

    # helpers

    def _make_att(self, check_in, check_out, emp=None):
        return self.env['hr.attendance'].create({
            'employee_id': (emp or self.emp).id,
            'check_in': check_in,
            'check_out': check_out,
        })

    def _make_leave(self, date_from_dt, date_to_dt, wet=None, emp=None, skip_rules=False):
        ctx = dict(
            leave_fast_create=True,
            leave_skip_date_from_to_computation=True,
            leave_skip_state_check=True,
        )
        if skip_rules:
            ctx['skip_time_rules'] = True
        leave = self.env['hr.leave'].with_context(**ctx).sudo().create({
            'employee_id': (emp or self.emp).id,
            'work_entry_type_id': (wet or self.leave_src_type).id,
            'date_from': date_from_dt,
            'date_to': date_to_dt,
            'request_date_from': date_from_dt.date(),
            'request_date_to': date_to_dt.date(),
            'state': 'validate',
        })
        return leave.with_context({})

    def _wizard(self, rule):
        return self.env['hr.time.rule.regenerate.wizard'].create({'rule_ids': [(6, 0, [rule.id])]})

    def _att_outputs(self, att):
        return self.env['hr.attendance'].with_context(active_test=False).search([
            ('source_attendance_id', '=', att.id),
            ('time_rule_id', '!=', False),
        ])

    def _leave_outputs(self, leave):
        return self.env['hr.leave'].with_context(active_test=False).search([
            ('source_leave_id', '=', leave.id),
            ('time_rule_id', '!=', False),
        ])

    def _run_deficit_day_cron(self, for_date):
        """Simulate the day-undertime cron as if running the morning after for_date."""
        with freeze_time(for_date + timedelta(days=1)):
            self.env['hr.leave']._cron_process_day_undertime_rules()

    # find step

    def test_find_attendance_outputs(self):
        """action_find shows the active OT output, not the archived source."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Saturday 6h -> OT
        output_att = self._att_outputs(att)
        self.assertTrue(output_att, "prerequisite: OT output must exist")

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        self.assertEqual(len(wiz.line_ids), 1)
        self.assertEqual(wiz.line_ids.source_model, 'hr.attendance')
        self.assertEqual(wiz.line_ids.source_id, output_att.id)
        self.assertTrue(wiz.line_ids.is_output)
        self.assertEqual(wiz.step, 'restore')

    def test_find_leave_outputs(self):
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))  # 6h > 4h threshold
        output_leave = self._leave_outputs(leave)
        self.assertTrue(output_leave, "prerequisite: output leave must exist")

        wiz = self._wizard(self.leave_excess_rule)
        wiz.action_find()

        # output + remainder are both shown (they share the same original)
        self.assertEqual(len(wiz.line_ids), 2)
        self.assertTrue(all(l.source_model == 'hr.leave' for l in wiz.line_ids))
        self.assertTrue(all(l.is_output for l in wiz.line_ids))
        output_line = wiz.line_ids.filtered(lambda l: l.source_id == output_leave.id)
        self.assertTrue(output_line, "output leave must be one of the lines")

    def test_find_both_source_types_are_independent(self):
        """Rules targeting attendance and leave sources are isolated - each wizard sees only its rule's outputs."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Saturday OT
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))

        att_wiz = self._wizard(self.att_rule)
        att_wiz.action_find()
        # att rule: 1 output (no remainder for attendance; excess = entire OT span)
        self.assertEqual(len(att_wiz.line_ids), 1)
        self.assertEqual(att_wiz.line_ids.source_model, 'hr.attendance')
        # att wizard must not include leave records
        self.assertFalse(any(l.source_model == 'hr.leave' for l in att_wiz.line_ids))

        lv_wiz = self._wizard(self.leave_excess_rule)
        lv_wiz.action_find()
        # leave rule: output + remainder (6h leave against 4h threshold -> 2 lines)
        self.assertEqual(len(lv_wiz.line_ids), 2)
        self.assertTrue(all(l.source_model == 'hr.leave' for l in lv_wiz.line_ids))
        # leave wizard must not include attendance records
        self.assertFalse(any(l.source_model == 'hr.attendance' for l in lv_wiz.line_ids))

        # cleanup for other tests
        att.with_context(active_test=False, skip_time_rules=True).sudo().unlink()
        leave.with_context(active_test=False, skip_time_rules=True).sudo().unlink()

    def test_find_shows_all_outputs_separately(self):
        """Multiple active outputs for the same original source appear as separate lines."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        outputs = self._att_outputs(att)
        self.assertEqual(len(outputs), 1, "prerequisite: one OT output")

        # create a second fake output pointing to the same source (two passes of the engine)
        second = self.env['hr.attendance'].sudo().with_context(skip_time_rules=True).create({
            'employee_id': self.emp.id,
            'check_in': datetime(2022, 12, 10, 14),
            'check_out': datetime(2022, 12, 10, 15),
            'source_attendance_id': att.id,
            'time_rule_id': self.att_rule.id,
            'work_entry_type_id': self.ot_type.id,
        })

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        output_ids = {outputs.id, second.id}
        self.assertEqual(len(wiz.line_ids), 2, "each output is its own line")
        self.assertTrue(
            all(l.source_id in output_ids for l in wiz.line_ids),
            "lines reference output IDs, not the archived source",
        )
        self.assertTrue(all(l.is_output for l in wiz.line_ids))

        second.with_context(skip_time_rules=True).sudo().unlink()

    def test_find_no_outputs_yields_empty_lines(self):
        """When the rule has produced no outputs, action_find results in zero lines (scope='all')."""
        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        self.assertFalse(wiz.line_ids, "no outputs and scope='all' -> no lines")
        self.assertEqual(wiz.step, 'restore')

    def test_find_scope_range_includes_matching(self):
        """scope='range' with matching date window includes outputs within it."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Saturday
        output_att = self._att_outputs(att)
        self.assertTrue(output_att)

        wiz = self._wizard(self.att_rule)
        wiz.write({'scope': 'range', 'date_from': '2022-12-10', 'date_to': '2022-12-10'})
        wiz.action_find()

        self.assertEqual(len(wiz.line_ids), 1)
        self.assertEqual(wiz.line_ids.source_id, output_att.id)

    def test_find_scope_range_excludes_outside(self):
        """scope='range' with a window that doesn't overlap the output -> no lines."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        self.assertTrue(self._att_outputs(att))

        wiz = self._wizard(self.att_rule)
        wiz.write({'scope': 'range', 'date_from': '2022-12-01', 'date_to': '2022-12-09'})
        wiz.action_find()

        self.assertFalse(wiz.line_ids, "output is outside the date range; must not appear")

    def test_find_scope_range_picks_up_virgin_attendance(self):
        """scope='range' finds an attendance with no outputs yet (is_output=False)."""
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 16))  # Mon 8h, no OT

        wiz = self._wizard(self.att_rule)
        wiz.write({'scope': 'range', 'date_from': '2022-12-12', 'date_to': '2022-12-12'})
        wiz.action_find()

        virgin_line = wiz.line_ids.filtered(lambda l: l.source_id == att.id)
        self.assertTrue(virgin_line, "virgin attendance must appear in scope='range' find")
        self.assertFalse(virgin_line.is_output, "virgin source is not an output")

    def test_find_scope_range_picks_up_virgin_leave(self):
        """scope='range' finds a validated leave with no outputs yet (is_output=False)."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 11),
                                 skip_rules=True)  # skip rules so no output is created
        self.assertFalse(self._leave_outputs(leave), "prerequisite: no outputs")

        wiz = self._wizard(self.leave_excess_rule)
        wiz.write({'scope': 'range', 'date_from': '2022-12-12', 'date_to': '2022-12-12'})
        wiz.action_find()

        virgin_line = wiz.line_ids.filtered(lambda l: l.source_id == leave.id)
        self.assertTrue(virgin_line, "virgin leave must appear in scope='range' find")
        self.assertFalse(virgin_line.is_output)

    def test_find_scope_all_does_not_include_virgin_sources(self):
        att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 16))  # no OT

        wiz = self._wizard(self.att_rule)
        # scope='all' (default)
        wiz.action_find()

        virgin_line = wiz.line_ids.filtered(lambda l: l.source_id == att.id)
        self.assertFalse(virgin_line, "scope='all' must not include sources with no outputs")

    def test_find_is_output_true_for_output_records(self):
        """Active outputs found via backward lookup have is_output=True."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Sat OT
        self.assertTrue(self._att_outputs(att))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        self.assertTrue(wiz.line_ids.is_output, "active output -> is_output=True")

    def test_find_multiple_sources_multiple_outputs(self):
        """Two different source attendances -> two output lines in the wizard."""
        att1 = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Sat 6h OT
        att2 = self._make_att(datetime(2022, 12, 17, 11), datetime(2022, 12, 17, 17))  # Sat 6h OT
        out1 = self._att_outputs(att1)
        out2 = self._att_outputs(att2)

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        self.assertEqual(len(wiz.line_ids), 2)
        source_ids = set(wiz.line_ids.mapped('source_id'))
        self.assertIn(out1.id, source_ids)
        self.assertIn(out2.id, source_ids)

    def test_find_multiple_employees_all_listed(self):
        """Outputs for different employees under the same rule all appear in the wizard."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16), emp=self.emp)
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16), emp=self.emp2)

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        self.assertEqual(len(wiz.line_ids), 2)
        employee_ids = set(wiz.line_ids.mapped('employee_id').ids)
        self.assertIn(self.emp.id, employee_ids)
        self.assertIn(self.emp2.id, employee_ids)

    def test_find_second_call_clears_previous_lines(self):
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        first_line_ids = wiz.line_ids.ids

        # call again - should replace, not accumulate
        wiz.step = 'find'
        wiz.action_find()

        self.assertEqual(len(wiz.line_ids), 1, "second find must not duplicate lines")
        self.assertNotEqual(wiz.line_ids.ids, first_line_ids, "fresh line records created")

    def test_find_deficit_leave_shows_output(self):
        """Deficit rule: the deficit output leave(s) are shown, not the source leave."""
        # 3h leave on 8h day -> deficit = 5h -> output leave(s) created
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 11),
                                 wet=self.leave_deficit_src_type)
        self._run_deficit_day_cron(date(2022, 12, 12))
        output_leaves = self._leave_outputs(leave)
        self.assertTrue(output_leaves, "prerequisite: deficit output must exist")

        wiz = self._wizard(self.deficit_rule)
        wiz.action_find()

        self.assertEqual(len(wiz.line_ids), len(output_leaves))
        self.assertTrue(all(l.source_model == 'hr.leave' for l in wiz.line_ids))
        self.assertEqual(set(wiz.line_ids.mapped('source_id')), set(output_leaves.ids))
        self.assertTrue(all(l.is_output for l in wiz.line_ids))

    def test_find_line_fields_populated_attendance(self):
        """Line fields (employee_id, date, date_from, date_to, work_entry_type_id) reflect the OUTPUT record."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        output_att = self._att_outputs(att)

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        line = wiz.line_ids
        self.assertEqual(line.employee_id, self.emp)
        self.assertEqual(line.date, output_att.check_in.date())
        self.assertEqual(line.date_from, output_att.check_in)
        self.assertEqual(line.date_to, output_att.check_out)
        self.assertEqual(line.work_entry_type_id, output_att.work_entry_type_id)

    def test_find_line_fields_populated_leave(self):
        """Line fields reflect the OUTPUT leave record."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
        output_leave = self._leave_outputs(leave)

        wiz = self._wizard(self.leave_excess_rule)
        wiz.action_find()

        # filter to the output line (remainder also present)
        line = wiz.line_ids.filtered(lambda l: l.source_id == output_leave.id)
        self.assertTrue(line, "output leave line must be present")
        line.ensure_one()
        self.assertEqual(line.employee_id, self.emp)
        self.assertEqual(line.date, output_leave.date_from.date())
        self.assertEqual(line.date_from, output_leave.date_from)
        self.assertEqual(line.date_to, output_leave.date_to)

    # restore step

    def test_restore_attendance_reactivates_source_and_removes_outputs(self):
        """action_restore undoes OT outputs and restores the archived source attendance."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        self.assertFalse(att.active, "source must be archived after OT creation")
        outputs_before = self._att_outputs(att)
        self.assertTrue(outputs_before, "outputs must exist before restore")

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        att.invalidate_recordset()
        self.assertTrue(att.active, "source restored to active after wizard restore")
        outputs_after = self._att_outputs(att)
        self.assertFalse(outputs_after, "all OT outputs removed after restore")

    def test_restore_leave_reactivates_source_and_removes_outputs(self):
        """action_restore undoes excess outputs and restores the archived source leave."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
        self.assertFalse(leave.active, "source leave must be archived after excess rule fires")
        self.assertTrue(self._leave_outputs(leave))

        wiz = self._wizard(self.leave_excess_rule)
        wiz.action_find()
        wiz.action_restore()

        leave.invalidate_recordset()
        self.assertTrue(leave.active, "source leave restored to active")
        self.assertFalse(self._leave_outputs(leave))

    def test_restore_deficit_leave_does_not_archive_source(self):
        """Deficit sources are never archived, so restore still removes the deficit output."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 11),
                                 wet=self.leave_deficit_src_type)  # 3h -> deficit
        self._run_deficit_day_cron(date(2022, 12, 12))
        self.assertTrue(leave.active, "deficit source stays active")
        self.assertTrue(self._leave_outputs(leave))

        wiz = self._wizard(self.deficit_rule)
        wiz.action_find()
        wiz.action_restore()

        self.assertTrue(leave.active, "deficit source remains active after restore")
        self.assertFalse(self._leave_outputs(leave), "deficit output removed")

    def test_restore_step_advances_to_rerun(self):
        """After action_restore the wizard step is 'rerun'."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()
        self.assertEqual(wiz.step, 'rerun')

    def test_restore_populates_removed_line_ids(self):
        """After action_restore, removed_line_ids contains info about the deleted outputs."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        self.assertTrue(wiz.removed_line_ids, "removed_line_ids must be populated after restore")
        removed = wiz.removed_line_ids
        self.assertEqual(removed.employee_id, self.emp)

    def test_restore_line_ids_replaced_with_restored_originals(self):
        """After action_restore, line_ids contains the now-active original source records (is_output=False)."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        # before restore: line has the output, is_output=True
        self.assertTrue(wiz.line_ids.is_output)

        wiz.action_restore()

        # after restore: line has the restored original (att), is_output=False
        self.assertEqual(len(wiz.line_ids), 1)
        self.assertEqual(wiz.line_ids.source_id, att.id)
        self.assertFalse(wiz.line_ids.is_output, "restored original is not an output")

    def test_restore_skips_virgin_lines(self):
        """action_restore silently skips lines where is_output=False (virgin candidates)."""
        # att has outputs (Sat OT); fresh_att has none (Mon 8h, no excess)
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        fresh_att = self._make_att(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 16))

        wiz = self._wizard(self.att_rule)
        wiz.write({'scope': 'range', 'date_from': '2022-12-10', 'date_to': '2022-12-12'})
        wiz.action_find()

        fresh_line = wiz.line_ids.filtered(lambda l: l.source_id == fresh_att.id)
        self.assertTrue(fresh_line, "fresh att must appear in scope=range find")
        self.assertFalse(fresh_line.is_output)

        wiz.action_restore()

        # fresh_att must not have been touched by restore
        fresh_att.invalidate_recordset()
        self.assertTrue(fresh_att.active, "virgin source must stay active after restore")
        # att must have been restored
        att.invalidate_recordset()
        self.assertTrue(att.active, "source with outputs must be restored")

    def test_restore_deduplicates_by_original_source(self):
        """Two output lines sharing the same original source trigger _undo_time_rules only once."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        self._att_outputs(att)

        # create a second fake output pointing to the same source
        self.env['hr.attendance'].sudo().with_context(skip_time_rules=True).create({
            'employee_id': self.emp.id,
            'check_in': datetime(2022, 12, 10, 14),
            'check_out': datetime(2022, 12, 10, 15),
            'source_attendance_id': att.id,
            'time_rule_id': self.att_rule.id,
            'work_entry_type_id': self.ot_type.id,
        })

        undo_calls = []
        original_undo = self.env.registry['hr.attendance']._undo_time_rules

        def _tracking_undo(self_inner):
            undo_calls.append(self_inner.id)
            original_undo(self_inner)

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        self.assertEqual(len(wiz.line_ids), 2, "prerequisite: two output lines")

        try:
            self.env.registry['hr.attendance']._undo_time_rules = _tracking_undo
            wiz.action_restore()
        finally:
            self.env.registry['hr.attendance']._undo_time_rules = original_undo

        self.assertEqual(undo_calls.count(att.id), 1, "_undo_time_rules called once for shared source")

    def test_restore_partial_selection_only_affects_selected(self):
        """Deselecting an output line in the wizard leaves that source's outputs intact."""
        att1 = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Sat
        att2 = self._make_att(datetime(2022, 12, 17, 11), datetime(2022, 12, 17, 17))  # Sat
        out2 = self._att_outputs(att2)

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        # deselect the line for att2's output
        line_for_att2 = wiz.line_ids.filtered(lambda l: l.source_id == out2.id)
        self.assertTrue(line_for_att2)
        line_for_att2.selected = False

        wiz.action_restore()

        att1.invalidate_recordset()
        att2.invalidate_recordset()
        self.assertTrue(att1.active, "selected source restored")
        self.assertFalse(att2.active, "unselected source left archived")
        self.assertTrue(self._att_outputs(att2), "unselected source outputs untouched")

    def test_restore_validation_error_lands_in_error_lines(self):
        """If _undo_time_rules raises ValidationError, the line moves to error_line_ids."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
        self.assertTrue(self._leave_outputs(leave))

        wiz = self._wizard(self.leave_excess_rule)
        wiz.action_find()

        original_undo = self.env.registry['hr.leave']._undo_time_rules

        def _failing_undo(self_inner):
            raise ValidationError("simulated allocation reversal failure")

        try:
            self.env.registry['hr.leave']._undo_time_rules = _failing_undo
            wiz.action_restore()
        finally:
            self.env.registry['hr.leave']._undo_time_rules = original_undo

        self.assertTrue(wiz.has_errors, "error must be recorded")
        self.assertEqual(len(wiz.error_line_ids), 1)
        self.assertIn("simulated", wiz.error_line_ids.error)
        self.assertFalse(wiz.line_ids, "failed output line removed; no survivors")

    def test_restore_surviving_lines_kept_failed_removed(self):
        """When one source fails and another succeeds, only the survivor stays in line_ids."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Sat
        self._make_att(datetime(2022, 12, 17, 11), datetime(2022, 12, 17, 17))  # Sat

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        # identify which original source we want to fail
        # the output line's source_id is an OUTPUT id; get the original via source_attendance_id
        fail_output_id = wiz.line_ids[0].source_id
        fail_rec = self.env['hr.attendance'].browse(fail_output_id)
        fail_original_id = fail_rec.with_context(active_test=False).source_attendance_id.id

        survive_output_id = wiz.line_ids[1].source_id
        survive_rec = self.env['hr.attendance'].browse(survive_output_id)
        survive_original_id = survive_rec.with_context(active_test=False).source_attendance_id.id

        original_undo = self.env.registry['hr.attendance']._undo_time_rules
        call_count = [0]

        def _partial_fail(self_inner):
            call_count[0] += 1
            if self_inner.id == fail_original_id:
                raise ValidationError("first fails")
            original_undo(self_inner)

        try:
            self.env.registry['hr.attendance']._undo_time_rules = _partial_fail
            wiz.action_restore()
        finally:
            self.env.registry['hr.attendance']._undo_time_rules = original_undo

        self.assertEqual(len(wiz.error_line_ids), 1)
        self.assertEqual(len(wiz.line_ids), 1, "survivor stays in line_ids for rerun")
        # after restore, the survivor line has the restored ORIGINAL's id
        self.assertEqual(wiz.line_ids.source_id, survive_original_id)

    def test_restore_clears_previous_error_lines(self):
        """Calling action_restore a second time clears error_line_ids from the previous attempt."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()

        original_undo = self.env.registry['hr.attendance']._undo_time_rules
        fail = [True]

        def _toggle_fail(self_inner):
            if fail[0]:
                raise ValidationError("first attempt fails")
            original_undo(self_inner)

        try:
            self.env.registry['hr.attendance']._undo_time_rules = _toggle_fail
            wiz.action_restore()
            self.assertEqual(len(wiz.error_line_ids), 1, "first attempt produced an error")

            # put the source line back and try again without failing
            fail[0] = False
            wiz.step = 'find'
            wiz.action_find()
            wiz.action_restore()
        finally:
            self.env.registry['hr.attendance']._undo_time_rules = original_undo

        self.assertFalse(wiz.error_line_ids, "previous errors cleared on fresh restore attempt")

    # rerun step

    def test_rerun_attendance_recreates_outputs(self):
        """After restore+rerun the OT output is recreated."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        self.assertFalse(self._att_outputs(att), "outputs removed after restore")

        wiz.action_rerun()

        att.invalidate_recordset()
        new_outputs = self._att_outputs(att)
        self.assertTrue(new_outputs, "outputs recreated after rerun")

    def test_rerun_leave_recreates_outputs(self):
        """After restore+rerun the excess leave output is recreated."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))

        wiz = self._wizard(self.leave_excess_rule)
        wiz.action_find()
        wiz.action_restore()
        self.assertFalse(self._leave_outputs(leave))

        wiz.action_rerun()

        new_outputs = self._leave_outputs(leave)
        self.assertTrue(new_outputs, "excess leave output recreated after rerun")

    def test_rerun_deficit_recreates_output(self):
        """Deficit rule: after restore+rerun the deficit output leave is recreated."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 11),
                                 wet=self.leave_deficit_src_type)
        self._run_deficit_day_cron(date(2022, 12, 12))

        wiz = self._wizard(self.deficit_rule)
        wiz.action_find()
        wiz.action_restore()
        self.assertFalse(self._leave_outputs(leave))

        wiz.action_rerun()

        new_outputs = self._leave_outputs(leave)
        self.assertTrue(new_outputs, "deficit output leave recreated after rerun")

    def test_rerun_success_advances_to_done_step(self):
        """Successful rerun moves the wizard to the 'done' step and reopens the form."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()
        result = wiz.action_rerun()

        self.assertEqual(wiz.step, 'done')
        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        self.assertEqual(result.get('res_id'), wiz.id)

    def test_rerun_failure_stays_in_rerun_step_with_error(self):
        """When action_rerun encounters a ValidationError, the wizard stays open with errors shown."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        original_trigger = self.env.registry['hr.attendance']._trigger_time_rules

        def _failing_trigger(self_inner, **kwargs):
            raise ValidationError("simulated rerun failure")

        try:
            self.env.registry['hr.attendance']._trigger_time_rules = _failing_trigger
            result = wiz.action_rerun()
        finally:
            self.env.registry['hr.attendance']._trigger_time_rules = original_trigger

        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        self.assertTrue(wiz.has_errors)
        self.assertEqual(len(wiz.error_line_ids), 1)
        self.assertEqual(wiz.step, 'rerun')

    def test_rerun_partial_failure_records_errors_for_failed_only(self):
        """When some sources succeed and others fail on rerun, only failures go to error_line_ids."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        self._make_att(datetime(2022, 12, 17, 11), datetime(2022, 12, 17, 17))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        # after restore, line_ids has the two restored originals
        fail_source_id = wiz.line_ids[0].source_id
        original_trigger = self.env.registry['hr.attendance']._trigger_time_rules

        def _partial_fail(self_inner, **kwargs):
            if self_inner.id == fail_source_id:
                raise ValidationError("fails")
            original_trigger(self_inner, **kwargs)

        try:
            self.env.registry['hr.attendance']._trigger_time_rules = _partial_fail
            wiz.action_rerun()
        finally:
            self.env.registry['hr.attendance']._trigger_time_rules = original_trigger

        self.assertEqual(len(wiz.error_line_ids), 1)
        self.assertTrue(wiz.has_errors)

    def test_rerun_clears_previous_rerun_errors(self):
        """A second rerun attempt clears error_line_ids from the previous failed rerun."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        original_trigger = self.env.registry['hr.attendance']._trigger_time_rules
        fail = [True]

        def _toggle_fail(self_inner, **kwargs):
            if fail[0]:
                raise ValidationError("first rerun fails")
            original_trigger(self_inner, **kwargs)

        try:
            self.env.registry['hr.attendance']._trigger_time_rules = _toggle_fail
            wiz.action_rerun()
            self.assertEqual(len(wiz.error_line_ids), 1)

            fail[0] = False
            wiz.action_rerun()
        finally:
            self.env.registry['hr.attendance']._trigger_time_rules = original_trigger

        self.assertFalse(wiz.error_line_ids, "second successful rerun clears previous errors")

    def test_rerun_deselected_line_skipped(self):
        """Lines that are deselected in the rerun step are not re-triggered."""
        att1 = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        att2 = self._make_att(datetime(2022, 12, 17, 11), datetime(2022, 12, 17, 17))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        # after restore, line_ids has restored originals; filter by att2.id
        line_att2 = wiz.line_ids.filtered(lambda l: l.source_id == att2.id)
        self.assertTrue(line_att2)
        line_att2.selected = False

        triggered = []
        original_trigger = self.env.registry['hr.attendance']._trigger_time_rules

        def _tracking_trigger(self_inner, **kwargs):
            triggered.append(self_inner.id)
            original_trigger(self_inner, **kwargs)

        try:
            self.env.registry['hr.attendance']._trigger_time_rules = _tracking_trigger
            wiz.action_rerun()
        finally:
            self.env.registry['hr.attendance']._trigger_time_rules = original_trigger

        self.assertIn(att1.id, triggered)
        self.assertNotIn(att2.id, triggered, "deselected source must not be re-triggered")

    # full round-trips

    def test_full_flow_attendance_find_restore_rerun(self):
        """Complete three-step flow for an attendance OT source produces identical net result."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        outputs_before = self._att_outputs(att)
        self.assertEqual(len(outputs_before), 1)
        hours_before = sum(
            (o.check_out - o.check_in).total_seconds() / 3600 for o in outputs_before
        )

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        self.assertEqual(wiz.step, 'restore')
        # find shows the OUTPUT (active, is_output=True)
        self.assertTrue(wiz.line_ids.is_output)

        wiz.action_restore()
        self.assertEqual(wiz.step, 'rerun')
        att.invalidate_recordset()
        self.assertTrue(att.active, "source reactivated after restore")
        self.assertFalse(self._att_outputs(att), "outputs removed after restore")
        # rerun step shows the restored original (is_output=False)
        self.assertFalse(wiz.line_ids.is_output)
        self.assertEqual(wiz.line_ids.source_id, att.id)
        # removed_line_ids populated
        self.assertTrue(wiz.removed_line_ids)

        wiz.action_rerun()
        att.invalidate_recordset()
        outputs_after = self._att_outputs(att)
        self.assertEqual(len(outputs_after), 1, "single OT output recreated")
        hours_after = sum(
            (o.check_out - o.check_in).total_seconds() / 3600 for o in outputs_after
        )
        self.assertAlmostEqual(hours_before, hours_after, places=5,
                               msg="OT duration unchanged by restore+rerun cycle")

    def test_full_flow_leave_excess(self):
        """Complete flow for a leave excess source: original excess hours preserved after rerun."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))
        outputs_before = self._leave_outputs(leave)
        self.assertTrue(outputs_before)
        hours_before = sum(
            (o.date_to - o.date_from).total_seconds() / 3600 for o in outputs_before
        )

        wiz = self._wizard(self.leave_excess_rule)
        wiz.action_find()
        wiz.action_restore()
        wiz.action_rerun()

        outputs_after = self._leave_outputs(leave)
        self.assertTrue(outputs_after)
        hours_after = sum(
            (o.date_to - o.date_from).total_seconds() / 3600 for o in outputs_after
        )
        self.assertAlmostEqual(hours_before, hours_after, places=5,
                               msg="excess leave output duration unchanged after round-trip")

    def test_full_flow_deficit_leave(self):
        """Complete flow for a leave deficit source: deficit output recreated correctly."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 11),
                                 wet=self.leave_deficit_src_type)  # 3h, 8h threshold -> deficit
        self._run_deficit_day_cron(date(2022, 12, 12))
        outputs_before = self._leave_outputs(leave)
        self.assertTrue(outputs_before)
        hours_before = sum(
            (o.date_to - o.date_from).total_seconds() / 3600 for o in outputs_before
        )

        wiz = self._wizard(self.deficit_rule)
        wiz.action_find()
        wiz.action_restore()
        wiz.action_rerun()

        outputs_after = self._leave_outputs(leave)
        self.assertTrue(outputs_after)
        hours_after = sum(
            (o.date_to - o.date_from).total_seconds() / 3600 for o in outputs_after
        )
        self.assertAlmostEqual(hours_before, hours_after, places=5,
                               msg="deficit output duration preserved after round-trip")

    def test_full_flow_multi_source(self):
        """Two sources for the same rule: both restored and rerun in one wizard pass."""
        att1 = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        att2 = self._make_att(datetime(2022, 12, 17, 11), datetime(2022, 12, 17, 17))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        self.assertEqual(len(wiz.line_ids), 2)

        wiz.action_restore()
        att1.invalidate_recordset()
        att2.invalidate_recordset()
        self.assertTrue(att1.active)
        self.assertTrue(att2.active)

        wiz.action_rerun()
        self.assertFalse(wiz.has_errors)
        self.assertTrue(self._att_outputs(att1), "att1 outputs recreated")
        self.assertTrue(self._att_outputs(att2), "att2 outputs recreated")

    def test_full_flow_different_rule_no_cross_contamination(self):
        """Restoring via one rule's wizard must not affect outputs owned by a different rule."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Sat OT
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))

        leave_outputs_before = self._leave_outputs(leave)
        self.assertTrue(leave_outputs_before)

        # only run the att_rule wizard
        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        leave.invalidate_recordset()
        leave_outputs_after = self._leave_outputs(leave)
        self.assertEqual(
            set(leave_outputs_after.ids),
            set(leave_outputs_before.ids),
            "leave excess outputs must not be touched by the attendance OT wizard",
        )

    # run step

    def test_run_on_output_lines_is_noop(self):
        """action_run on output lines (is_output=True) does nothing - use action_restore first."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))  # Sat 6h OT
        existing_output = self._att_outputs(att)
        self.assertEqual(len(existing_output), 1)

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        # all found lines are outputs
        self.assertTrue(all(l.is_output for l in wiz.line_ids))

        wiz.action_run()

        # output not touched: source still archived, output still exists
        att.invalidate_recordset()
        self.assertFalse(att.active, "source not restored when action_run is called on output lines")
        self.assertTrue(existing_output.exists(), "output not deleted: action_run skips is_output lines")

    def test_run_on_virgin_line_triggers_directly(self):
        """action_run on a fresh (virgin) candidate line triggers the rule directly."""
        att = self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        att.invalidate_recordset()
        self.assertTrue(att.active, "source reactivated after restore")
        self.assertFalse(self._att_outputs(att))

        # the rerun step line (is_output=False, restored original)
        wiz.action_run()

        self.assertTrue(self._att_outputs(att), "outputs created by action_run on virgin line")

    def test_run_success_returns_act_window(self):
        """Successful action_run (on non-output lines) returns act_window reopening the wizard."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()
        result = wiz.action_run()

        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        self.assertEqual(result.get('res_id'), wiz.id)
        self.assertEqual(wiz.step, 'done')

    def test_run_failure_goes_to_rerun_step_with_errors(self):
        """When action_run hits a ValidationError it records the error and moves to rerun step."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        original_trigger = self.env.registry['hr.attendance']._trigger_time_rules

        def _failing_trigger(self_inner, **kwargs):
            raise ValidationError("run failure")

        try:
            self.env.registry['hr.attendance']._trigger_time_rules = _failing_trigger
            result = wiz.action_run()
        finally:
            self.env.registry['hr.attendance']._trigger_time_rules = original_trigger

        self.assertEqual(result.get('type'), 'ir.actions.act_window')
        self.assertTrue(wiz.has_errors)
        self.assertEqual(wiz.step, 'rerun')

    def test_run_leave_creates_outputs(self):
        """action_run works for leave sources too."""
        leave = self._make_leave(datetime(2022, 12, 12, 8), datetime(2022, 12, 12, 14))

        wiz = self._wizard(self.leave_excess_rule)
        wiz.action_find()
        wiz.action_restore()
        self.assertFalse(self._leave_outputs(leave))

        wiz.action_run()

        self.assertTrue(self._leave_outputs(leave), "excess leave output created by action_run")

    def test_run_partial_failure_records_only_failed(self):
        """When some sources fail on action_run, only those appear in error_line_ids."""
        self._make_att(datetime(2022, 12, 10, 10), datetime(2022, 12, 10, 16))
        self._make_att(datetime(2022, 12, 17, 11), datetime(2022, 12, 17, 17))

        wiz = self._wizard(self.att_rule)
        wiz.action_find()
        wiz.action_restore()

        # after restore, lines have restored originals; pick one to fail
        fail_source_id = wiz.line_ids[0].source_id
        original_trigger = self.env.registry['hr.attendance']._trigger_time_rules

        def _partial_fail(self_inner, **kwargs):
            if self_inner.id == fail_source_id:
                raise ValidationError("fails")
            original_trigger(self_inner, **kwargs)

        try:
            self.env.registry['hr.attendance']._trigger_time_rules = _partial_fail
            wiz.action_run()
        finally:
            self.env.registry['hr.attendance']._trigger_time_rules = original_trigger

        self.assertEqual(len(wiz.error_line_ids), 1)
        self.assertTrue(wiz.error_line_ids.employee_id.id,
                        "error line must have employee populated")
