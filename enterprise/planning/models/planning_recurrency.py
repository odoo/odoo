# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz
from calendar import monthrange
from datetime import datetime, timedelta


from odoo import api, fields, models, _
from odoo.tools import get_timedelta
from odoo.exceptions import ValidationError


class PlanningRecurrency(models.Model):
    _name = 'planning.recurrency'
    _description = "Planning Recurrence"

    slot_ids = fields.One2many('planning.slot', 'recurrency_id', string="Related Planning Entries")
    repeat_interval = fields.Integer("Repeat Every", default=1, required=True)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', required=True)
    repeat_type = fields.Selection([('forever', 'Forever'), ('until', 'Until'), ('x_times', 'Number of Repetitions')], string='Weeks', default='forever')
    repeat_until = fields.Datetime(string="Repeat Until", help="Up to which date should the plannings be repeated")
    repeat_number = fields.Integer(string="Repetitions", help="No Of Repetitions of the plannings")
    last_generated_end_datetime = fields.Datetime(readonly=True, export_string_translation=False)
    company_id = fields.Many2one('res.company', string="Company", readonly=True, required=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('check_repeat_interval_positive', 'CHECK(repeat_interval >= 1)', 'The recurrence should be greater than 0.'),
        ('check_until_limit', "CHECK((repeat_type = 'until' AND repeat_until IS NOT NULL) OR (repeat_type != 'until'))", 'A recurrence repeating itself until a certain date must have its limit set'),
    ]

    @api.constrains('repeat_number', 'repeat_type')
    def _check_repeat_number(self):
        if self.filtered(lambda t: t.repeat_type == 'x_times' and t.repeat_number < 0):
            raise ValidationError(_('The number of repetitions cannot be negative.'))

    @api.constrains('company_id', 'slot_ids')
    def _check_multi_company(self):
        for recurrency in self:
            if any(recurrency.company_id != planning.company_id for planning in recurrency.slot_ids):
                raise ValidationError(_('A shift must be in the same company as its recurrence.'))

    @api.depends('repeat_type', 'repeat_interval', 'repeat_until')
    def _compute_display_name(self):
        for recurrency in self:
            if recurrency.repeat_type == 'forever':
                name = _('Forever, every %s week(s)', recurrency.repeat_interval)
            else:
                name = _('Every %(repeat_interval)s week(s) until %(repeat_until)s', repeat_interval=recurrency.repeat_interval, repeat_until=recurrency.repeat_until)
            recurrency.display_name = name

    @api.model
    def _cron_schedule_next(self):
        companies = self.env['res.company'].search([])
        now = fields.Datetime.now()
        for company in companies:
            delta = get_timedelta(company.planning_generation_interval, 'month')

            recurrencies = self.search([
                '&',
                '&',
                ('company_id', '=', company.id),
                ('last_generated_end_datetime', '<', now + delta),
                '|',
                ('repeat_until', '=', False),
                ('repeat_until', '>', now - delta),
            ])
            recurrencies._repeat_slot(now + delta)

    def _repeat_slot(self, stop_datetime=False):
        PlanningSlot = self.env['planning.slot']
        for recurrency in self:
            slot = PlanningSlot.search([('recurrency_id', '=', recurrency.id)], limit=1, order='start_datetime DESC')

            if slot:
                # find the end of the recurrence
                recurrence_end_dt = False
                if recurrency.repeat_type == 'until':
                    recurrence_end_dt = recurrency.repeat_until

                # find end of generation period (either the end of recurrence (if this one ends before the cron period), or the given `stop_datetime` (usually the cron period))
                recurrency_stop_datetime = stop_datetime or PlanningSlot._add_delta_with_dst(
                    fields.Datetime.now(),
                    get_timedelta(recurrency.company_id.planning_generation_interval, 'month')
                )
                misc_recurrence_stop = recurrency._get_misc_recurrence_stop()
                range_limit = min([dt for dt in [recurrence_end_dt, recurrency_stop_datetime, misc_recurrence_stop] if dt])
                slot_duration = slot.end_datetime - slot.start_datetime

                # add timezone information to the start and end of the recurrence duration (needed for company / resource availability computation)
                start_duration = slot.start_datetime.replace(tzinfo=pytz.utc)
                end_duration = range_limit.replace(tzinfo=pytz.utc)

                # get the company's work intervals as well as the public holidays
                company_calendar_working_days = recurrency.company_id.resource_calendar_id._work_intervals_batch(start_duration, end_duration)[False]

                # get the resource of the recurring shift
                resource = recurrency.slot_ids.resource_id[-1:]

                # We check whether the slot was generated outisde working days (includes public holidays), if so we will generate the recurrent slots normally
                days_of_slot = {slot.start_datetime.date() + timedelta(days=i) for i in range(slot_duration.days + 1)}
                is_slot_outside_working_days = not days_of_slot <= {start.date() for start, stop, dummy in company_calendar_working_days}

                def can_slot_be_generated(next_start):
                    next_start_utc = next_start.replace(tzinfo=pytz.utc)
                    lands_on_working_day = any(
                        next_start_utc.date() == start.date()
                        for start, stop, dummy in company_calendar_working_days
                    )
                    return lands_on_working_day or (resource and resource._is_flexible()) or is_slot_outside_working_days

                def get_all_next_starts():
                    generated_recurrency_slots = -1
                    if recurrency.repeat_type == "x_times":
                        generated_recurrency_slots = self.env['planning.slot'].search_count([('recurrency_id', '=', recurrency.id)])
                    for i in range(1, 365 * 5):  # 5 years if every day
                        next_start = PlanningSlot._add_delta_with_dst(
                            slot.start_datetime,
                            get_timedelta(recurrency.repeat_interval * i, recurrency.repeat_unit)
                        )
                        if not can_slot_be_generated(next_start):
                            continue
                        if next_start >= range_limit or generated_recurrency_slots >= recurrency.repeat_number:
                            return
                        generated_recurrency_slots += recurrency.repeat_type == "x_times"
                        yield next_start

                # generate recurring slots
                occurring_slots = PlanningSlot.search_read([
                    ('resource_id', '=', resource.id),
                    ('company_id', '=', resource.company_id.id),
                    ('end_datetime', '>=', slot.start_datetime),
                    ('start_datetime', '<=', range_limit)
                ], ['start_datetime', 'end_datetime', 'allocated_hours'])

                # get the resource's availability intervals
                resource_availability = resource._get_valid_work_intervals(start_duration, end_duration)[0][resource.id]

                # We check whether the slot was generated outisde working hours, if so we will assign the recurrent slots as well
                is_slot_outside_working_hours = all(
                    slot.start_datetime.replace(tzinfo=pytz.utc) >= stop or
                    slot.end_datetime.replace(tzinfo=pytz.utc) <= start
                    for start, stop, dummy in resource_availability
                )

                def can_slot_be_assigned(next_start, next_end):
                    next_start_utc = next_start.replace(tzinfo=pytz.utc)
                    next_end_utc = next_end.replace(tzinfo=pytz.utc)
                    # First we will check whether the resource is busy - we begin by collecting all overlapping slots
                    is_resource_busy = False
                    overlapping_slots = [
                        occurring_slot
                        for occurring_slot in occurring_slots
                        if (
                            next_start <= occurring_slot['end_datetime'] and
                            next_end >= occurring_slot['start_datetime']
                        )
                    ] + [{'start_datetime': next_start, 'end_datetime': next_end, 'allocated_hours': slot.allocated_hours}]  # we do this to include the current slot in the overlapping slots
                    # If we have overlapping slots, we check whether the resource is fully busy by comparing the planned hours to the total hours in the overlap period
                    if len(overlapping_slots) > 1:  # check that we have more than one overlapping slot (the first is always the one being planned)
                        earliest_start = min([overlapping_slot['start_datetime'] for overlapping_slot in overlapping_slots])
                        latest_end = max([overlapping_slot['end_datetime'] for overlapping_slot in overlapping_slots])
                        total_hours_planned = sum([slot['allocated_hours'] for slot in overlapping_slots])
                        total_hours_in_overlap = (latest_end - earliest_start).total_seconds() / 3600
                        if not resource._is_fully_flexible():
                            is_resource_busy = total_hours_planned > total_hours_in_overlap
                    # Then we check whether the resource is working at that time (they have intervals or are flexible)
                    # (if the initial shift is planned outside working hours, then the recurring shifts will be normaly assigned)
                    is_resource_working = any(
                        next_start_utc <= stop and
                        next_end_utc >= start
                        for start, stop, dummy in resource_availability
                    ) or resource and resource._is_flexible()
                    return (is_resource_working or is_slot_outside_working_hours) and not is_resource_busy

                slot_values_list = []
                for next_start in get_all_next_starts():
                    next_end = next_start + slot_duration
                    # Check that the duration is not longer than the month of the start to avoid overlapping slots
                    if slot.repeat_unit == 'month':
                        days_in_month = monthrange(next_start.year, next_start.month)[1]
                        if slot_duration.days >= days_in_month:
                            next_end -= timedelta(days=slot_duration.days - (days_in_month - 1))
                    slot_values = slot.copy_data({
                        'start_datetime': next_start,
                        'end_datetime': next_end,
                        'recurrency_id': recurrency.id,
                        'company_id': recurrency.company_id.id,
                        'repeat': True,
                        'state': 'draft'
                    })[0]
                    if not can_slot_be_assigned(next_start, next_end):
                        slot_values['resource_id'] = False
                    slot_values_list.append(slot_values)
                if slot_values_list:
                    PlanningSlot.create(slot_values_list)
                    recurrency.write({'last_generated_end_datetime': slot_values_list[-1]['start_datetime']})

            else:
                recurrency.unlink()

    def _delete_slot(self, start_datetime):
        slots = self.env['planning.slot'].search([
            ('recurrency_id', 'in', self.ids),
            ('start_datetime', '>=', start_datetime),
            ('state', '=', 'draft'),
        ])
        slots.unlink()

    def _get_misc_recurrence_stop(self):
        """
        If there are additional limitations on until when the recurring shifts can be generated, this method will return the
        earliest date after which shifts cannot be generated under this additional limitation.

        By default, we generate recurring shifts until the repeat_until date specified by the user or for 6 months in the future.
        If there are any additional limitations that prevent us from generating the slot until either of those two datetimes, they
        should be returned here.

        Example: this method is extended in the planning_contract module - to plan until the end of the contract period. That way,
        if we plan a shift on 1/1/25 to repeat weekly until 1/4/25 but the resource's contract ends in 1/3/25, we will only repeat the
        slot until 1/3/25 and not until 1/4/25. This method should thus return the detatime 1/3/25 23:59:59.
        """
        return datetime.max
