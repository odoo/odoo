# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    condition_work_entry_type_ids = fields.Many2many(
        domain="[('id', 'in', country_work_entry_type_ids)]",
    )
    work_entry_type_id = fields.Many2one(
        domain="[('id', 'in', country_work_entry_type_ids), ('requires_allocation', '=', False)]",
    )
    condition_is_hourly = fields.Boolean(
        compute='_compute_condition_is_hourly',
        help="True when all selected condition time types are hourly (request_unit='hour').",
    )

    @api.constrains('condition_work_entry_type_ids')
    def _check_condition_units_uniform(self):
        for rule in self:
            units = rule.condition_work_entry_type_ids.mapped('request_unit')
            if len(set(units)) > 1:
                raise ValidationError(self.env._(
                    "Rule '%(name)s': all condition time types must share the same "
                    "request unit (hour, day, or half-day). Mixed units are not supported.",
                    name=rule.name,
                ))

    @api.depends('condition_work_entry_type_ids.request_unit')
    def _compute_condition_is_hourly(self):
        for rule in self:
            types = rule.condition_work_entry_type_ids
            rule.condition_is_hourly = not types or all(t.request_unit == 'hour' for t in types)

    def _is_hourly(self):
        types = self.condition_work_entry_type_ids
        return not types or all(t.request_unit == 'hour' for t in types)

    @api.depends('condition_work_entry_type_ids.request_unit', 'working_hours_mode')
    def _compute_calendar_source(self):
        non_hourly = self.filtered(lambda r: not r._is_hourly())
        non_hourly.calendar_source = False
        super(HrTimeRule, self - non_hourly)._compute_calendar_source()

    @api.depends('condition_work_entry_type_ids.request_unit', 'working_hours_mode')
    def _compute_expected_hours(self):
        non_hourly = self.filtered(lambda r: not r._is_hourly())
        non_hourly.expected_hours = 0
        super(HrTimeRule, self - non_hourly)._compute_expected_hours()

    @api.depends('condition_work_entry_type_ids.request_unit', 'working_hours_mode')
    def _compute_quantity_period(self):
        non_hourly = self.filtered(lambda r: not r._is_hourly())
        non_hourly.quantity_period = 'day'
        super(HrTimeRule, self - non_hourly)._compute_quantity_period()

    leave_compensation_rate = fields.Float(
        "Allocate %",
        default=0.0,
        help="Leave allocated or taken at this rate of the excess or deficit. 100% = 1:1.",
    )
    allocation_type_id = fields.Many2one(
        'hr.work.entry.type',
        string="Allocate to",
        domain="[('requires_allocation', '=', True), ('id', 'in', country_work_entry_type_ids)]",
    )

    def _resolve_output_intervals(self, intervals):
        """Resolve output intervals, then merge consecutive slices sharing a merge key."""
        resolved = super()._resolve_output_intervals(intervals)
        # each element: (_OutIv, merge_key)
        merged = []
        for iv in resolved:
            mk = iv.rule._get_output_leave_merge_key(accumulated_pp=iv.pp)
            if merged and merged[-1][0].end == iv.start and merged[-1][1] == mk:
                prev, _ = merged[-1]
                merged[-1] = (prev._replace(end=iv.end, pp=prev.pp | iv.pp), mk)
            else:
                merged.append((iv, mk))
        return [iv for iv, _mk in merged]

    def _get_output_leave_vals(self, employee, rule, date_from, date_to, source_leave, accumulated_pp=frozenset()):
        tz = ZoneInfo(employee._get_tz())
        df_local = date_from.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        dt_local = date_to.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return {
            'employee_id': employee.id,
            'work_entry_type_id': rule.work_entry_type_id.id,
            'date_from': date_from,
            'date_to': date_to,
            'request_date_from': df_local.date(),
            'request_date_to': dt_local.date(),
            'request_hour_from': df_local.hour + df_local.minute / 60,
            'request_hour_to': dt_local.hour + dt_local.minute / 60,
            'time_rule_id': rule.id,
            'source_leave_id': source_leave.id,
            'resource_calendar_id': source_leave.resource_calendar_id.id,
            'state': 'validate',
        }

    def _get_output_leave_merge_key(self, accumulated_pp=frozenset()):
        """Hashable key controlling when consecutive excess slices are merged into one leave.

        Override to add extra discriminators (e.g. premium pay rule sets in Belgium).
        """
        return self

    def _apply_leave_output(self, excess, deficit, active_iv=None):
        new_records, all_source_ids, excess_alloc, deficit_alloc = self._apply_output(excess, deficit, active_iv=active_iv)
        alloc_create_vals = []
        for employee, rule, excess_hours in excess_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            alloc_days = excess_hours * rule.leave_compensation_rate / hours_per_day
            if alloc_days <= 0:
                continue
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', rule.allocation_type_id.id),
                ('state', '=', 'validate'),
            ], limit=1)
            if allocation:
                allocation.number_of_days += alloc_days
            else:
                alloc_create_vals.append({
                    'employee_id': employee.id,
                    'work_entry_type_id': rule.allocation_type_id.id,
                    'number_of_days': alloc_days,
                    'state': 'confirm',
                })
        if alloc_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create(alloc_create_vals)
            new_allocs.with_context(leave_skip_state_check=True).action_approve()
        for employee, rule, deficit_hours in deficit_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            deduct_days = deficit_hours * rule.leave_compensation_rate / hours_per_day
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', rule.allocation_type_id.id),
                ('state', '=', 'validate'),
            ], limit=1)
            if allocation:
                allocation.number_of_days = max(0, allocation.number_of_days - deduct_days)
        if all_source_ids:
            Leave = self.env['hr.leave'].sudo()
            sources = Leave.with_context(active_test=False).browse(list(all_source_ids))
            (sources | new_records).with_context(**Leave._time_rule_write_ctx)._create_resource_leave()
