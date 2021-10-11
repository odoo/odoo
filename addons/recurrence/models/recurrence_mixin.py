# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import pytz
from datetime import timedelta

from odoo.addons.base.models.res_partner import _tz_get
from odoo import api, models, fields, _
from odoo.addons.recurrence.models.recurrence_recurrence import weekday_to_field, RRULE_TYPE_SELECTION, END_TYPE_SELECTION, MONTH_BY_SELECTION, WEEKDAY_SELECTION, BYDAY_SELECTION
from odoo.exceptions import UserError


def get_weekday_occurence(date):
    """
    :returns: ocurrence

    >>> get_weekday_occurence(date(2019, 12, 17))
    3  # third Tuesday of the month

    >>> get_weekday_occurence(date(2019, 12, 25))
    -1  # last Friday of the month
    """
    occurence_in_month = math.ceil(date.day/7)
    if occurence_in_month in {4, 5}:  # fourth or fifth week on the month -> last
        return -1
    return occurence_in_month


class RecurrenceMixin(models.AbstractModel):
    """ Inherit this mixin if you want your model to be able to create recurrent records
    Public methods are prefixed with ``recurrence_`` in order to avoid name
        collisions with methods of the models that will inherit from this class.
    """
    _name = 'recurrence.mixin'
    _description = "Recurrence Mixin"

    @api.model
    def _default_batch(self):
        return False

    @api.model
    def _default_next_recurrence_interval(self):
        """Number of month between batch of records
        This method must be overridden when batch creation is needed.
        """
        return 0

    active = fields.Boolean('Active', default=True)
    start_datetime = fields.Datetime(
        'Start', required=True, default=fields.Date.today)
    stop_datetime = fields.Datetime(
        'Stop', required=True, default=lambda self: fields.Datetime.today() + timedelta(hours=1))
    duration = fields.Float('Duration', compute='_compute_duration', store=True, readonly=False)
    recurrence_id = fields.Many2one('recurrence.recurrence', string="Recurrence Rule", index=True)
    recurrency = fields.Boolean('Recurrent')
    follow_recurrence = fields.Boolean(
        default=False)  # Indicates if a record follows the recurrence, i.e. is not an exception
    recurrence_update = fields.Selection([
        ('self_only', "This record"),
        ('future_records', "This and following records"),
        ('all_records', "All records"),
    ], store=False, copy=False, default='self_only',
       help="Choose what to do with other events in the recurrence")

    # Those field are pseudo-related fields of recurrence_id.
    # They can't be "real" related fields because it should work at record creation
    # when recurrence_id is not created yet.
    # If some of these fields are set and recurrence_id does not exists,
    # a `recurrence.recurrence.rule` will be dynamically created.
    rrule = fields.Char('Recurrent Rule', compute='_compute_recurrence', readonly=False)
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, string='Recurrence',
                                  help="Let the event automatically repeat at that interval",
                                  compute='_compute_recurrence', readonly=False)
    record_tz = fields.Selection(
        _tz_get, string='Timezone', compute='_compute_recurrence', readonly=False)
    end_type = fields.Selection(
        END_TYPE_SELECTION, string='Recurrence Termination',
        compute='_compute_recurrence', readonly=False)
    interval = fields.Integer(
        string='Repeat Every', compute='_compute_recurrence', readonly=False,
        help="Repeat every (Days/Week/Month/Year)")
    count = fields.Integer(
        string='Repeat', help="Repeat x times", compute='_compute_recurrence', readonly=False)
    mon = fields.Boolean(compute='_compute_recurrence', readonly=False)
    tue = fields.Boolean(compute='_compute_recurrence', readonly=False)
    wed = fields.Boolean(compute='_compute_recurrence', readonly=False)
    thu = fields.Boolean(compute='_compute_recurrence', readonly=False)
    fri = fields.Boolean(compute='_compute_recurrence', readonly=False)
    sat = fields.Boolean(compute='_compute_recurrence', readonly=False)
    sun = fields.Boolean(compute='_compute_recurrence', readonly=False)
    month_by = fields.Selection(
        MONTH_BY_SELECTION, string='Option', compute='_compute_recurrence', readonly=False)
    day = fields.Integer('Date of month', compute='_compute_recurrence', readonly=False)
    weekday = fields.Selection(WEEKDAY_SELECTION, compute='_compute_recurrence', readonly=False)
    byday = fields.Selection(BYDAY_SELECTION, compute='_compute_recurrence', readonly=False)
    until = fields.Date(compute='_compute_recurrence', readonly=False)
    next_recurrence_interval = fields.Integer(default=lambda s: s._default_next_recurrence_interval(),
                                              compute='_compute_next_recurrence_interval')
    allday = fields.Boolean('All Day', default=False)

    @api.depends('recurrence_id', 'recurrency')
    def _compute_recurrence(self):
        recurrence_fields = self._get_recurrent_fields()
        false_values = {field: False for field in recurrence_fields}  # computes need to set a value
        defaults = self.env['recurrence.recurrence'].default_get(recurrence_fields)
        for record in self:
            if record.recurrency:
                record_values = record._get_recurrence_params()
                rrule_values = {
                    field: record.recurrence_id[field]
                    for field in recurrence_fields
                    if record.recurrence_id[field]
                }
                record.update({**false_values, **defaults, **record_values, **rrule_values})
            else:
                record.update(false_values)

    @api.depends('stop_datetime', 'start_datetime')
    def _compute_duration(self):
        for event in self:
            event.duration = self._get_duration(event.start_datetime, event.stop_datetime)

    def _compute_next_recurrence_interval(self):
        for record in self:
            record.next_recurrence_interval = 0

    @api.model
    def _get_duration(self, start_datetime, stop_datetime):
        """ Get the duration value between the 2 given dates. """
        if not start_datetime or not stop_datetime:
            return 0
        duration = (stop_datetime - start_datetime).total_seconds() / 3600
        return round(duration, 2)

    @api.model
    def _get_recurrent_fields(self):
        return {'byday', 'until', 'rrule_type', 'month_by', 'record_tz', 'rrule',
                'interval', 'count', 'end_type', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat',
                'sun', 'day', 'weekday'}

    @api.model
    def _get_time_fields(self):
        return {'start_datetime', 'stop_datetime'}

    def _range(self):
        self.ensure_one()
        return self.start_datetime, self.stop_datetime

    # ------------------------------------------------------------
    # RECURRENCE
    # ------------------------------------------------------------
    def _apply_recurrence_values(self, values, future=True):
        """Apply the new recurrence rules in `values`. Create a recurrence if it does not exist
        and create all missing events according to the rrule.
        If the changes are applied to future
        events only, a new recurrence is created with the updated rrule.

        :param values: new recurrence values to apply
        :param future: rrule values are applied to future events only if True.
                       Rrule changes are applied to all events in the recurrence otherwise.
                       (ignored if no recurrence exists yet).
        :return: events detached from the recurrence
        """
        if not values:
            return self.browse()
        model_name = self._get_recurrent_record_name()
        recurrence_vals = []
        to_update = self.env['recurrence.recurrence']
        detached_records = self.env[model_name]
        for record in self:
            event_rec_vals = record._get_recurrency_vals()
            if not record.recurrence_id:
                model = self._get_recurrent_record_name()
                recurrence_vals += [dict(values, **event_rec_vals, model=model, base_id=record.id, batch=self.env[self._name]._default_batch())]
            elif future:
                new_recurrence, split_records = record.recurrence_id._split_from(record, values)
                to_update |= new_recurrence
                detached_records |= split_records
        to_update |= self.env['recurrence.recurrence'].create(recurrence_vals)
        for rec in to_update:
            record = self.env[rec.model].browse(rec.base_id)
            values = {'recurrency': True, 'follow_recurrence': True, 'recurrence_id': rec.id}
            # Keep the base event and modifies his start_datetime to match the first event day
            keep_base = self._keep_initiator()
            if keep_base:
                duration = record.stop_datetime - record.start_datetime
                ranges = list(rec._range_calculation(record, duration, bypass_batch=True))
                ranges.sort()
                start = ranges and ranges[0][0]
                if start:
                    values.update(start_datetime=start, stop_datetime=start + duration)
                # arj fixme: add a test for this behavior once it is approved
            record.write(values)
        detached_records |= to_update._apply_recurrence(model=model_name, keep_base=keep_base)
        return detached_records

    def _get_recurrency_vals(self):
        """ This method is called when a recurrency must be updated according to values not present in the recurrence
        mixin.
        For example, if one want to update the recurrence according to the record company.
        As some model do not have a company field, this method must be overriden.
        :return: dict: needed values to update the recurrence
        """
        self.ensure_one()
        return {}

    def _get_recurrence_params(self):
        if not self:
            return {}
        event_date = self._get_start_date()
        weekday_field_name = weekday_to_field(event_date.weekday())
        return {
            weekday_field_name: True,
            'weekday': weekday_field_name.upper(),
            'byday': str(get_weekday_occurence(event_date)),
            'day': event_date.day,
        }

    def _split_recurrence(self, time_values):
        """Apply time changes to events and update the recurrence accordingly.

        :return: detached events
        """
        self.ensure_one()
        if not time_values:
            return self.browse()
        if self.follow_recurrence and self.recurrency:
            previous_week_day_field = weekday_to_field(self._get_start_date().weekday())
        else:
            # When we try to change recurrence values of an event not following the recurrence, we get the parameters from
            # the base_event
            previous_week_day_field = weekday_to_field(self.recurrence_id.base_id._get_start_date().weekday())
        self.write({**time_values})
        return self._apply_recurrence_values({
            previous_week_day_field: False,
            **self._get_recurrence_params(),
        }, future=True)

    def _break_recurrence(self, future=True):
        """Breaks the event's recurrence.
        Stop the recurrence at the current event if `future` is True, leaving past events in the recurrence.
        If `future` is False, all events in the recurrence are detached and the recurrence itself is unlinked.
        :return: detached events excluding the current events
        """
        recurrences_to_unlink = self.env['recurrence.recurrence']
        detached_events = self.env['calendar.event']
        for event in self:
            recurrence = event.recurrence_id
            if future:
                detached_events |= recurrence._stop_at(event)
            else:
                events = event.recurrence_id._get_recurrent_records(model='calendar.event')
                detached_events |= events
                events.recurrence_id = False
                recurrences_to_unlink |= recurrence
        recurrences_to_unlink.with_context(archive_on_error=True).unlink()
        return detached_events - self

    def _get_start_date(self):
        """Return the event starting date in the event's timezone.
        If no starting time is assigned (yet), return today as default
        :return: date
        """
        if not self.start_datetime:
            return fields.Date.today()
        if self.recurrence_id.record_tz:
            tz = pytz.timezone(self.recurrence_id.record_tz)
            return pytz.utc.localize(self.start_datetime).astimezone(tz).date()
        return self.start_datetime.date()

    def get_display_time_tz(self, tz=False):
        """ get the display_time of the meeting, forcing the timezone. This method is called from email template, to not use sudo(). """
        self.ensure_one()
        if tz:
            self = self.with_context(tz=tz)
        return self._get_display_time(self.start_datetime, self.stop_datetime, self.duration, self.allday)

    def _get_recurrent_record_name(self):
        """ By default, a model inheriting this mixin will create other records of the same type"""
        return self._name

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        recurrence_fields = self._get_recurrent_fields()
        recurring_vals = [vals for vals in vals_list if vals.get('recurrency')]
        other_vals = [vals for vals in vals_list if not vals.get('recurrency')]
        events = super().create(other_vals)
        for vals in recurring_vals:
            vals['follow_recurrence'] = True
        recurring_events = super().create(recurring_vals)
        events += recurring_events
        for event, vals in zip(recurring_events, recurring_vals):
            recurrence_values = {field: vals.pop(field) for field in recurrence_fields if field in vals}
            if vals.get('recurrency'):
                detached_events = event._apply_recurrence_values(recurrence_values)
                detached_events.active = False
        return events

    def write(self, values):
        res = True
        model_name = self._get_recurrent_record_name()
        detached_events = self.env[model_name]
        recurrence_update_setting = values.pop('recurrence_update', None)
        update_recurrence = recurrence_update_setting in ('all_records', 'future_records') and len(self) == 1
        break_recurrence = values.get('recurrency') is False
        time_fields = self.env[self._name]._get_time_fields()

        if (not recurrence_update_setting or recurrence_update_setting == 'self_only' and len(self) == 1) and 'follow_recurrence' not in values:
            if any({field: values.get(field) for field in self.env[model_name]._get_time_fields() if field in values}):
                values['follow_recurrence'] = False

        recurrence_values = {field: values.pop(field) for field in self._get_recurrent_fields() if field in values}
        if update_recurrence:
            if break_recurrence:
                # Update this event
                detached_events |= self._break_recurrence(future=recurrence_update_setting == 'future_records')
            else:
                future_update_start = self.start_datetime if recurrence_update_setting == 'future_records' else None
                time_values = {field: values.pop(field) for field in time_fields if field in values}
                if recurrence_update_setting == 'all_records':
                    # Update all events: we create a new reccurrence and dismiss the existing events
                    self._rewrite_recurrence(values, time_values, recurrence_values)
                else:
                    # Update future events
                    detached_events |= self._split_recurrence(time_values)
                    self.recurrence_id._write_records(values, dtstart=future_update_start)
        else:
            res = super().write(values)
        # We reapply recurrence for future events and when we add a rrule and 'recurrency' == True on the event
        if recurrence_update_setting not in ['self_only', 'all_records'] and not break_recurrence:
            detached_events |= self._apply_recurrence_values(recurrence_values,
                                                             future=recurrence_update_setting == 'future_records')

        (detached_events - self).with_context(archive_on_error=True).unlink()
        return res

    def unlink(self):
        """When a record is deleted and if it was the base_id of a recurrence, we should update the recurrence """
        current_ids = self.ids
        super().unlink()
        recurrences = self.env['recurrence.recurrence'].search([('base_id', 'in', current_ids)])
        for recurrence in recurrences:
            first_record = recurrence._get_first_record(include_outliers=False, model=recurrence.model)
            if first_record:
                recurrence.base_id = first_record.id

    def _rewrite_recurrence(self, values, time_values, recurrence_values):
        """ Recreate the whole recurrence when all recurrent events must be moved
        time_values corresponds to date times for one specific event. We need to update the base_event of the recurrence
        and reapply the recurrence later. All exceptions are lost.
        """
        self.ensure_one()
        model = self._get_recurrent_record_name()
        base_event = self.env[model].browse(self.recurrence_id.base_id)
        if not base_event:
            raise UserError(_("You can't update a recurrence without base event."))
        [base_time_values] = base_event.read(['start_datetime', 'stop_datetime', 'allday'])
        update_dict = {}
        start_update = fields.Datetime.to_datetime(time_values.get('start_datetime'))
        stop_update = fields.Datetime.to_datetime(time_values.get('stop_datetime'))
        # Convert the base_event_id hours according to new values: time shift
        if start_update or stop_update:
            if start_update:
                update_dict = self._rewrite_start_time_fields(update_dict, base_time_values, start_update)
            if stop_update:
                update_dict = self._rewrite_stop_time_fields(update_dict, base_time_values, start_update, stop_update)
        time_values.update(update_dict)
        if time_values or recurrence_values:
            rec_fields = list(self._get_recurrent_fields())
            [rec_vals] = base_event.read(rec_fields)
            old_recurrence_values = {field: rec_vals.pop(field) for field in rec_fields if
                                     field in rec_vals}
            base_event.write({**values, **time_values})
            # Delete all events except the base event and the currently modified
            model = self._get_recurrent_record_name()
            records = self.recurrence_id._get_recurrent_records(model=model)
            expandable_events = records - (base_event + self)
            self.recurrence_id.with_context(archive_on_error=True).unlink()
            expandable_events.with_context(archive_on_error=True).unlink()
            # Make sure to recreate a new recurrence. Needed to prevent sync issues
            base_event.recurrence_id = False
            # Recreate all events and the recurrence: override updated values
            new_values = {
                **old_recurrence_values,
                **base_event._get_recurrence_params(),
                **recurrence_values,
            }
            new_values = {k: v for k, v in new_values.items() if k not in ['rrule', 'next_recurrence_interval']}
            detached_events = base_event._apply_recurrence_values(new_values)
            detached_events.write({'active': False})
            # archive the current event if all the events were recreated
            if self.id != base_event.recurrence_id.base_id and time_values:
                self.active = False
        else:
            # Write on all events. Carefully, it could trigger a lot of noise to synced models
            self.recurrence_id._write_records(values)

    @api.model
    def _rewrite_start_time_fields(self, update_dict, base_time_values, start_update):
        """ Update the start_datetime and stop_datetime when rewriting the whole recurrence.
            This method can be override in module with more time fields. e.g. start_date and stop_date
        """
        start = base_time_values['start_datetime'] + (start_update - self.start_datetime)
        stop = base_time_values['stop_datetime'] + (start_update - self.start_datetime)
        update_dict.update({'start_datetime': start, 'stop_datetime': stop})
        return update_dict

    @api.model
    def _rewrite_stop_time_fields(self, update_dict, base_time_values, start_update, stop_update,):
        if not start_update:
            # Apply the same shift for start
            start = base_time_values['start'] + (stop_update - self.stop_datetime)
            update_dict.update({'start': start})
        stop = base_time_values['stop_datetime'] + (stop_update - self.stop_datetime)
        update_dict.update({'stop_datetime': stop})
        return update_dict

    @api.model
    def _keep_initiator(self):
        """ When a recurrent record is created, the base event can be dismissed if it does not follow the rrule.
        For example, if a friday weekly recurrency is created and the base record has a start_datetime = wednesday,
        it will be automatically archived. In some model that's not the intended behavior (e.g. project).
        This method should be override according to the model need.
        """
        return False

    def _get_recurring_values(self):
        """ This method aims to provide the base value of each record duplicated in a recurrence.
        By default, these are the value of the base record but other model may want to customized them further
        :param: create: in some override, this method may need to create extra records.

        """
        self.ensure_one()
        [values] = self.copy_data()
        return values
