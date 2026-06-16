# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC, timedelta
from zoneinfo import ZoneInfo

from odoo import models
from odoo.tools.intervals import Intervals

from odoo.addons.hr_work_entry.models.hr_time_rule import _record_overlap_intervals


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

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

    def _get_output_leave_vals(self, employee, rule, date_from, date_to, source_leave, all_rules=None):
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

    def _get_output_leave_merge_key(self, all_rules):
        """Hashable key controlling when consecutive excess slices are merged into one leave.

        Override to add extra discriminators (e.g. premium pay rule sets in Belgium).
        `self` is the effective (lowest-sequence) rule; `all_rules` is the full active set.
        """
        return self

    def _apply_leave_output(self, excess, deficit):
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
        for employee, by_source in deficit.items():
            tz = ZoneInfo(employee._get_tz())
            for source_leave, intervals in by_source.items():
                by_period = defaultdict(list)
                for start, stop, rule in intervals:
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

        remainder_writes = defaultdict(list)
        zeroout_writes = defaultdict(list)

        for employee, by_source in excess.items():
            tz = ZoneInfo(employee._get_tz())
            for source_leave, intervals in by_source.items():
                slices = list(_record_overlap_intervals(intervals))
                output_slices = [
                    (start, stop, rules)
                    for start, stop, rules in slices
                    if stop > start and rules.filtered('work_entry_type_id')
                ]
                if not output_slices:
                    continue

                src_start = source_leave.date_from.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
                src_stop = source_leave.date_to.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
                src_iv = Intervals([(src_start, src_stop, self.env['resource.calendar'])])
                out_iv = Intervals(
                    [(s, e, self.env['resource.calendar']) for s, e, _ in output_slices],
                    keep_distinct=True,
                )
                remainder = list(src_iv - out_iv)

                if remainder:
                    first_start, first_stop, _ = remainder[0]
                    first_date_from = first_start.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    first_date_to = first_stop.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    remainder_writes[first_date_from, first_date_to].append(source_leave.id)
                    for seg_start, seg_stop, _ in remainder[1:]:
                        seg_date_from = seg_start.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        seg_date_to = seg_stop.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                        leave_create_vals.append(
                            self._get_remainder_leave_vals(employee, source_leave, seg_date_from, seg_date_to)
                        )
                else:
                    zeroout_writes[source_leave.date_from].append(source_leave.id)

                alloc_create_vals = []
                for start_local, stop_local, rules in output_slices:
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
                for start, stop, rules in output_slices:
                    effective = rules.sorted('sequence').filtered('work_entry_type_id')[:1]
                    merge_key = effective._get_output_leave_merge_key(rules)
                    if merged_slices and merged_slices[-1][1] == start and merged_slices[-1][4] == merge_key:
                        merged_slices[-1][1] = stop
                        merged_slices[-1][2] |= rules
                    else:
                        merged_slices.append([start, stop, rules, effective, merge_key])

                for start_local, stop_local, all_rules, rule, _merge_key in merged_slices:
                    date_from = start_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    date_to = stop_local.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)
                    leave_create_vals.append(
                        self._get_output_leave_vals(employee, rule, date_from, date_to, source_leave, all_rules=all_rules)
                    )

        all_modified_source_ids = []
        for (df, dt), ids in remainder_writes.items():
            Leave.browse(ids).with_context(**auto_ctx).write({
                'date_from': df,
                'date_to': dt,
            })
            all_modified_source_ids.extend(ids)
        for date_from, ids in zeroout_writes.items():
            Leave.browse(ids).with_context(**auto_ctx).write({'date_to': date_from})
            all_modified_source_ids.extend(ids)
        if all_modified_source_ids:
            resource_leave_ctx = {k: v for k, v in auto_ctx.items() if k != 'skip_create_resource_leave'}
            Leave.browse(all_modified_source_ids).with_context(**resource_leave_ctx)._create_resource_leave()

        Leave.with_context(**auto_ctx).create(leave_create_vals)
