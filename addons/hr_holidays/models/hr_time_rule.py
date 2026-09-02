# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrTimeRuleSourceMixin(models.AbstractModel):
    _inherit = 'hr.time.rule.source.mixin'

    def _on_sources_collected(self, sources):
        """Reverse prior allocation credits before the batch is re-evaluated.
        """
        self.env['hr.time.rule']._reverse_allocation_credits(self._name, sources.ids)


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    work_entry_type_id = fields.Many2one(
        domain="[('id', 'in', allowed_output_work_entry_type_ids)]",
    )
    allowed_output_work_entry_type_ids = fields.Many2many(
        'hr.work.entry.type',
        compute='_compute_allowed_output_work_entry_type_ids',
    )
    condition_is_hourly = fields.Boolean(
        compute='_compute_condition_is_hourly',
        help="True when all selected condition time types are hourly (request_unit='hour').",
    )

    _OUTPUT_UNITS_ALLOWED = {
        'hour': {'hour'},
        'half_day': {'hour', 'half_day'},
        'day': {'hour', 'half_day', 'day'},
    }

    @api.depends('condition_work_entry_type_ids.request_unit', 'country_work_entry_type_ids')
    def _compute_allowed_output_work_entry_type_ids(self):
        for rule in self:
            units = rule.condition_work_entry_type_ids.mapped('request_unit')
            cond_unit = units[0] if units else 'hour'
            allowed = rule._OUTPUT_UNITS_ALLOWED.get(cond_unit, {'hour'})
            rule.allowed_output_work_entry_type_ids = rule.country_work_entry_type_ids.filtered(
                lambda t: not t.requires_allocation and t.request_unit in allowed
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
        domain="[('requires_allocation', '=', True), ('time_off_selectable', '=', True), ('id', 'in', country_work_entry_type_ids)]",
    )

    def _resolve_output_intervals(self, intervals):
        """Resolve output intervals, then merge consecutive slices sharing a merge key."""
        resolved = super()._resolve_output_intervals(intervals)
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

    def _apply_allocation_credits(self, excess_alloc, deficit_alloc, *, approve_ctx=None):
        """Translate excess/deficit hours into allocation credits and write the log.

        Time-rule allocations are always open-ended (date_to=False) so they don't
        collide with accrual or fixed-period allocations.

        approve_ctx -- extra context passed to action_approve on new allocations
                       (e.g. {'leave_skip_state_check': True})
        """
        approve_ctx = approve_ctx or {}
        search_domain = [('state', '=', 'validate'), ('date_to', '=', False)]

        excess_by_key = defaultdict(float)
        log_by_source = defaultdict(float)

        for employee, rule, excess_hours, source, log_source in excess_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            alloc_days = excess_hours * rule.leave_compensation_rate / hours_per_day
            if alloc_days > 0:
                excess_by_key[employee, rule.allocation_type_id] += alloc_days
                log_by_source[log_source._name, log_source.id, employee, rule.allocation_type_id] += alloc_days

        alloc_by_key = {}
        alloc_create_vals = []
        alloc_create_keys = []
        for (employee, alloc_type), alloc_days in excess_by_key.items():
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', alloc_type.id),
                *search_domain,
            ], limit=1)
            if allocation:
                allocation.number_of_days += alloc_days
                alloc_by_key[employee, alloc_type] = allocation
            else:
                alloc_create_vals.append({
                    'employee_id': employee.id,
                    'work_entry_type_id': alloc_type.id,
                    'number_of_days': alloc_days,
                    'date_to': False,
                    'state': 'confirm',
                })
                alloc_create_keys.append((employee, alloc_type))
        if alloc_create_vals:
            new_allocs = self.env['hr.leave.allocation'].sudo().with_context(skip_time_rules=True).create(alloc_create_vals)
            new_allocs.with_context(**approve_ctx).action_approve()
            for key, alloc in zip(alloc_create_keys, new_allocs):
                alloc_by_key[key] = alloc

        deficit_by_key = defaultdict(float)
        for employee, rule, deficit_hours, source, log_source in deficit_alloc:
            if not (rule.leave_compensation_rate > 0 and rule.allocation_type_id):
                continue
            hours_per_day = employee.resource_calendar_id.hours_per_day or 8.0
            deduct = deficit_hours * rule.leave_compensation_rate / hours_per_day
            if deduct > 0:
                deficit_by_key[employee, rule.allocation_type_id] += deduct
                log_by_source[log_source._name, log_source.id, employee, rule.allocation_type_id] -= deduct

        for (employee, alloc_type), deduct in deficit_by_key.items():
            allocation = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', employee.id),
                ('work_entry_type_id', '=', alloc_type.id),
                *search_domain,
            ], limit=1)
            if allocation:
                allocation.number_of_days = max(0, allocation.number_of_days - deduct)
                alloc_by_key.setdefault((employee, alloc_type), allocation)

        log_vals = []
        for (source_model, source_id, employee, alloc_type), days in log_by_source.items():
            allocation = alloc_by_key.get((employee, alloc_type))
            if allocation and days:
                log_vals.append({
                    'source_model': source_model,
                    'source_id': source_id,
                    'allocation_id': allocation.id,
                    'days': days,
                })
        if log_vals:
            self.env['hr.time.rule.allocation.log'].sudo().create(log_vals)

    def _apply_leave_output(self, excess, deficit, active_iv=None):
        new_records, all_source_ids, excess_alloc, deficit_alloc = self._apply_output(excess, deficit, active_iv=active_iv)
        self._apply_allocation_credits(
            excess_alloc, deficit_alloc,
            approve_ctx={'leave_skip_state_check': True},
        )
        if all_source_ids:
            Leave = self.env['hr.leave'].sudo()
            sources = Leave.with_context(active_test=False).browse(list(all_source_ids))
            (sources | new_records).with_context(**Leave._time_rule_write_ctx)._create_resource_leave()

    @api.model
    def _reverse_allocation_credits(self, source_model, source_ids):
        """subtract credits logged for the given source records."""
        if not source_ids:
            return
        Log = self.env['hr.time.rule.allocation.log'].sudo()
        logs = Log.search([
            ('source_model', '=', source_model),
            ('source_id', 'in', list(source_ids)),
        ])
        if not logs:
            return
        by_alloc = defaultdict(float)
        for log in logs:
            by_alloc[log.allocation_id] += log.days
        errors = []
        for allocation, days in by_alloc.items():
            if not allocation.exists() or not days:
                continue
            wet = allocation.work_entry_type_id
            allowed_floor = -wet.max_allowed_negative if wet.allows_negative else 0.0
            remaining_after = allocation.virtual_remaining_leaves - days
            if remaining_after < allowed_floor:
                errors.append(self.env._(
                    "Cannot reverse %(days).4g day(s) from '%(leave_type)s' allocation "
                    "for %(employee)s: available balance is %(balance).4g day(s) and would "
                    "drop to %(after).4g day(s), below the allowed minimum of %(floor).4g. "
                    "Refuse or reduce taken leaves first, or adjust the allocation manually, "
                    "then retry.",
                    days=days,
                    leave_type=wet.name,
                    employee=allocation.employee_id.name,
                    balance=allocation.virtual_remaining_leaves,
                    after=remaining_after,
                    floor=allowed_floor,
                ))
        if errors:
            raise ValidationError('\n'.join(errors))
        for allocation, days in by_alloc.items():
            if not allocation.exists() or not days:
                continue
            allocation.number_of_days -= days
        logs.unlink()
