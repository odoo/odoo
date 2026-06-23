# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from odoo import fields, models

from odoo.addons.hr_work_entry.models.hr_time_rule import _record_overlap_intervals
from odoo.tools.intervals import Intervals


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    work_entry_type_id = fields.Many2one(
        domain="[('id', 'in', country_work_entry_type_ids), ('requires_allocation', '=', False)]",
    )
    leave_compensation_rate = fields.Float("Allocate %", default=0.0)
    allocation_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Allocate to",
        domain="[('requires_allocation', '=', True), ('id', 'in', country_work_entry_type_ids)]",
    )

    def _get_remainder_leave_vals(self, employee, source_leave, date_from, date_to):
        return {
            'employee_id': employee.id,
            'work_entry_type_id': source_leave.work_entry_type_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': date_from.date(),
            'request_date_to': date_to.date(),
            'source_leave_id': source_leave.id,
            'resource_calendar_id': source_leave.resource_calendar_id.id,
            'state': 'validate',
        }

    def _get_output_leave_vals(self, employee, rule, date_from, date_to, source_leave, all_rules=None, accumulated_pp=frozenset()):
        return {
            'employee_id': employee.id,
            'work_entry_type_id': rule.work_entry_type_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': date_from.date(),
            'request_date_to': date_to.date(),
            'time_rule_id': rule.id,
            'source_leave_id': source_leave.id,
            'resource_calendar_id': source_leave.resource_calendar_id.id,
            'state': 'validate',
        }

    def _get_output_leave_merge_key(self, all_rules, accumulated_pp=frozenset()):
        """Hashable key controlling when consecutive excess slices are merged into one leave.

        Override to add extra discriminators (e.g. premium pay rule sets in Belgium).
        `self` is the effective (lowest-sequence) rule; `all_rules` is the full active set.
        """
        return self

    def _apply_leave_output(self, excess, deficit):
        """Create output and remainder leave records from the computed excess/deficit.

        For excess: shrink source date_to to first OT start (or archive if OT covers the
        beginning), create remainder records for subsequent non-OT gaps, and output records
        for OT segments.  For deficit: emit output records as before.
        """
        Leave = self.env['hr.leave'].sudo()
        auto_ctx = dict(
            skip_time_rules=True,
            leave_fast_create=True,
            leave_skip_date_check=True,
            leave_skip_state_check=True,
            tracking_disable=True,
            mail_activity_automation_skip=True,
            skip_leave_version_check=True,
            skip_create_resource_leave=True,
        )

        leave_create_vals = []
        archive_source_ids = []
        all_source_ids = set()

        for employee, by_source in deficit.items():
            tz = ZoneInfo(employee._get_tz())
            for source_leave, intervals in by_source.items():
                all_source_ids.add(source_leave.id)
                by_period = defaultdict(list)
                for start, stop, rule, _pp in intervals:
                    if rule.quantity_period == 'week':
                        ws = int(rule.week_start or '0')
                        days_to_end = ((ws - 1) % 7 - start.weekday()) % 7
                        pkey = ('week', start.date() + timedelta(days=days_to_end))
                    else:
                        pkey = ('day', start.date())
                    by_period[pkey].append((start, stop, rule))

                winning_intervals = []
                for pivs in by_period.values():
                    all_period_rules = self.browse([r.id for _, _, r in pivs])
                    min_seq = min(r.sequence for r in all_period_rules)
                    for s, e, r in pivs:
                        if r.sequence == min_seq:
                            winning_intervals.append((s, e, r, all_period_rules))

                for start_local, stop_local, rule, all_rules in winning_intervals:
                    if not rule.work_entry_type_id:
                        continue
                    date_from = start_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    date_to = stop_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    leave_create_vals.append(
                        self._get_output_leave_vals(employee, rule, date_from, date_to, source_leave, all_rules=all_rules)
                    )

                    if rule.leave_compensation_rate > 0 and rule.allocation_type_id:
                        deficit_hours = (date_to - date_from).total_seconds() / 3600
                        deduct_days = deficit_hours * rule.leave_compensation_rate / 100
                        allocation = self.env['hr.leave.allocation'].sudo().search([
                            ('employee_id', '=', employee.id),
                            ('work_entry_type_id', '=', rule.allocation_type_id.id),
                            ('state', '=', 'validate'),
                        ], limit=1)
                        if allocation:
                            allocation.number_of_days = max(0, allocation.number_of_days - deduct_days)

        dummy = self.env['resource.calendar']

        for employee, by_source in excess.items():
            tz = ZoneInfo(employee._get_tz())
            for source_leave, intervals in by_source.items():
                all_source_ids.add(source_leave.id)
                pp_by_range = {}
                for s, e, _r, pp in intervals:
                    key = (s, e)
                    pp_by_range[key] = pp_by_range.get(key, frozenset()) | pp

                slices = list(_record_overlap_intervals([(s, e, r) for s, e, r, _pp in intervals]))
                output_slices = [
                    (start, stop, rules, pp_by_range.get((start, stop), frozenset()))
                    for start, stop, rules in slices
                    if stop > start and rules.filtered('work_entry_type_id')
                ]
                if not output_slices:
                    continue

                alloc_create_vals = []
                for start_local, stop_local, rules, _pp in output_slices:
                    alloc_rules = rules.filtered(
                        lambda r: r.leave_compensation_rate > 0 and r.allocation_type_id
                    )
                    for alloc_rule in alloc_rules:
                        excess_hours = (stop_local - start_local).total_seconds() / 3600
                        alloc_days = excess_hours * alloc_rule.leave_compensation_rate / 100
                        if alloc_days <= 0:
                            continue
                        allocation = self.env['hr.leave.allocation'].sudo().search([
                            ('employee_id', '=', employee.id),
                            ('work_entry_type_id', '=', alloc_rule.allocation_type_id.id),
                            ('state', '=', 'validate'),
                        ], limit=1)
                        if allocation:
                            allocation.number_of_days += alloc_days
                        else:
                            alloc_create_vals.append({
                                'employee_id': employee.id,
                                'work_entry_type_id': alloc_rule.allocation_type_id.id,
                                'number_of_days': alloc_days,
                                'state': 'confirm',
                            })

                if alloc_create_vals:
                    new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create(alloc_create_vals)
                    new_allocs.action_approve()

                merged_slices = []
                for start, stop, rules, pp in output_slices:
                    effective = rules.sorted('sequence').filtered('work_entry_type_id')[:1]
                    merge_key = effective._get_output_leave_merge_key(rules, accumulated_pp=pp)
                    if merged_slices and merged_slices[-1][1] == start and merged_slices[-1][5] == merge_key:
                        merged_slices[-1][1] = stop
                        merged_slices[-1][2] |= rules
                        merged_slices[-1][4] |= pp
                    else:
                        merged_slices.append([start, stop, rules, effective, pp, merge_key])

                # compute remainder segments (source - all outputs)
                src_start = source_leave.date_from.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
                src_stop = source_leave.date_to.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
                out_union = Intervals(
                    [(s, e, dummy) for s, e, *_ in output_slices],
                    keep_distinct=True,
                )
                remainder_segments = list(Intervals([(src_start, src_stop, dummy)]) - out_union)

                min_out_start_local = min(s for s, e, *_ in output_slices)
                min_out_start_utc = min_out_start_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)

                if min_out_start_utc <= source_leave.date_from:
                    # OT covers the very start → archive source; all remainders become records
                    archive_source_ids.append(source_leave.id)
                    for seg_s, seg_e, _ in remainder_segments:
                        df = seg_s.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        dt = seg_e.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        leave_create_vals.append(self._get_remainder_leave_vals(employee, source_leave, df, dt))
                else:
                    # OT starts after source start → shrink source date_to; source IS remainder[0]
                    Leave.browse([source_leave.id]).with_context(**auto_ctx).write({
                        'date_to': min_out_start_utc,
                        'request_date_to': min_out_start_utc.date(),
                    })
                    for seg_s, seg_e, _ in remainder_segments[1:]:
                        df = seg_s.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        dt = seg_e.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        leave_create_vals.append(self._get_remainder_leave_vals(employee, source_leave, df, dt))

                for start_local, stop_local, all_rules, rule, accumulated_pp, _merge_key in merged_slices:
                    date_from = start_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    date_to = stop_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    leave_create_vals.append(
                        self._get_output_leave_vals(
                            employee, rule, date_from, date_to, source_leave,
                            all_rules=all_rules, accumulated_pp=accumulated_pp,
                        )
                    )

        if archive_source_ids:
            Leave.browse(archive_source_ids).with_context(**auto_ctx).write({'active': False})

        new_leaves = Leave.with_context(**auto_ctx).create(leave_create_vals)

        if all_source_ids:
            sources = Leave.with_context(active_test=False).browse(list(all_source_ids))
            (sources | new_leaves)._create_resource_leave()
