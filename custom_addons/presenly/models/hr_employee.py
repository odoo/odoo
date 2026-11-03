from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


DAY_LOCATION_FIELDS = [
    'monday_location_id', 'tuesday_location_id', 'wednesday_location_id',
    'thursday_location_id', 'friday_location_id', 'saturday_location_id',
    'sunday_location_id',
]


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _attendance_action_change(self, geo_information=None):
        """Disable Odoo kiosk, barcode/RFID, and systray attendance mutation."""
        raise ValidationError(_(
            'Native Odoo check-in and check-out are disabled. '
            'Use the Presenly mobile application.'
        ))

    presenly_schedule_ids = fields.One2many(
        'presenly.work.location.schedule', 'employee_id',
        string='Work Location Schedules',
    )
    presenly_schedule_count = fields.Integer(
        compute='_compute_presenly_schedule_count', string='Location Schedules',
    )
    presenly_schedule_health = fields.Selection([
        ('synced', 'Fully Assigned'),
        ('partial', 'Working Hours Have Gaps'),
        ('conflict', 'Schedule Conflict'),
        ('flexible', 'Flexible Working Hours'),
        ('no_calendar', 'No Working Hours'),
    ], compute='_compute_presenly_schedule_health', string='Location Coverage')
    presenly_schedule_health_message = fields.Char(
        compute='_compute_presenly_schedule_health',
        string='Location Coverage Details',
    )
    presenly_schedule_gap_count = fields.Integer(
        compute='_compute_presenly_schedule_health', string='Unassigned Periods',
    )
    presenly_schedule_conflict_count = fields.Integer(
        compute='_compute_presenly_schedule_health', string='Conflicting Slots',
    )

    @api.depends('presenly_schedule_ids')
    def _compute_presenly_schedule_count(self):
        grouped = self.env['presenly.work.location.schedule'].sudo()._read_group(
            [('employee_id', 'in', self.ids)],
            ['employee_id'],
            ['__count'],
        ) if self.ids else []
        counts = {employee.id: count for employee, count in grouped}
        for employee in self:
            employee.presenly_schedule_count = counts.get(employee.id, 0)

    @api.depends(
        'presenly_schedule_ids.active', 'presenly_schedule_ids.schedule_type',
        'presenly_schedule_ids.weekday', 'presenly_schedule_ids.week_type',
        'presenly_schedule_ids.hour_from', 'presenly_schedule_ids.hour_to',
        'current_version_id', 'current_version_id.resource_calendar_id',
        'current_version_id.resource_calendar_id.flexible_hours',
        'current_version_id.resource_calendar_id.two_weeks_calendar',
        'current_version_id.resource_calendar_id.attendance_ids.dayofweek',
        'current_version_id.resource_calendar_id.attendance_ids.week_type',
        'current_version_id.resource_calendar_id.attendance_ids.hour_from',
        'current_version_id.resource_calendar_id.attendance_ids.hour_to',
        'current_version_id.resource_calendar_id.attendance_ids.day_period',
        'current_version_id.resource_calendar_id.attendance_ids.display_type',
    )
    def _compute_presenly_schedule_health(self):
        schedule_model = self.env['presenly.work.location.schedule']
        for employee in self:
            calendar = employee.sudo().resource_calendar_id
            employee.presenly_schedule_gap_count = 0
            employee.presenly_schedule_conflict_count = 0
            if not calendar:
                employee.presenly_schedule_health = 'no_calendar'
                employee.presenly_schedule_health_message = (
                    'Select Working Hours before assigning Work Locations.'
                )
                continue
            if calendar.flexible_hours:
                employee.presenly_schedule_health = 'flexible'
                employee.presenly_schedule_health_message = (
                    'Flexible Working Hours use the primary/native Work Location fallback.'
                )
                continue

            weekly_slots = employee.presenly_schedule_ids.filtered(
                lambda slot: slot.active and slot.schedule_type == 'weekly'
            )
            conflicts = weekly_slots.filtered(
                lambda slot: not slot._presenly_is_within_working_hours()
            )
            gaps = []
            for period in schedule_model._calendar_template_periods(employee):
                matching = weekly_slots.filtered(
                    lambda slot: slot.weekday == period['weekday']
                    and (slot.week_type or False) == (period['week_type'] or False)
                    and slot._presenly_is_within_working_hours()
                    and slot.hour_from < period['hour_to']
                    and slot.hour_to > period['hour_from']
                )
                cursor = period['hour_from']
                for slot in matching.sorted('hour_from'):
                    if slot.hour_from > cursor + 0.000001:
                        gaps.append((period, cursor, slot.hour_from))
                    cursor = max(cursor, min(slot.hour_to, period['hour_to']))
                if cursor < period['hour_to'] - 0.000001:
                    gaps.append((period, cursor, period['hour_to']))

            employee.presenly_schedule_gap_count = len(gaps)
            employee.presenly_schedule_conflict_count = len(conflicts)
            if conflicts:
                employee.presenly_schedule_health = 'conflict'
                employee.presenly_schedule_health_message = (
                    f'{len(conflicts)} location slot(s) are outside the current '
                    'Working Hours and are ignored by attendance resolution.'
                )
            elif gaps:
                employee.presenly_schedule_health = 'partial'
                employee.presenly_schedule_health_message = (
                    f'{len(gaps)} Working Hours period(s) still need a Work Location.'
                )
            else:
                employee.presenly_schedule_health = 'synced'
                employee.presenly_schedule_health_message = (
                    'Every regular Working Hours period has a Work Location.'
                )

    def _presenly_active_schedules(self):
        """Read technical schedule data only for this validated employee."""
        self.ensure_one()
        schedules = self.env['presenly.work.location.schedule'].sudo().search([
            ('employee_id', '=', self.id),
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
            ('work_location_id.active', '=', True),
            ('work_location_id.company_id', '=', self.company_id.id),
        ])
        return schedules.filtered(
            lambda schedule: schedule._presenly_is_within_working_hours()
        )

    def _presenly_local_datetime(self, value=None):
        self.ensure_one()
        value = fields.Datetime.to_datetime(value or fields.Datetime.now())
        timezone = self._get_tz() or self.env.user.tz or 'UTC'
        return fields.Datetime.context_timestamp(
            self.with_context(tz=timezone), value,
        )

    def _presenly_schedule_resolution(self, value=None):
        """Return matching slots and whether this moment is schedule-controlled.

        Specific-date slots replace weekly slots for that date. Weekly slots
        replace native one-location-per-day configuration for that weekday. If
        slots exist for the day but none match the current time, no fallback is
        returned, so attendance outside scheduled hours is rejected.
        """
        self.ensure_one()
        local_datetime = self._presenly_local_datetime(value)
        target_date = local_datetime.date()
        schedules = self._presenly_active_schedules()
        date_slots = schedules.filtered(
            lambda slot: slot.schedule_type == 'date'
            and slot.schedule_date == target_date
        )
        candidates = date_slots
        if not date_slots:
            candidates = schedules.filtered(
                lambda slot: slot.schedule_type == 'weekly'
                and slot._covers_date(target_date)
            )
        return candidates.filtered(
            lambda slot: slot._matches_local_datetime(local_datetime)
        ), bool(candidates)

    def _presenly_locations_at(self, value=None):
        self.ensure_one()
        slots, controlled = self._presenly_schedule_resolution(value)
        if controlled:
            return slots.mapped('work_location_id'), slots

        local_date = self._presenly_local_datetime(value).date()
        exception = self.env['hr.employee.location'].sudo().search([
            ('employee_id', '=', self.id),
            ('date', '=', local_date),
        ], limit=1).work_location_id
        if exception and exception.active and exception.company_id == self.company_id:
            return exception, self.env['presenly.work.location.schedule']

        daily_location = self[DAY_LOCATION_FIELDS[local_date.weekday()]]
        if (
            daily_location and daily_location.active
            and daily_location.company_id == self.company_id
        ):
            return daily_location, self.env['presenly.work.location.schedule']

        if (
            self.work_location_id and self.work_location_id.active
            and self.work_location_id.company_id == self.company_id
        ):
            return self.work_location_id, self.env['presenly.work.location.schedule']
        return self.env['hr.work.location'], self.env['presenly.work.location.schedule']

    def _presenly_work_locations_for_period(self, date_from=None, date_to=None):
        self.ensure_one()
        # Employee location fields are related through hr.version and may be
        # field-restricted for a regular employee in Odoo 19. This internal
        # resolver is already scoped to one validated Employee record, so read
        # only that Employee's technical location configuration with sudo and
        # keep the explicit employee/company filters below.
        employee = self.sudo()
        date_from = fields.Date.to_date(
            date_from or fields.Date.context_today(employee)
        )
        date_to = fields.Date.to_date(date_to or date_from)
        locations = employee.env['hr.work.location']
        active_slots = employee._presenly_active_schedules()
        current = date_from
        while current <= date_to:
            date_slots = active_slots.filtered(
                lambda slot: slot.schedule_type == 'date'
                and slot.schedule_date == current
            )
            day_slots = date_slots or active_slots.filtered(
                lambda slot: slot.schedule_type == 'weekly'
                and slot._covers_date(current)
            )
            if day_slots:
                locations |= day_slots.mapped('work_location_id')
            else:
                exception = employee.env['hr.employee.location'].sudo().search([
                    ('employee_id', '=', employee.id), ('date', '=', current),
                ], limit=1).work_location_id
                daily = exception or employee[
                    DAY_LOCATION_FIELDS[current.weekday()]
                ]
                if daily:
                    locations |= daily
                elif employee.work_location_id:
                    locations |= employee.work_location_id
            current += timedelta(days=1)
        return locations.filtered(
            lambda location: location.active
            and location.company_id == employee.company_id
        )

    def _presenly_resolve_period_location(
        self, date_from=None, date_to=None, hour_from=None, hour_to=None,
    ):
        """Resolve ONE Work Location for a request period.

        Returns ``(location, by_date, ambiguous, error)``:
        - ``location``: the unique recommended location for the whole period
          (``hr.work.location``) or empty recordset.
        - ``by_date``: dict ``{date(iso): {'id': ..., 'name': ...}}`` mapping
          every day in the period to its resolved location (for UI transparency
          and K1 error detail).
        - ``ambiguous``: True when the period spans MORE than one location (K1).
        - ``error``: message describing a missing-location day, or False.

        Policies applied:
        - K2 (default / full-day): when several slots exist on one day, the
          first slot by (hour_from, id) wins.
        - K2b (partial-hours): when ``hour_from``/``hour_to`` are given, prefer
          a slot overlapping that time range; fall back to the first slot.
        - K1: does NOT raise here; returns ``(empty, by_date, True, False)`` so
          the caller can reject with per-date details.

        Follows the same visibility rules as ``_presenly_work_locations_for_period``
        (sudo, scoped to employee + company, active filter).
        """
        self.ensure_one()
        employee = self.sudo()
        date_from = fields.Date.to_date(
            date_from or fields.Date.context_today(employee)
        )
        date_to = fields.Date.to_date(date_to or date_from)
        if hour_from is not None:
            hour_from = float(hour_from)
            hour_to = float(hour_to) if hour_to is not None else hour_from

        active_slots = employee._presenly_active_schedules()
        by_date = {}
        error = False
        current = date_from
        while current <= date_to:
            date_slots = active_slots.filtered(
                lambda slot: slot.schedule_type == 'date'
                and slot.schedule_date == current
            )
            day_slots = date_slots or active_slots.filtered(
                lambda slot: slot.schedule_type == 'weekly'
                and slot._covers_date(current)
            )
            if day_slots:
                ordered = day_slots.sorted(lambda s: (s.hour_from, s.id))
                if hour_from is not None:
                    overlapping = ordered.filtered(
                        lambda s: s.hour_from <= hour_to
                        and s.hour_to >= hour_from
                    )
                    selected = (overlapping or ordered)[:1]
                else:
                    selected = ordered[:1]
                location = selected.work_location_id
            else:
                exception = employee.env['hr.employee.location'].sudo().search([
                    ('employee_id', '=', employee.id), ('date', '=', current),
                ], limit=1).work_location_id
                daily = exception or employee[
                    DAY_LOCATION_FIELDS[current.weekday()]
                ]
                location = daily or employee.work_location_id
                if (
                    not location
                    or not location.active
                    or location.company_id != employee.company_id
                ):
                    location = employee.env['hr.work.location']
            if not location:
                error = error or (
                    'No Work Location is configured for %s.'
                    % fields.Date.to_string(current)
                )
                by_date[fields.Date.to_string(current)] = {
                    'id': False, 'name': False,
                }
            else:
                by_date[fields.Date.to_string(current)] = {
                    'id': location.id, 'name': location.name,
                }
            current += timedelta(days=1)

        unique_ids = {entry['id'] for entry in by_date.values() if entry['id']}
        if not unique_ids:
            return (
                employee.env['hr.work.location'], by_date, False,
                error or 'No Work Location is configured for this period.',
            )
        if len(unique_ids) == 1:
            location = employee.env['hr.work.location'].browse(
                unique_ids.pop()
            )
            return location, by_date, False, error
        return employee.env['hr.work.location'], by_date, True, error

    def action_open_presenly_schedules(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'presenly.action_presenly_work_location_schedule'
        )
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action

    def action_generate_presenly_schedules(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Generate Locations from Working Hours',
            'res_model': 'presenly.schedule.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_employee_id': self.id},
        }

    def action_open_presenly_working_hours(self):
        self.ensure_one()
        calendar = self.resource_calendar_id
        if not calendar:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Working Hours',
                'res_model': 'resource.calendar',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_company_id': self.company_id.id,
                    'default_name': f'{self.name} Working Hours',
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': f'Working Hours - {self.name}',
            'res_model': 'resource.calendar',
            'res_id': calendar.id,
            'view_mode': 'form',
            'target': 'current',
        }
