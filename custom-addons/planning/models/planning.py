# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import logging
import pytz
import uuid
from math import modf
from random import randint, shuffle
import itertools

from odoo import api, fields, models, _
from odoo.addons.resource.models.utils import Intervals, sum_intervals, string_to_datetime
from odoo.addons.resource.models.resource_mixin import timezone_datetime
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_utils, format_datetime

_logger = logging.getLogger(__name__)


def days_span(start_datetime, end_datetime):
    if not isinstance(start_datetime, datetime):
        raise ValueError
    if not isinstance(end_datetime, datetime):
        raise ValueError
    end = datetime.combine(end_datetime, datetime.min.time())
    start = datetime.combine(start_datetime, datetime.min.time())
    duration = end - start
    return duration.days + 1


class Planning(models.Model):
    _name = 'planning.slot'
    _description = 'Planning Shift'
    _order = 'start_datetime desc, id desc'
    _rec_name = 'name'
    _check_company_auto = True

    def _default_start_datetime(self):
        return datetime.combine(fields.Date.context_today(self), time.min)

    def _default_end_datetime(self):
        return datetime.combine(fields.Date.context_today(self), time.max)

    name = fields.Text('Note')
    resource_id = fields.Many2one('resource.resource', 'Resource', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", group_expand='_group_expand_resource_id')
    resource_type = fields.Selection(related='resource_id.resource_type')
    resource_color = fields.Integer(related='resource_id.color', string="Resource color")
    employee_id = fields.Many2one('hr.employee', 'Employee', compute='_compute_employee_id', store=True)
    work_email = fields.Char("Work Email", related='employee_id.work_email')
    work_address_id = fields.Many2one(related='employee_id.address_id', store=True)
    work_location_id = fields.Many2one(related='employee_id.work_location_id')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    user_id = fields.Many2one('res.users', string="User", related='resource_id.user_id', store=True, readonly=True)
    manager_id = fields.Many2one(related='employee_id.parent_id', store=True)
    job_title = fields.Char(related='employee_id.job_title')
    company_id = fields.Many2one('res.company', string="Company", required=True, compute="_compute_planning_slot_company_id", store=True, readonly=False)
    role_id = fields.Many2one('planning.role', string="Role", compute="_compute_role_id", store=True, readonly=False, copy=True, group_expand='_read_group_role_id',
        help="Define the roles your resources perform (e.g. Chef, Bartender, Waiter...). Create open shifts for the roles you need to complete a mission. Then, assign those open shifts to the resources that are available.")
    color = fields.Integer("Color", compute='_compute_color')
    was_copied = fields.Boolean("This Shift Was Copied From Previous Week", default=False, readonly=True)
    access_token = fields.Char("Security Token", default=lambda self: str(uuid.uuid4()), required=True, copy=False, readonly=True)

    start_datetime = fields.Datetime(
        "Start Date", compute='_compute_datetime', store=True, readonly=False, required=True,
        copy=True)
    end_datetime = fields.Datetime(
        "End Date", compute='_compute_datetime', store=True, readonly=False, required=True,
        copy=True)
    # UI fields and warnings
    allow_self_unassign = fields.Boolean('Let Employee Unassign Themselves', related='company_id.planning_allow_self_unassign')
    self_unassign_days_before = fields.Integer(
        "Days before shift for unassignment",
        related="company_id.planning_self_unassign_days_before"
    )
    unassign_deadline = fields.Datetime('Deadline for unassignment', compute="_compute_unassign_deadline")
    is_unassign_deadline_passed = fields.Boolean('Is unassignement deadline not past', compute="_compute_is_unassign_deadline_passed")
    is_assigned_to_me = fields.Boolean('Is This Shift Assigned To The Current User', compute='_compute_is_assigned_to_me')
    conflicting_slot_ids = fields.Many2many('planning.slot', compute='_compute_overlap_slot_count')
    overlap_slot_count = fields.Integer('Overlapping Slots', compute='_compute_overlap_slot_count', search='_search_overlap_slot_count')
    is_past = fields.Boolean('Is This Shift In The Past?', compute='_compute_past_shift')
    is_users_role = fields.Boolean('Is the shifts role one of the current user roles', compute='_compute_is_users_role', search='_search_is_users_role')
    request_to_switch = fields.Boolean('Has there been a request to switch on this shift slot?', default=False, readonly=True)

    # time allocation
    allocation_type = fields.Selection([
        ('planning', 'Planning'),
        ('forecast', 'Forecast')
    ], compute='_compute_allocation_type')
    allocated_hours = fields.Float("Allocated Time", compute='_compute_allocated_hours', store=True, readonly=False)
    allocated_percentage = fields.Float("Allocated Time %", default=100,
        compute='_compute_allocated_percentage', store=True, readonly=False,
        group_operator="avg")
    working_days_count = fields.Float("Working Days", compute='_compute_working_days_count', store=True)
    duration = fields.Float("Duration", compute="_compute_slot_duration")

    # publication and sending
    publication_warning = fields.Boolean(
        "Modified Since Last Publication", default=False, compute='_compute_publication_warning',
        store=True, readonly=True, copy=False,
        help="If checked, it means that the shift contains has changed since its last publish.")
    state = fields.Selection([
            ('draft', 'Draft'),
            ('published', 'Published'),
    ], string='Status', default='draft')
    # template dummy fields (only for UI purpose)
    template_creation = fields.Boolean("Save as Template", store=False, inverse='_inverse_template_creation')
    template_autocomplete_ids = fields.Many2many('planning.slot.template', store=False, compute='_compute_template_autocomplete_ids')
    template_id = fields.Many2one('planning.slot.template', string='Shift Templates', compute='_compute_template_id', readonly=False, store=True)
    template_reset = fields.Boolean()
    previous_template_id = fields.Many2one('planning.slot.template')
    allow_template_creation = fields.Boolean(string='Allow Template Creation', compute='_compute_allow_template_creation')

    # Recurring (`repeat_` fields are none stored, only used for UI purpose)
    recurrency_id = fields.Many2one('planning.recurrency', readonly=True, index=True, ondelete="set null", copy=False)
    repeat = fields.Boolean("Repeat", compute='_compute_repeat', inverse='_inverse_repeat',
        help="To avoid polluting your database and performance issues, shifts are only created for the next 6 months. They are then gradually created as time passes by in order to always get shifts 6 months ahead. This value can be modified from the settings of Planning, in debug mode.")
    repeat_interval = fields.Integer("Repeat every", default=1, compute='_compute_repeat_interval', inverse='_inverse_repeat')
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', compute='_compute_repeat_unit', inverse='_inverse_repeat', required=True)
    repeat_type = fields.Selection([('forever', 'Forever'), ('until', 'Until'), ('x_times', 'Number of Occurrences')],
        string='Repeat Type', default='forever', compute='_compute_repeat_type', inverse='_inverse_repeat')
    repeat_until = fields.Date("Repeat Until", compute='_compute_repeat_until', inverse='_inverse_repeat')
    repeat_number = fields.Integer("Repetitions", default=1, compute='_compute_repeat_number', inverse='_inverse_repeat')
    recurrence_update = fields.Selection([
        ('this', 'This shift'),
        ('subsequent', 'This and following shifts'),
        ('all', 'All shifts'),
    ], default='this', store=False)
    confirm_delete = fields.Boolean('Confirm Slots Deletion', compute='_compute_confirm_delete')

    is_hatched = fields.Boolean(compute='_compute_is_hatched')

    slot_properties = fields.Properties('Properties', definition='role_id.slot_properties_definition', precompute=False)

    _sql_constraints = [
        ('check_start_date_lower_end_date', 'CHECK(end_datetime > start_datetime)', 'The end date of a shift should be after its start date.'),
        ('check_allocated_hours_positive', 'CHECK(allocated_hours >= 0)', 'Allocated hours and allocated time percentage cannot be negative.'),
    ]

    @api.depends('role_id.color', 'resource_id.color')
    def _compute_color(self):
        for slot in self:
            slot.color = slot.role_id.color or slot.resource_id.color

    @api.depends('repeat_until', 'repeat_number')
    def _compute_confirm_delete(self):
        for slot in self:
            if slot.recurrency_id and slot.repeat_until and slot.repeat_number:
                recurrence_end_dt = slot.repeat_until or slot.recurrency_id._get_recurrence_last_datetime()
                slot.confirm_delete = fields.Date.to_date(recurrence_end_dt) > slot.repeat_until
            else:
                slot.confirm_delete = False

    @api.constrains('repeat_until')
    def _check_repeat_until(self):
        if any([slot.repeat_until and slot.repeat_until < slot.start_datetime.date() for slot in self]):
            raise UserError(_("The recurrence's end date should fall after the shift's start date."))

    @api.onchange('repeat_until')
    def _onchange_repeat_until(self):
        self._check_repeat_until()

    @api.depends('resource_id.company_id')
    def _compute_planning_slot_company_id(self):
        for slot in self:
            slot.company_id = slot.resource_id.company_id or slot.company_id or slot.env.company

    @api.depends('start_datetime')
    def _compute_past_shift(self):
        now = fields.Datetime.now()
        for slot in self:
            if slot.end_datetime:
                if slot.end_datetime < now:
                    slot.is_past = True
                    # We have to do this (below), for the field to be set automatically to False when the shift is in the past
                    if slot.request_to_switch:
                        slot.sudo().request_to_switch = False
                else:
                    slot.is_past = False
            else:
                slot.is_past = False

    @api.depends('resource_id.employee_id', 'resource_type')
    def _compute_employee_id(self):
        for slot in self:
            slot.employee_id = slot.resource_id.with_context(active_test=False).employee_id if slot.resource_type == 'user' else False

    @api.depends('employee_id', 'template_id')
    def _compute_role_id(self):
        for slot in self:
            if not slot.role_id:
                slot.role_id = slot.resource_id.default_role_id

            if slot.template_id:
                slot.previous_template_id = slot.template_id
                if slot.template_id.role_id:
                    slot.role_id = slot.template_id.role_id
            elif slot.previous_template_id and not slot.template_id and slot.previous_template_id.role_id == slot.role_id:
                slot.role_id = False

    @api.depends('state')
    def _compute_is_hatched(self):
        for slot in self:
            slot.is_hatched = slot.state == 'draft'

    @api.depends('user_id')
    def _compute_is_assigned_to_me(self):
        for slot in self:
            slot.is_assigned_to_me = slot.user_id == self.env.user

    @api.depends('role_id')
    def _compute_is_users_role(self):
        user_resource_roles = self.env['resource.resource'].search([('user_id', '=', self.env.user.id)]).role_ids
        for slot in self:
            slot.is_users_role = (slot.role_id in user_resource_roles) or not user_resource_roles or not slot.role_id

    def _search_is_users_role(self, operator, value):
        if operator not in ('=', '!=') or not isinstance(value, bool):
            raise NotImplementedError(_("Search operation not supported"))
        user_resource_roles = self.env['resource.resource'].search([('user_id', '=', self.env.user.id)]).role_ids
        if not user_resource_roles:
            return [(1, '=', 1)]
        if (operator, value) in [('!=', True), ('=', False)]:
            return [('role_id', 'not in', user_resource_roles.ids)]
        return ['|', ('role_id', 'in', user_resource_roles.ids), ('role_id', '=', False)]

    @api.depends('start_datetime', 'end_datetime')
    def _compute_allocation_type(self):
        for slot in self:
            if slot.start_datetime and slot.end_datetime and slot._get_slot_duration() < 24:
                slot.allocation_type = 'planning'
            else:
                slot.allocation_type = 'forecast'

    @api.depends('start_datetime', 'end_datetime', 'employee_id.resource_calendar_id', 'allocated_hours')
    def _compute_allocated_percentage(self):
        # [TW:Cyclic dependency] allocated_hours,allocated_percentage
        # As allocated_hours and allocated percentage have some common dependencies, and are dependant one from another, we have to make sure
        # they are computed in the right order to get rid of undeterministic computation.
        #
        # Allocated percentage must only be recomputed if allocated_hours has been modified by the user and not in any other cases.
        # If allocated hours have to be recomputed, the allocated percentage have to keep its current value.
        # Hence, we stop the computation of allocated percentage if allocated hours have to be recomputed.
        allocated_hours_field = self._fields['allocated_hours']
        slots = self.filtered(lambda slot: not self.env.is_to_compute(allocated_hours_field, slot) and slot.start_datetime and slot.end_datetime and slot.start_datetime != slot.end_datetime)
        if not slots:
            return
        # if there are at least one slot having start or end date, call the _get_valid_work_intervals
        start_utc = pytz.utc.localize(min(slots.mapped('start_datetime')))
        end_utc = pytz.utc.localize(max(slots.mapped('end_datetime')))
        resource_work_intervals, calendar_work_intervals = slots.resource_id \
            .filtered('calendar_id') \
            ._get_valid_work_intervals(start_utc, end_utc, calendars=slots.company_id.resource_calendar_id)
        for slot in slots:
            if not slot.resource_id and slot.allocation_type == 'planning' or not slot.resource_id.calendar_id:
                slot.allocated_percentage = 100 * slot.allocated_hours / slot._calculate_slot_duration()
            else:
                work_hours = slot._get_working_hours_over_period(start_utc, end_utc, resource_work_intervals, calendar_work_intervals)
                slot.allocated_percentage = 100 * slot.allocated_hours / work_hours if work_hours else 100

    @api.depends(
        'start_datetime', 'end_datetime', 'resource_id.calendar_id',
        'company_id.resource_calendar_id', 'allocated_percentage')
    def _compute_allocated_hours(self):
        percentage_field = self._fields['allocated_percentage']
        self.env.remove_to_compute(percentage_field, self)
        planning_slots = self.filtered(
            lambda s:
                (s.allocation_type == 'planning' or not s.company_id)
                and not s.resource_id
                or not s.resource_id.calendar_id
        )
        slots_with_calendar = self - planning_slots
        for slot in planning_slots:
            # for each planning slot, compute the duration
            ratio = slot.allocated_percentage / 100.0
            slot.allocated_hours = slot._calculate_slot_duration() * ratio
        if slots_with_calendar:
            # for forecasted slots, compute the conjunction of the slot resource's work intervals and the slot.
            unplanned_slots_with_calendar = slots_with_calendar.filtered_domain([
                '|', ('start_datetime', "=", False), ('end_datetime', "=", False),
            ])
            # Unplanned slots will have allocated hours set to 0.0 as there are no enough information
            # to compute the allocated hours (start or end datetime are mandatory for this computation)
            for slot in unplanned_slots_with_calendar:
                slot.allocated_hours = 0.0
            planned_slots_with_calendar = slots_with_calendar - unplanned_slots_with_calendar
            if not planned_slots_with_calendar:
                return
            # if there are at least one slot having start or end date, call the _get_valid_work_intervals
            start_utc = pytz.utc.localize(min(planned_slots_with_calendar.mapped('start_datetime')))
            end_utc = pytz.utc.localize(max(planned_slots_with_calendar.mapped('end_datetime')))
            # work intervals per resource are retrieved with a batch
            resource_work_intervals, calendar_work_intervals = slots_with_calendar.resource_id._get_valid_work_intervals(
                start_utc, end_utc, calendars=slots_with_calendar.company_id.resource_calendar_id
            )
            for slot in planned_slots_with_calendar:
                slot.allocated_hours = slot._get_duration_over_period(
                    pytz.utc.localize(slot.start_datetime), pytz.utc.localize(slot.end_datetime),
                    resource_work_intervals, calendar_work_intervals, has_allocated_hours=False
                )

    @api.depends('start_datetime', 'end_datetime', 'resource_id')
    def _compute_working_days_count(self):
        slots_per_calendar = defaultdict(set)
        planned_dates_per_calendar_id = defaultdict(lambda: (datetime.max, datetime.min))
        for slot in self:
            if not slot.employee_id:
                slot.working_days_count = 0
                continue
            calendar = slot.resource_id.calendar_id or slot.resource_id.company_id.resource_calendar_id
            slots_per_calendar[calendar].add(slot.id)
            datetime_begin, datetime_end = planned_dates_per_calendar_id[calendar.id]
            datetime_begin = min(datetime_begin, slot.start_datetime)
            datetime_end = max(datetime_end, slot.end_datetime)
            planned_dates_per_calendar_id[calendar.id] = datetime_begin, datetime_end
        for calendar, slot_ids in slots_per_calendar.items():
            slots = self.env['planning.slot'].browse(list(slot_ids))
            if not calendar:
                slots.working_days_count = 0
                continue
            datetime_begin, datetime_end = planned_dates_per_calendar_id[calendar.id]
            datetime_begin = timezone_datetime(datetime_begin)
            datetime_end = timezone_datetime(datetime_end)
            resources = slots.resource_id
            day_total = calendar._get_resources_day_total(datetime_begin, datetime_end, resources)
            intervals = calendar._work_intervals_batch(datetime_begin, datetime_end, resources)
            for slot in slots:
                slot.working_days_count = calendar._get_days_data(
                    intervals[slot.resource_id.id] & Intervals([(
                        timezone_datetime(slot.start_datetime),
                        timezone_datetime(slot.end_datetime),
                        self.env['resource.calendar.attendance']
                    )]),
                    day_total[slot.resource_id.id]
                )['days']

    @api.depends('start_datetime', 'end_datetime', 'resource_id')
    def _compute_overlap_slot_count(self):
        if self.ids:
            self.flush_model(['start_datetime', 'end_datetime', 'resource_id'])
            query = """
                SELECT S1.id,ARRAY_AGG(DISTINCT S2.id) as conflict_ids FROM
                    planning_slot S1, planning_slot S2
                WHERE
                    S1.start_datetime < S2.end_datetime
                    AND S1.end_datetime > S2.start_datetime
                    AND S1.id <> S2.id AND S1.resource_id = S2.resource_id
                    AND S1.allocated_percentage + S2.allocated_percentage > 100
                    and S1.id in %s
                GROUP BY S1.id;
            """
            self.env.cr.execute(query, (tuple(self.ids),))
            overlap_mapping = dict(self.env.cr.fetchall())
            for slot in self:
                slot_result = overlap_mapping.get(slot.id, [])
                slot.overlap_slot_count = len(slot_result)
                slot.conflicting_slot_ids = [(6, 0, slot_result)]
        else:
            # Allow fetching overlap without id if there is only one record
            # This is to allow displaying the warning when creating a new record without having an ID yet
            if len(self) == 1 and self.employee_id and self.start_datetime and self.end_datetime:
                query = """
                    SELECT ARRAY_AGG(s.id) as conflict_ids
                      FROM planning_slot s
                     WHERE s.employee_id = %s
                       AND s.start_datetime < %s
                       AND s.end_datetime > %s
                       AND s.allocated_percentage + %s > 100
                """
                self.env.cr.execute(query, (self.employee_id.id, self.end_datetime,
                                            self.start_datetime, self.allocated_percentage))
                overlaps = self.env.cr.dictfetchall()
                if overlaps[0]['conflict_ids']:
                    self.overlap_slot_count = len(overlaps[0]['conflict_ids'])
                    self.conflicting_slot_ids = [(6, 0, overlaps[0]['conflict_ids'])]
                else:
                    self.overlap_slot_count = False
            else:
                self.overlap_slot_count = False

    @api.model
    def _search_overlap_slot_count(self, operator, value):
        if operator not in ['=', '>'] or not isinstance(value, int) or value != 0:
            raise NotImplementedError(_('Operation not supported, you should always compare overlap_slot_count to 0 value with = or > operator.'))

        query = """
            SELECT S1.id
            FROM planning_slot S1
            WHERE EXISTS (
                SELECT 1
                  FROM planning_slot S2
                 WHERE S1.id <> S2.id
                   AND S1.resource_id = S2.resource_id
                   AND S1.start_datetime < S2.end_datetime
                   AND S1.end_datetime > S2.start_datetime
                   AND S1.allocated_percentage + S2.allocated_percentage > 100
            )
        """
        operator_new = (operator == ">") and "inselect" or "not inselect"
        return [('id', operator_new, (query, ()))]

    @api.depends('start_datetime', 'end_datetime')
    def _compute_slot_duration(self):
        for slot in self:
            slot.duration = slot._get_slot_duration()

    def _get_slot_duration(self):
        """Return the slot (effective) duration expressed in hours.
        """
        self.ensure_one()
        if not self.start_datetime or not self.end_datetime:
            return False
        return (self.end_datetime - self.start_datetime).total_seconds() / 3600.0

    def _get_domain_template_slots(self):
        domain = []
        if self.resource_type == 'material':
            domain += [('role_id', '=', False)]
        elif self.role_id:
            domain += ['|', ('role_id', '=', self.role_id.id), ('role_id', '=', False)]
        elif self.employee_id and self.employee_id.sudo().planning_role_ids:
            domain += ['|', ('role_id', 'in', self.employee_id.sudo().planning_role_ids.ids), ('role_id', '=', False)]
        return domain

    @api.depends('role_id', 'employee_id')
    def _compute_template_autocomplete_ids(self):
        domain = self._get_domain_template_slots()
        templates = self.env['planning.slot.template'].search(domain, order='start_time', limit=10)
        self.template_autocomplete_ids = templates + self.template_id

    @api.depends('employee_id', 'role_id', 'start_datetime', 'end_datetime')
    def _compute_template_id(self):
        for slot in self.filtered(lambda s: s.template_id):
            slot.previous_template_id = slot.template_id
            slot.template_reset = False
            if slot._different_than_template():
                slot.template_id = False
                slot.previous_template_id = False
                slot.template_reset = True

    def _different_than_template(self, check_empty=True):
        self.ensure_one()
        if not self.start_datetime:
            return True
        template_fields = self._get_template_fields().items()
        for template_field, slot_field in template_fields:
            if self.template_id[template_field] or not check_empty:
                if template_field == 'start_time':
                    h = int(self.template_id.start_time)
                    m = round(modf(self.template_id.start_time)[0] * 60.0)
                    slot_time = self[slot_field].astimezone(pytz.timezone(self._get_tz()))
                    if slot_time.hour != h or slot_time.minute != m:
                        return True
                else:
                    if self[slot_field] != self.template_id[template_field]:
                        return True
        return False

    @api.depends('template_id', 'role_id', 'allocated_hours', 'start_datetime', 'end_datetime')
    def _compute_allow_template_creation(self):
        for slot in self:
            if not (slot.start_datetime and slot.end_datetime):
                slot.allow_template_creation = False
                continue

            values = self._prepare_template_values()
            domain = [(x, '=', values[x]) for x in values.keys()]
            existing_templates = self.env['planning.slot.template'].search(domain, limit=1)
            slot.allow_template_creation = not existing_templates and slot._different_than_template(check_empty=False)

    @api.depends('recurrency_id')
    def _compute_repeat(self):
        for slot in self:
            if slot.recurrency_id:
                slot.repeat = True
            else:
                slot.repeat = False

    @api.depends('recurrency_id.repeat_interval')
    def _compute_repeat_interval(self):
        recurrency_slots = self.filtered('recurrency_id')
        for slot in recurrency_slots:
            if slot.recurrency_id:
                slot.repeat_interval = slot.recurrency_id.repeat_interval
        (self - recurrency_slots).update(self.default_get(['repeat_interval']))

    @api.depends('recurrency_id.repeat_until', 'repeat', 'repeat_type')
    def _compute_repeat_until(self):
        for slot in self:
            repeat_until = False
            if slot.repeat and slot.repeat_type == 'until':
                if slot.recurrency_id and slot.recurrency_id.repeat_until:
                    repeat_until = slot.recurrency_id.repeat_until
                elif slot.start_datetime:
                    repeat_until = slot.start_datetime + relativedelta(weeks=1)
            slot.repeat_until = repeat_until

    @api.depends('recurrency_id.repeat_number', 'repeat_type')
    def _compute_repeat_number(self):
        recurrency_slots = self.filtered('recurrency_id')
        for slot in recurrency_slots:
            slot.repeat_number = slot.recurrency_id.repeat_number
        (self - recurrency_slots).update(self.default_get(['repeat_number']))

    @api.depends('recurrency_id.repeat_unit')
    def _compute_repeat_unit(self):
        non_recurrent_slots = self.env['planning.slot']
        for slot in self:
            if slot.recurrency_id:
                slot.repeat_unit = slot.recurrency_id.repeat_unit
            else:
                non_recurrent_slots += slot
        non_recurrent_slots.update(self.default_get(['repeat_unit']))

    @api.depends('recurrency_id.repeat_type')
    def _compute_repeat_type(self):
        recurrency_slots = self.filtered('recurrency_id')
        for slot in recurrency_slots:
            if slot.recurrency_id:
                slot.repeat_type = slot.recurrency_id.repeat_type
        (self - recurrency_slots).update(self.default_get(['repeat_type']))

    def _inverse_repeat(self):
        for slot in self:
            if slot.repeat and not slot.recurrency_id.id:  # create the recurrence
                repeat_until = False
                repeat_number = 0
                if slot.repeat_type == "until":
                    repeat_until = datetime.combine(fields.Date.to_date(slot.repeat_until), datetime.max.time())
                    repeat_until = repeat_until.replace(tzinfo=pytz.timezone(slot.company_id.resource_calendar_id.tz or 'UTC')).astimezone(pytz.utc).replace(tzinfo=None)
                if slot.repeat_type == 'x_times':
                    repeat_number = slot.repeat_number
                recurrency_values = {
                    'repeat_interval': slot.repeat_interval,
                    'repeat_unit': slot.repeat_unit,
                    'repeat_until': repeat_until,
                    'repeat_number': repeat_number,
                    'repeat_type': slot.repeat_type,
                    'company_id': slot.company_id.id,
                }
                recurrence = self.env['planning.recurrency'].create(recurrency_values)
                slot.recurrency_id = recurrence
                slot.recurrency_id._repeat_slot()
            # user wants to delete the recurrence
            # here we also check that we don't delete by mistake a slot of which the repeat parameters have been changed
            elif not slot.repeat and slot.recurrency_id.id:
                slot.recurrency_id._delete_slot(slot.end_datetime)
                slot.recurrency_id.unlink()  # will set recurrency_id to NULL

    def _inverse_template_creation(self):
        PlanningTemplate = self.env['planning.slot.template']
        for slot in self.filtered(lambda s: s.template_creation):
            values = slot._prepare_template_values()
            domain = [(x, '=', values[x]) for x in values.keys()]
            existing_templates = PlanningTemplate.search(domain, limit=1)
            if not existing_templates:
                template = PlanningTemplate.create(values)
                slot.write({'template_id': template.id, 'previous_template_id': template.id})
            else:
                slot.write({'template_id': existing_templates.id})

    @api.model
    def _calculate_start_end_dates(self,
                                 start_datetime,
                                 end_datetime,
                                 resource_id,
                                 template_id,
                                 previous_template_id,
                                 template_reset):
        """
        Calculate the start and end dates for a given planning slot based on various parameters.

        Returns: A tuple containing the calculated start and end datetime values in UTC without timezone.
        """
        def convert_datetime_timezone(dt, tz):
            return dt and pytz.utc.localize(dt).astimezone(tz)

        resource = resource_id or self.env.user.employee_id.resource_id
        company = self.company_id or self.env.company
        employee = resource_id.employee_id if resource_id.resource_type == 'user' else False
        user_tz = pytz.timezone(self.env.user.tz
                                or employee and employee.tz
                                or resource_id.tz
                                or self._context.get('tz')
                                or self.env.user.company_id.resource_calendar_id.tz
                                or 'UTC')

        if start_datetime and end_datetime and not template_id:
            # Transform the current column's start/end_datetime to the user's timezone from UTC
            current_start = convert_datetime_timezone(start_datetime, user_tz)
            current_end = convert_datetime_timezone(end_datetime, user_tz)
            # Look at the work intervals to examine whether the current start/end_datetimes are inside working hours
            calendar_id = resource.calendar_id or company.resource_calendar_id
            work_interval = calendar_id._work_intervals_batch(current_start, current_end)[False]
            intervals = [(date_start, date_stop) for date_start, date_stop, attendance in work_interval]
            if not intervals:
                # If we are outside working hours, we do not edit the start/end_datetime
                # Return the start/end times back at UTC and remove the tzinfo from the object
                return (current_start.astimezone(pytz.utc).replace(tzinfo=None),
                        current_end.astimezone(pytz.utc).replace(tzinfo=None))

        # start_datetime and end_datetime are from 00:00 to 23:59 in user timezone
        # Converted in UTC, it gives an offset for any other timezone, _convert_datetime_timezone removes the offset
        start = convert_datetime_timezone(start_datetime, user_tz) if start_datetime else user_tz.localize(self._default_start_datetime())
        end = convert_datetime_timezone(end_datetime, user_tz) if end_datetime else user_tz.localize(self._default_end_datetime())

        # Get start and end in resource timezone so that it begins/ends at the same hour of the day as it would be in the user timezone
        # This is needed because _adjust_to_calendar takes start as datetime for the start of the day and end as end time for the end of the day
        # This can lead to different results depending on the timezone difference between the current user and the resource.
        # Example:
        # The user is in Europe/Brussels timezone (CET, UTC+1)
        # The resource is Asia/Krasnoyarsk timezone (IST, UTC+7)
        # The resource has two shifts during the day:
        #       - Morning shift: 8 to 12
        #       - Afternoon shift: 13 to 17
        # When the user selects a day to plan a shift for the resource, he expects to have the shift scheduled according to the resource's calendar given a search range between 00:00 and 23:59
        # The datetime received from the frontend is in the user's timezone meaning that the search interval will be between 23:00 and 22:59 in UTC
        # If the datetime is not adjusted to the resource's calendar beforehand, _adjust_to_calendar and _get_closest_work_time will shift the time to the resource's timezone.
        # The datetime given to _get_closest_work_time will be 6 AM once shifted in the resource's timezone. This will properly find the start of the morning shift at 8AM
        # For the afternoon shift, _get_closest_work_time will search the end of the shift that is close to 6AM the day after.
        # The closest shift found based on the end datetime will be the morning shift meaning that the work_interval_end will be the end of the morning shift the following day.
        if resource:
            work_interval_start, work_interval_end = resource._adjust_to_calendar(start.replace(tzinfo=pytz.timezone(resource.tz)), end.replace(tzinfo=pytz.timezone(resource.tz)), compute_leaves=False)[resource]
            start, end = (work_interval_start or start, work_interval_end or end)

        if not previous_template_id and not template_reset:
            start = start.astimezone(pytz.utc).replace(tzinfo=None)
            end = end.astimezone(pytz.utc).replace(tzinfo=None)

        if template_id and start_datetime:
            h = int(template_id.start_time)
            m = round(modf(template_id.start_time)[0] * 60.0)
            start = pytz.utc.localize(start_datetime).astimezone(pytz.timezone(resource.tz) if
                                                                 resource else user_tz)
            start = start.replace(hour=int(h), minute=int(m))
            start = start.astimezone(pytz.utc).replace(tzinfo=None)

            h, m = divmod(template_id.duration, 1)
            delta = timedelta(hours=int(h), minutes=int(round(m * 60)))
            end = start + delta

        # Need to remove the tzinfo in start and end as without these it leads to a traceback
        # when the start time is empty
        start = start.astimezone(pytz.utc).replace(tzinfo=None) if start.tzinfo else start
        end = end.astimezone(pytz.utc).replace(tzinfo=None) if end.tzinfo else end
        return (start, end)

    @api.depends('template_id')
    def _compute_datetime(self):
        for slot in self.filtered(lambda s: s.template_id):
            slot.start_datetime, slot.end_datetime = self._calculate_start_end_dates(slot.start_datetime,
                                                                                     slot.end_datetime,
                                                                                     slot.resource_id,
                                                                                     slot.template_id,
                                                                                     slot.previous_template_id,
                                                                                     slot.template_reset)

    @api.depends(lambda self: self._get_fields_breaking_publication())
    def _compute_publication_warning(self):
        for slot in self:
            slot.publication_warning = slot.resource_id and slot.resource_type != 'material' and slot.state == 'published'

    def _company_working_hours(self, start, end):
        company = self.company_id or self.env.company
        work_interval = company.resource_calendar_id._work_intervals_batch(start, end)[False]
        intervals = [(date_start, date_stop) for date_start, date_stop, attendance in work_interval]
        start_datetime, end_datetime = (start, end)
        if intervals and (end_datetime-start_datetime).days == 0: # Then we want the first working day and keep the end hours of this day
            start_datetime = intervals[0][0]
            end_datetime = [stop for start, stop in intervals if stop.date() == start_datetime.date()][-1]
        elif intervals and (end_datetime-start_datetime).days >= 0:
            start_datetime = intervals[0][0]
            end_datetime = intervals[-1][1]

        return (start_datetime, end_datetime)

    @api.depends('self_unassign_days_before', 'start_datetime')
    def _compute_unassign_deadline(self):
        slots_with_date = self.filtered('start_datetime')
        (self - slots_with_date).unassign_deadline = False
        for slot in slots_with_date:
            slot.unassign_deadline = fields.Datetime.subtract(slot.start_datetime, days=slot.self_unassign_days_before)

    @api.depends('unassign_deadline')
    def _compute_is_unassign_deadline_passed(self):
        slots_with_date = self.filtered('unassign_deadline')
        (self - slots_with_date).is_unassign_deadline_passed = False
        for slot in slots_with_date:
            slot.is_unassign_deadline_passed = slot.unassign_deadline < fields.Datetime.now()

    # Used in report
    def _group_slots_by_resource(self):
        grouped_slots = defaultdict(self.browse)
        for slot in self.sorted(key=lambda s: s.resource_id.name or ''):
            grouped_slots[slot.resource_id] |= slot
        return grouped_slots

    # ----------------------------------------------------
    # ORM overrides
    # ----------------------------------------------------

    @api.model
    def _read_group_fields_nullify(self):
        return ['working_days_count']

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if lazy:
            return res

        null_fields = [f for f in self._read_group_fields_nullify() if any(f2.startswith(f) for f2 in fields)]
        if null_fields:
            for r in res:
                for f in null_fields:
                    if r[f] == 0:
                        r[f] = False
        return res

    @api.model
    def default_get(self, fields_list):
        res = super(Planning, self).default_get(fields_list)

        if res.get('resource_id'):
            resource_id = self.env['resource.resource'].browse(res.get('resource_id'))
            template_id, previous_template_id = [res.get(key) for key in ['template_id', 'previous_template_id']]
            template_id = template_id and self.env['planning.slot.template'].browse(template_id)
            previous_template_id = template_id and self.env['planning.slot.template'].browse(previous_template_id)
            res['start_datetime'], res['end_datetime'] = self._calculate_start_end_dates(res.get('start_datetime'),
                                                                                       res.get('end_datetime'),
                                                                                       resource_id,
                                                                                       template_id,
                                                                                       previous_template_id,
                                                                                       res.get('template_reset'))
        else:
            if 'start_datetime' in fields_list and not self._context.get('planning_keep_default_datetime', False):
                start_datetime = fields.Datetime.from_string(res.get('start_datetime')) if res.get('start_datetime') else self._default_start_datetime()
                end_datetime = fields.Datetime.from_string(res.get('end_datetime')) if res.get('end_datetime') else self._default_end_datetime()
                start = pytz.utc.localize(start_datetime)
                end = pytz.utc.localize(end_datetime) if end_datetime else self._default_end_datetime()
                opening_hours = self._company_working_hours(start, end)
                res['start_datetime'] = opening_hours[0].astimezone(pytz.utc).replace(tzinfo=None)

                if 'end_datetime' in fields_list:
                    res['end_datetime'] = opening_hours[1].astimezone(pytz.utc).replace(tzinfo=None)

        return res

    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows.
            Overridden here because we need to generate different access tokens
            and by default _init_column calls the default method once and applies
            it for every record.
        """
        if column_name != 'access_token':
            super(Planning, self)._init_column(column_name)
        else:
            query = """
                UPDATE %(table_name)s
                SET access_token = md5(md5(random()::varchar || id::varchar) || clock_timestamp()::varchar)::uuid::varchar
                WHERE access_token IS NULL
            """ % {'table_name': self._table}
            self.env.cr.execute(query)

    @api.depends(lambda self: self._display_name_fields())
    @api.depends_context('group_by')
    def _compute_display_name(self):
        group_by = self.env.context.get('group_by', [])
        field_list = [fname for fname in self._display_name_fields() if fname not in group_by]

        # Sudo as a planning manager is not able to read private project if he is not project manager.
        self = self.sudo()
        for slot in self.with_context(hide_partner_ref=True):
            # label part, depending on context `groupby`
            name_values = [
                self._fields[fname].convert_to_display_name(slot[fname], slot) if fname != 'resource_id' else slot.resource_id.name
                for fname in field_list
                if slot[fname]
            ][:4]  # limit to 4 labels
            name = ' - '.join(name_values) or slot.resource_id.name

            # add unicode bubble to tell there is a note
            if slot.name:
                name = f'{name} \U0001F4AC'

            slot.display_name = name or ''

    @api.model_create_multi
    def create(self, vals_list):
        Resource = self.env['resource.resource']
        for vals in vals_list:
            if vals.get('resource_id'):
                resource = Resource.browse(vals.get('resource_id'))
                if not vals.get('company_id'):
                    vals['company_id'] = resource.company_id.id
                if resource.resource_type == 'material':
                    vals['state'] = 'published'
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    def write(self, values):
        new_resource = self.env['resource.resource'].browse(values['resource_id']) if 'resource_id' in values else None
        if new_resource and new_resource.resource_type == 'material':
            values['state'] = 'published'
        # if the resource_id is changed while the shift has already been published and the resource is human, that means that the shift has been re-assigned
        # and thus we should send the email about the shift re-assignment
        for slot in self.filtered(lambda s: new_resource and s.state == 'published' and s.resource_type == 'user' and new_resource.resource_type == 'user'):
            self._send_shift_assigned(slot, new_resource)
        for slot in self:
            if slot.request_to_switch and (
                (new_resource and slot.resource_id != new_resource)
                or ('start_datetime' in values and slot.start_datetime != datetime.strptime(values['start_datetime'], '%Y-%m-%d %H:%M:%S'))
                or ('end_datetime' in values and slot.end_datetime != datetime.strptime(values['end_datetime'], '%Y-%m-%d %H:%M:%S'))
            ):
                values['request_to_switch'] = False

        recurrence_update = values.pop('recurrence_update', 'this')
        if recurrence_update != 'this':
            recurrence_domain = []
            if recurrence_update == 'subsequent':
                for slot in self:
                    recurrence_domain = expression.OR([recurrence_domain,
                        ['&', ('recurrency_id', '=', slot.recurrency_id.id), ('start_datetime', '>=', slot.start_datetime)]
                    ])
                    recurrence_slots = self.search(recurrence_domain)
                    if any(
                        field_name in values
                        for field_name in ('start_datetime', 'end_datetime')
                    ):
                        recurrence_slots -= slot
                        values["repeat_type"] = slot.repeat_type
                        self -= recurrence_slots
                        recurrence_slots.unlink()
                    else:
                        self |= recurrence_slots
            else:
                recurrence_slots = self.search([('recurrency_id', 'in', self.recurrency_id.ids)])
                if any(
                    field_name in values
                    for field_name in ('start_datetime', 'end_datetime')
                ):
                    slot = recurrence_slots[-1]
                    values["repeat_type"] = slot.repeat_type    # this is to ensure that the subsequent slots are recreated
                    recurrence_slots -= slot
                    recurrence_slots.unlink()
                    self -= recurrence_slots
                    self |= slot
                else:
                    self |= recurrence_slots

        result = super().write(values)
        # recurrence
        if any(key in ('repeat', 'repeat_unit', 'repeat_type', 'repeat_until', 'repeat_interval', 'repeat_number') for key in values):
            # User is trying to change this record's recurrence so we delete future slots belonging to recurrence A
            # and we create recurrence B from now on w/ the new parameters
            for slot in self:
                recurrence = slot.recurrency_id
                if recurrence and values.get('repeat') is None:
                    repeat_type = values.get('repeat_type') or recurrence.repeat_type
                    repeat_until = values.get('repeat_until') or recurrence.repeat_until
                    repeat_number = values.get('repeat_number', 0) or slot.repeat_number
                    if repeat_type == 'until':
                        repeat_until = datetime.combine(fields.Date.to_date(repeat_until), datetime.max.time())
                        repeat_until = repeat_until.replace(tzinfo=pytz.timezone(slot.company_id.resource_calendar_id.tz or 'UTC')).astimezone(pytz.utc).replace(tzinfo=None)
                    recurrency_values = {
                        'repeat_interval': values.get('repeat_interval') or recurrence.repeat_interval,
                        'repeat_unit': values.get('repeat_unit') or recurrence.repeat_unit,
                        'repeat_until': repeat_until if repeat_type == 'until' else False,
                        'repeat_number': repeat_number,
                        'repeat_type': repeat_type,
                        'company_id': slot.company_id.id,
                    }
                    recurrence.write(recurrency_values)
                    if slot.repeat_type == 'x_times':
                        recurrency_values['repeat_until'] = recurrence._get_recurrence_last_datetime()
                    end_datetime = slot.end_datetime if values.get('repeat_unit') else recurrency_values.get('repeat_until')
                    recurrence._delete_slot(end_datetime)
                    recurrence._repeat_slot()
        return result

    @api.returns(None, lambda value: value[0])
    def copy_data(self, default=None):
        if default is None:
            default = {}
        if self._context.get('planning_split_tool'):
            default['state'] = self.state
        return super().copy_data(default=default)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        result = super().copy(default=default)
        # force recompute of stored computed fields depending on start_datetime
        if default and "start_datetime" in default:
            result._compute_allocated_hours()
            result._compute_working_days_count()
        return result

    # ----------------------------------------------------
    # Actions
    # ----------------------------------------------------

    def action_address_recurrency(self, recurrence_update):
        """ :param recurrence_update: the occurences to be targetted (this, subsequent, all)
        """
        if recurrence_update == 'this':
            return
        domain = [('id', 'not in', self.ids)]
        if recurrence_update == 'all':
            domain = expression.AND([domain, [('recurrency_id', 'in', self.recurrency_id.ids)]])
        elif recurrence_update == 'subsequent':
            start_date_per_recurrency_id = {}
            sub_domain = []
            for shift in self:
                if shift.recurrency_id.id not in start_date_per_recurrency_id\
                    or shift.start_datetime < start_date_per_recurrency_id[shift.recurrency_id.id]:
                    start_date_per_recurrency_id[shift.recurrency_id.id] = shift.start_datetime
            for recurrency_id, start_datetime in start_date_per_recurrency_id.items():
                sub_domain = expression.OR([sub_domain,
                    ['&', ('recurrency_id', '=', recurrency_id), ('start_datetime', '>', start_datetime)]
                ])
            domain = expression.AND([domain, sub_domain])
        sibling_slots = self.env['planning.slot'].search(domain)
        self.recurrency_id.unlink()
        sibling_slots.unlink()

    def action_unlink(self):
        self.unlink()
        return {'type': 'ir.actions.act_window_close'}

    def action_see_overlaping_slots(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'planning.slot',
            'name': _('Shifts in Conflict'),
            'view_mode': 'gantt,list,form',
            'context': {
                'initialDate': min(self.mapped('start_datetime')),
                'search_default_conflict_shifts': True,
                'search_default_resource_id': self.resource_id.ids
            }
        }

    def action_self_assign(self):
        """ Allow planning user to self assign open shift. """
        self.ensure_one()
        # user must at least 'read' the shift to self assign (Prevent any user in the system (portal, ...) to assign themselves)
        if not self.check_access_rights('read', raise_exception=False):
            raise AccessError(_("You don't have the right to self assign."))
        if self.resource_id and not self.request_to_switch:
            raise UserError(_("You can not assign yourself to an already assigned shift."))
        return self.sudo().write({'resource_id': self.env.user.employee_id.resource_id.id if self.env.user.employee_id else False})

    def action_self_unassign(self):
        """ Allow planning user to self unassign from a shift, if the feature is activated """
        self.ensure_one()
        # The following condition will check the read access on planning.slot, and that user must at least 'read' the
        # shift to self unassign. Prevent any user in the system (portal, ...) to unassign any shift.
        if not self.allow_self_unassign:
            raise UserError(_("The company does not allow you to self unassign."))
        if self.is_unassign_deadline_passed:
            raise UserError(_("The deadline for unassignment has passed."))
        if self.employee_id != self.env.user.employee_id:
            raise UserError(_("You can not unassign another employee than yourself."))
        return self.sudo().write({'resource_id': False})

    def action_switch_shift(self):
        """ Allow planning user to make shift available for other people to assign themselves to. """
        self.ensure_one()
        # same as with self-assign, a user must be able to 'read' the shift in order to request a switch
        if not self.check_access_rights('read', raise_exception=False):
            raise AccessError(_("You don't have the right to switch shifts."))
        if self.employee_id != self.env.user.employee_id:
            raise UserError(_("You can not request to switch a shift that is assigned to another user."))
        if self.is_past:
            raise UserError(_("You cannot switch a shift that is in the past."))
        return self.sudo().write({'request_to_switch': True})

    def action_cancel_switch(self):
        """ Allows the planning user to cancel the shift switch if they change their mind at a later date """
        self.ensure_one()
        # same as above, the user rights are checked in order for the operation to be completed
        if not self.check_access_rights('read', raise_exception=False):
            raise AccessError(_("You don't have the right to cancel a request to switch."))
        if self.employee_id != self.env.user.employee_id:
            raise UserError(_("You can not cancel a request to switch made by another user."))
        if self.is_past:
            raise UserError(_("You cannot cancel a request to switch that is in the past."))
        return self.sudo().write({'request_to_switch': False})

    def auto_plan_id(self):
        """ Used in the form view to auto plan a single shift.
        """
        if not self.with_context(planning_slot_id=self.id).auto_plan_ids([('id', '=', self.id)]):
            return self._get_notification_action("danger", _("There are no resources available for this open shift."))

    @api.model
    def auto_plan_ids(self, view_domain):
        # We need to make sure we have a specified either one shift in particular or a period to look into.
        assert self._context.get('planning_slot_id') or (
            self._context.get('default_start_datetime') and self._context.get('default_end_datetime')
        ), "`default_start_datetime` and `default_end_datetime` attributes should be in the context"

        # Our goal is to assign empty shifts in this period. So first, let's get them all!
        open_shifts, min_start, max_end = self._read_group(
            expression.AND([
                view_domain,
                [('resource_id', '=', False)],
            ]),
            [],
            ['id:recordset', 'start_datetime:min', 'end_datetime:max'],
        )[0]
        if not open_shifts:
            return []
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        min_start = min_start.astimezone(user_tz)
        max_end = max_end.astimezone(user_tz)

        # Get all resources that have the role set on those shifts as default role or in their roles.
        Resource = self.env['resource.resource']
        # open_shifts.role_id.ids wouldn't include False, yet we need this information
        open_shift_role_ids = [shift.role_id.id for shift in open_shifts]
        resources = Resource.search([
            ('calendar_id', '!=', False),
            '|',
                ('default_role_id', 'in', open_shift_role_ids),
                ('role_ids', 'in', open_shift_role_ids),
        ])
        # And make two dictionnaries out of it (default roles and roles). We will prioritize default roles.
        resource_ids_per_role_id = defaultdict(list)
        resource_ids_per_default_role_id = defaultdict(list)
        for resource in resources:
            resource_ids_per_default_role_id[resource.default_role_id.id].append(resource.id)
            for role in resource.role_ids:
                if role == resource.default_role_id:
                    continue
                resource_ids_per_role_id[role.id].append(resource.id)
        # Get the schedule of each resource in the period.
        schedule_intervals_per_resource_id, dummy = resources._get_valid_work_intervals(min_start, max_end)

        # Now let's get the assigned shifts and count the worked hours per day for each resource
        min_start = min_start.astimezone(pytz.utc).replace(tzinfo=None) + relativedelta(hour=0, minute=0, second=0, microsecond=0)
        max_end = max_end.astimezone(pytz.utc).replace(tzinfo=None) + relativedelta(days=1, hour=0, minute=0, second=0, microsecond=0)
        PlanningShift = self.env['planning.slot']
        same_days_shifts = PlanningShift.search_read([
            ('resource_id', 'in', resources.ids),
            ('end_datetime', '>', min_start),
            ('start_datetime', '<', max_end),
        ], ['start_datetime', 'end_datetime', 'resource_id', 'allocated_hours'], load=False)
        timeline_and_worked_hours_per_resource_id = self._shift_records_to_timeline_per_resource_id(same_days_shifts)

        # Create an "empty timeline" with midnight for each day in the period
        delta_days = (max_end - min_start).days
        empty_timeline = [
            ((min_start + relativedelta(days=i + 1)).astimezone(user_tz).replace(tzinfo=None), 0)
            for i in range(delta_days)
        ]

        def find_resource(shift):
            shift_intervals = Intervals([(
                shift.start_datetime.astimezone(user_tz),
                shift.end_datetime.astimezone(user_tz),
                PlanningShift,
            )])
            for resources_dict in [resource_ids_per_default_role_id, resource_ids_per_role_id]:
                resource_ids = resources_dict[shift.role_id.id]
                shuffle(resource_ids)
                for resource in Resource.browse(resource_ids):
                    split_shift_intervals = shift_intervals & schedule_intervals_per_resource_id[resource.id]
                    # If the shift is out of resource's schedule, skip it.
                    if not split_shift_intervals:
                        continue
                    rate = shift.allocated_hours * 3600 / sum(
                        round((end - start).total_seconds())
                        for start, end, rec in split_shift_intervals
                    )
                    # Try to add the shift to the timeline.
                    timeline = self._get_new_timeline_if_fits_in(
                        split_shift_intervals,
                        rate,
                        resource.calendar_id.hours_per_day if resource.calendar_id else resource.company_id.resource_calendar_id.hours_per_day,
                        timeline_and_worked_hours_per_resource_id[resource.id].copy(),
                        empty_timeline,
                    )
                    # If we got a new timeline (not False), it means the shift fits for the resource
                    # (no overload, no "occupation rate" > 100%).
                    # If it fits, assign the shift to the resource and update the timeline.
                    # If a timeline is found, the resource can work the allocated_hours set on the shift.
                    # so the allocated_percentage is recomputed based on the working calendar of the
                    # resource and the allocated_hours set on the shift.
                    if timeline:
                        original_allocated_hours = shift.allocated_hours
                        shift.resource_id = resource
                        timeline_and_worked_hours_per_resource_id[resource.id] = timeline
                        start_utc = pytz.utc.localize(shift.start_datetime)
                        end_utc = pytz.utc.localize(shift.end_datetime)
                        resource_work_intervals, calendar_work_intervals = shift.resource_id \
                            .filtered('calendar_id') \
                            ._get_valid_work_intervals(start_utc, end_utc, calendars=shift.company_id.resource_calendar_id)
                        work_hours = shift._get_working_hours_over_period(start_utc, end_utc, resource_work_intervals, calendar_work_intervals)
                        shift.allocated_percentage = 100 * original_allocated_hours / work_hours if work_hours else 100
                        return True
            return False

        return open_shifts.filtered(find_resource).ids

# A. Represent the resoures shifts and the open shift on a timeline
#   Legend
#   ┏━━ : open shift                    ┌─────────────────── 2023/01/02 ────────────────┬─────────────────── 2023/01/03 ────────────────┐
#   ┌── : resource's shifts             0 ───────────── 8 ~~~~~~~~~~~~~ 16 ──────────── 0 ───────────── 8 ~~~~~~~~~~~~~ 16 ──────────── 0
#   ~~~ : resource's schedule           ├───────────────┼───────────────┼───────────────┼───────────────┼───────────────┼───────────────┤

# a/ Allocated Hours (ah) :                             ┏━━ 3h ━┓                                               ┌────── 8h ─────┐
#                                                       ┡━━━━━━━┹────────────────────── 7h ─────────────────────┴───────┬───────┘
#                                                       └───────────────────────────────────────────────────────────────┘

# b/ Rates [ah / (end - start)] :                       ┏━━ 75% ┓                                               ┌───── 100% ────┐
#                                                       ┡━━━━━━━┹───────────────────── 25% ─────────────────────┴───────┬───────┘
#                                                       └───────────────────────────────────────────────────────────────┘

# c/ Increments Timeline :                             ┌↑75%
#   Visual :                                           └↑25%    ↓75%                                            ↑100%   ↓25%    ↓100%
#   Array :                                             ┗━━━━━━━┹───────────────────────────────────────────────┴───────┴───────┘
# [
#    (dt(2023, 1, 2,  8, 0), +1.00),
#    (dt(2023, 1, 2, 12, 0), -0.75),
#    (dt(2023, 1, 3, 12, 0), +1.00),
#    (dt(2023, 1, 3, 16, 0), -0.25),
#    (dt(2023, 1, 3, 20, 0), -1.00),
# ]

# d/ Values Timeline :
#   Visual :                                            |100%   |25%                                            |125%   |100%   |0%
#   Array :                                             ┗━━━━━━━┹───────────────────────────────────────────────┴───────┴───────┘
# [
#    (dt(2023, 1, 2,  8, 0),  1.00),
#    (dt(2023, 1, 2, 12, 0),  0.25),
#    (dt(2023, 1, 3, 12, 0),  1.25),
#    (dt(2023, 1, 3, 16, 0),  1.00),
#    (dt(2023, 1, 3, 20, 0),  0.00),
# ]

# B. Try to assign each open shift to a resource

# 1) Check that the shift fits in the resource's schedule
#   We just get the schedule intervals of the resource, convert the shift to intervals, and check the difference.

# 2) Check that the resource would not be overloaded this day
#   Delimit days with ghost events at 0:00. Then compute the total time worked per day and compare it to the resource's max load.
#   We do so considering that every resource have the same time zone (the user's one).

# 3) ...and that it would not conflict with the resource's other shifts (sum of rates > 100%)
#   Visual :                            |0%             |100%   |25%                    |25%                    |125%   |100%   |0%     |0%
#   Array :                             └────── A ──────┗━━ B ━━┹────────── C ──────────┴───────────────────────┴───────┴───────┴───────┘
# [                                     ^                                               ^                                               ^
#    (dt(2023, 1, 2,  0, 0),  0.00), <
#    (dt(2023, 1, 2,  8, 0),  1.25),                         2) Worked Hours on 2023/01/02
#    (dt(2023, 1, 2, 12, 0),  0.25),                            = 8h * 0% (A) + 4h * 125% (B) + 12h * 25% (C)
#    (dt(2023, 1, 3,  0, 0),  0.25), <                          = 0h          + 5h            + 3h
#    (dt(2023, 1, 3, 12, 0),  1.00),                            = 8h => OK
#    (dt(2023, 1, 3, 16, 0),  0.75),
#    (dt(2023, 1, 3, 20, 0),  0.00),                         3) rate(B) = 100% => OK
#    (dt(2023, 1, 4,  0, 0),  0.00), <
# ]

    @api.model
    def _shift_records_to_timeline_per_resource_id(self, records):
        timeline_and_worked_hours_per_resource_id = defaultdict(list)
        for record in records:
            rate = record['allocated_hours'] * 3600 / (
                fields.Datetime.from_string(record['end_datetime']) - fields.Datetime.from_string(record['start_datetime'])
            ).total_seconds()
            timeline_and_worked_hours_per_resource_id[record['resource_id']].extend([
                (record['start_datetime'], rate), (record['end_datetime'], -rate)
            ])
        for resource_id, timeline in timeline_and_worked_hours_per_resource_id.items():
            timeline_and_worked_hours_per_resource_id[resource_id] = self._increments_to_values(timeline)
        return timeline_and_worked_hours_per_resource_id

    @api.model
    def _get_new_timeline_if_fits_in(self, split_shift_intervals, rate, resource_hours_per_day, timeline, empty_timeline):
        if rate > 1:
            return False
        add_midnights = True
        for split_shift_start, split_shift_end, _ in split_shift_intervals:
            start = split_shift_start.astimezone(pytz.utc).replace(tzinfo=None)
            end = split_shift_end.astimezone(pytz.utc).replace(tzinfo=None)
            increments = self._values_to_increments(timeline) + [(start, rate), (end, -rate)]
            if add_midnights:
                # Add ghost events at 0:00 to delimit days. This condition prevents from adding ghost events on each iteration.
                increments += empty_timeline
                add_midnights = False
            timeline = self._increments_to_values(increments, check=(start, end, resource_hours_per_day))
            if not timeline:
                return False
        return timeline

    @api.model
    def _increments_to_values(self, increments, check=False):
        """ Transform a timeline of increments into a timeline of values by accumulating the increments.
            If check is a tuple (start, end, resource_hours_per_day), the timeline is checked to ensure
            that the resource would not be overloaded this day or have an "occupation rate" > 100% between start and end.

            :param increments: List of tuples (instant, increment).
            :param check: False or a tuple (start, end, resource_hours_per_day).
            :return: List of tuples (instant, value) if check is False or the timeline is valid, else False.
        """
        if not increments:
            return []
        if check:
            start, end, resource_hours_per_day = check

        values = []
        # Sum and sort increments by instant.
        increments_sum_per_instant = defaultdict(float)
        for instant, increment in increments:
            increments_sum_per_instant[instant] += increment
        increments = list(increments_sum_per_instant.items())
        increments.sort(key=lambda increment: increment[0])

        def get_instant_plus_days(instant, days):
            return instant + relativedelta(days=days, hour=0, minute=0, second=0, microsecond=0)

        hours_per_day = defaultdict(float)
        last_instant, last_value = increments[0][0], 0.0
        for increment in increments:
            # Check if the resource is overloaded this day.
            hours_per_day[last_instant.date()] += last_value * (increment[0] - last_instant).total_seconds() / 3600
            if check and hours_per_day[last_instant.date()] > resource_hours_per_day and (
                get_instant_plus_days(start, 0) <= last_instant < get_instant_plus_days(end, 1)
            ):
                return False
            last_value += increment[1]
            last_instant = increment[0]
            # Check if the occupation rate exceeds 100%.
            if check and last_value > 1 and start <= last_instant <= end:
                return False
            values.append((last_instant, last_value))
        return values

    @api.model
    def _values_to_increments(self, values):
        """ Transform a timeline of values into a timeline of increments by subtracting the values.

            :param values: List of tuples (instant, value).
            :return: List of tuples (instant, increment).
        """
        increments = []
        last_value = 0
        for value in values:
            increments.append((value[0], value[1] - last_value))
            last_value = value[1]
        return increments

    # ----------------------------------------------------
    # Gantt - Calendar view
    # ----------------------------------------------------

    @api.model
    def gantt_resource_work_interval(self, slot_ids):
        """ Returns the work intervals of the resources corresponding to the provided slots

            This method is used in a rpc call

        :param slot_ids: The slots the work intervals have to be returned for.
        :return: list of dicts { resource_id: [Intervals] } and { resource_id: flexible_hours }.
        """
        # Get the oldest start date and latest end date from the slots.
        domain = [("id", "in", slot_ids)]
        read_group_fields = ["start_datetime:min", "end_datetime:max", "resource_id:recordset", "__count"]
        planning_slot_read_group = self.env["planning.slot"]._read_group(domain, [], read_group_fields)
        start_datetime, end_datetime, resources, count = planning_slot_read_group[0]
        if not count:
            return [{}]

        # Get default start/end datetime if any.
        default_start_datetime = (fields.Datetime.to_datetime(self._context.get('default_start_datetime')) or datetime.min).replace(tzinfo=pytz.utc)
        default_end_datetime = (fields.Datetime.to_datetime(self._context.get('default_end_datetime')) or datetime.max).replace(tzinfo=pytz.utc)

        start_datetime = max(default_start_datetime, start_datetime.replace(tzinfo=pytz.utc))
        end_datetime = min(default_end_datetime, end_datetime.replace(tzinfo=pytz.utc))

        # Get slots' resources and current company work intervals.
        work_intervals_per_resource, dummy = resources._get_valid_work_intervals(start_datetime, end_datetime)
        company_calendar = self.env.company.resource_calendar_id
        company_calendar_work_intervals = company_calendar._work_intervals_batch(start_datetime, end_datetime)

        # Export work intervals in UTC
        work_intervals_per_resource[False] = company_calendar_work_intervals[False]
        work_interval_per_resource = defaultdict(list)
        for resource_id, resource_work_intervals in work_intervals_per_resource.items():
            for resource_work_interval in resource_work_intervals:
                work_interval_per_resource[resource_id].append(
                    (resource_work_interval[0].astimezone(pytz.UTC), resource_work_interval[1].astimezone(pytz.UTC))
                )
        # Add the flexible status per resource to the output
        flexible_per_resource = {resource.id: not bool(resource.calendar_id) for resource in set(resources)}
        flexible_per_resource[False] = True
        return [work_interval_per_resource, flexible_per_resource]

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        start_datetime = fields.Datetime.from_string(start_date)
        end_datetime = fields.Datetime.from_string(end_date)
        resource_ids = set()

        # function to "mark" top level rows concerning resources
        # the propagation of that item to subrows is taken care of in the traverse function below
        def tag_resource_rows(rows):
            for row in rows:
                group_bys = row.get('groupedBy')
                res_id = row.get('resId')
                if group_bys:
                    # if resource_id is the first grouping attribute, we mark the row
                    if group_bys[0] == 'resource_id' and res_id:
                        resource_id = res_id
                        resource_ids.add(resource_id)
                        row['resource_id'] = resource_id
                    # else we recursively traverse the rows where resource_id appears in the group_by
                    elif 'resource_id' in group_bys:
                        tag_resource_rows(row.get('rows'))

        tag_resource_rows(rows)
        resources = self.env['resource.resource'].browse(resource_ids).filtered('calendar_id')
        leaves_mapping = resources._get_unavailable_intervals(start_datetime, end_datetime)
        company_leaves = self.env.company.resource_calendar_id._unavailable_intervals(start_datetime.replace(tzinfo=pytz.utc), end_datetime.replace(tzinfo=pytz.utc))

        # function to recursively replace subrows with the ones returned by func
        def traverse(func, row):
            new_row = dict(row)
            if new_row.get('resource_id'):
                for sub_row in new_row.get('rows'):
                    sub_row['resource_id'] = new_row['resource_id']
            new_row['rows'] = [traverse(func, row) for row in new_row.get('rows')]
            return func(new_row)

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        # for a single row, inject unavailability data
        def inject_unavailability(row):
            new_row = dict(row)

            calendar = company_leaves
            if row.get('resource_id'):
                resource_id = self.env['resource.resource'].browse(row.get('resource_id'))
                if resource_id:
                    if not resource_id.calendar_id:
                        return new_row
                    calendar = leaves_mapping[resource_id.id]

            # remove intervals smaller than a cell, as they will cause half a cell to turn grey
            # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
            # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
            notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, calendar)
            new_row['unavailabilities'] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
            return new_row

        return [traverse(inject_unavailability, row) for row in rows]

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    # ----------------------------------------------------
    # Period Duplication
    # ----------------------------------------------------

    @api.model
    def action_copy_previous_week(self, date_start_week, view_domain):
        date_end_copy = datetime.strptime(date_start_week, DEFAULT_SERVER_DATETIME_FORMAT)
        date_start_copy = date_end_copy - relativedelta(days=7)
        domain = [
            ('recurrency_id', '=', False),
            ('was_copied', '=', False)
        ]
        for dom in view_domain:
            if dom in ['|', '&', '!']:
                domain.append(dom)
            elif dom[0] == 'start_datetime':
                domain.append(('start_datetime', '>=', date_start_copy))
            elif dom[0] == 'end_datetime':
                domain.append(('end_datetime', '<=', date_end_copy))
            else:
                domain.append(tuple(dom))
        slots_to_copy = self.search(domain)

        new_slot_values = []
        new_slot_values = slots_to_copy._copy_slots(date_start_copy, date_end_copy, relativedelta(days=7))
        slots_to_copy.write({'was_copied': True})
        if new_slot_values:
            return [self.create(new_slot_values).ids, slots_to_copy.ids]
        return False

    def action_rollback_copy_previous_week(self, copied_slot_ids):
        self.browse(copied_slot_ids).was_copied = False
        self.unlink()

    # ----------------------------------------------------
    # Sending Shifts
    # ----------------------------------------------------

    def get_employees_without_work_email(self):
        """ Check if the employees to send the slot have a work email set.

            This method is used in a rpc call.

            :returns: a dictionnary containing the all needed information to continue the process.
                Returns None, if no employee or all employees have an email set.
        """
        self.ensure_one()
        if not self.employee_id.check_access_rights('write', raise_exception=False):
            return None
        employees = self.employee_id or self._get_employees_to_send_slot()
        employee_ids_without_work_email = employees.filtered(lambda employee: not employee.work_email).ids
        if not employee_ids_without_work_email:
            return None
        context = dict(self._context)
        context['force_email'] = True
        context['form_view_ref'] = 'planning.hr_employee_view_form_simplified'
        return {
            'relation': 'hr.employee',
            'res_ids': employee_ids_without_work_email,
            'context': context,
        }

    def _get_employees_to_send_slot(self):
        self.ensure_one()
        if not self.employee_id or not self.employee_id.work_email:
            domain = [('company_id', '=', self.company_id.id), ('work_email', '!=', False)]
            if self.role_id:
                domain = expression.AND([
                    domain,
                    ['|', ('planning_role_ids', '=', False), ('planning_role_ids', 'in', self.role_id.id)]])
            return self.env['hr.employee'].sudo().search(domain)
        return self.employee_id

    def _get_notification_action(self, notif_type, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notif_type,
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_planning_publish_and_send(self):
        notif_type = "success"
        start, end = min(self.mapped('start_datetime')), max(self.mapped('end_datetime'))
        if all(shift.state == 'published' for shift in self) or not start or not end:
            notif_type = "warning"
            message = _('There are no shifts to publish and send.')
        else:
            planning = self.env['planning.planning'].create({
                'start_datetime': start,
                'end_datetime': end,
            })
            planning._send_planning(slots=self, employees=self.employee_id)
            message = _('The shifts have successfully been published and sent.')
        return self._get_notification_action(notif_type, message)

    def action_send(self):
        self.ensure_one()
        if not self.employee_id or not self.employee_id.work_email:
            self.state = 'published'
        employee_ids = self._get_employees_to_send_slot()
        self._send_slot(employee_ids, self.start_datetime, self.end_datetime)
        message = _("The shift has successfully been sent.")
        return self._get_notification_action('success', message)

    def action_unpublish(self):
        if not self.env.user.has_group('planning.group_planning_manager'):
            raise AccessError(_('You are not allowed to reset to draft shifts.'))
        published_shifts = self.filtered(lambda shift: shift.state == 'published' and shift.resource_type != 'material')
        if published_shifts:
            published_shifts.write({'state': 'draft', 'publication_warning': False,})
            notif_type = "success"
            message = _('The shifts have been successfully reset to draft.')
        else:
            notif_type = "warning"
            message = _('There are no shifts to reset to draft.')
        return self._get_notification_action(notif_type, message)

    # ----------------------------------------------------
    # Business Methods
    # ----------------------------------------------------

    def _calculate_slot_duration(self):
        self.ensure_one()
        if not self.start_datetime or not self.end_datetime:
            return 0.0
        period = self.end_datetime - self.start_datetime
        slot_duration = period.total_seconds() / 3600
        max_duration = (period.days + (1 if period.seconds else 0)) * self.company_id.resource_calendar_id.hours_per_day
        if not max_duration or max_duration >= slot_duration:
            return slot_duration
        return max_duration

    # ----------------------------------------------------
    # Copy Slots
    # ----------------------------------------------------

    def _add_delta_with_dst(self, start, delta):
        """
        Add to start, adjusting the hours if needed to account for a shift in the local timezone between the
        start date and the resulting date (typically, because of DST)

        :param start: origin date in UTC timezone, but without timezone info (a naive date)
        :return resulting date in the UTC timezone (a naive date)
        """
        try:
            tz = pytz.timezone(self._get_tz())
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
        start = start.replace(tzinfo=pytz.utc).astimezone(tz).replace(tzinfo=None)
        result = start + delta
        return tz.localize(result).astimezone(pytz.utc).replace(tzinfo=None)

    def _get_half_day_interval(self, values):
        """
            This method computes the afternoon and/or the morning whole interval where the planning slot exists.
            The resulting interval frames the slot in a bigger interval beginning before the slot (max 11:59:59 sooner)
            and finishing later (max 11:59:59 later)

            :param values: a dict filled in with new planning.slot vals
            :return an interval
        """
        return Intervals([(
            self._get_half_day_datetime(values['start_datetime']),
            self._get_half_day_datetime(values['end_datetime'], end=True),
            self.env['resource.calendar.attendance']
        )])

    def _get_half_day_datetime(self, dt, end=False):
        """
            This method computes a datetime in order to frame the slot in a bigger interval begining at midnight or
            noon and ending at midnight or noon.

            This method returns :
            - If end is False : Greatest datetime between midnight and noon that is sooner than the `dt` datetime;
            - Otherwise : Lowest datetime between midnight and noon that is later than the `dt` datetime.

            :param dt: input datetime
            :param end: wheter the dt is the end, resp. the start, of the interval if set, resp. not set.
            :return a datetime
        """
        self.ensure_one()
        tz = pytz.timezone(self._get_tz())
        localized_dt = pytz.utc.localize(dt).astimezone(tz)
        midday = localized_dt.replace(hour=12, minute=0, second=0)
        if end:
            return midday if midday > localized_dt else (localized_dt.replace(hour=0, minute=0, second=0) + timedelta(days=1))
        return midday if midday < localized_dt else localized_dt.replace(hour=0, minute=0, second=0)

    def _init_remaining_hours_to_plan(self, remaining_hours_to_plan):
        """
            Inits the remaining_hours_to_plan dict for a given slot and returns wether
            there are enough remaining hours.

            :return a bool representing wether or not there are still hours remaining
        """
        self.ensure_one()
        return True

    def _update_remaining_hours_to_plan_and_values(self, remaining_hours_to_plan, values):
        """
            Update the remaining_hours_to_plan with the allocated hours of the slot in `values`
            and returns wether there are enough remaining hours.

            If remaining_hours is strictly positive, and the allocated hours of the slot in `values` is
            higher than remaining hours, than update the values in order to consume at most the
            number of remaining_hours still available.

            :return a bool representing wether or not there are still hours remaining
        """
        self.ensure_one()
        return True

    def _get_split_slot_values(self, values, intervals, remaining_hours_to_plan, unassign=False):
        """
            Generates and returns slots values within the given intervals

            The slot in values, which represents a forecast planning slot, is split in multiple parts
            filling the (available) intervals.

            :return a vals list of the slot to create
        """
        self.ensure_one()
        splitted_slot_values = []
        for start_inter, end_inter, _resource in intervals:
            new_slot_vals = {
                **values,
                'start_datetime': start_inter.astimezone(pytz.utc).replace(tzinfo=None),
                'end_datetime': end_inter.astimezone(pytz.utc).replace(tzinfo=None),
            }
            was_updated = self._update_remaining_hours_to_plan_and_values(remaining_hours_to_plan, new_slot_vals)
            new_slot_vals['allocated_hours'] = float_utils.float_round(
                ((end_inter - start_inter).total_seconds() / 3600.0) * (self.allocated_percentage / 100.0),
                precision_digits=2
            )
            if not was_updated:
                return splitted_slot_values
            if unassign:
                new_slot_vals['resource_id'] = False
            splitted_slot_values.append(new_slot_vals)
        return splitted_slot_values

    def _copy_slots(self, start_dt, end_dt, delta):
        """
            Copy slots planned between `start_dt` and `end_dt`, after a `delta`

            Takes into account the resource calendar and the slots already planned.
            All the slots will be copied, whatever the value of was_copied is.

            :return a vals list of the slot to create
        """
        # 1) Retrieve all the slots of the new period and create intervals within the slots will have to be unassigned (resource_slots_intervals),
        #    add it to `unavailable_intervals_per_resource`
        # 2) Retrieve all the calendars for the resource and their validity intervals (intervals within which the calendar is valid for the resource)
        # 3) For each calendar, retrieve the attendances and the leaves. Add attendances by resource in `attendance_intervals_per_resource` and
        #    the leaves by resource in `unavailable_intervals_per_resource`
        # 4) For each slot, check if the slot is at least within an attendance and outside a company leave :
        #    - If it is a planning :
        #       - Copy it if the resource is available
        #       - Copy and unassign it if the resource isn't available
        #    - Otherwise :
        #       - Split it and assign the part within resource work intervals
        #       - Split it and unassign the part within resource leaves and outside company leaves
        resource_per_calendar = defaultdict(lambda: self.env['resource.resource'])
        resource_calendar_validity_intervals = defaultdict(dict)
        attendance_intervals_per_resource = defaultdict(Intervals)  # key: resource, values: attendance intervals
        unavailable_intervals_per_resource = defaultdict(Intervals)  # key: resource, values: unavailable intervals
        attendance_intervals_per_calendar = defaultdict(Intervals)  # key: calendar, values: attendance intervals (used for company calendars)
        leave_intervals_per_calendar = defaultdict(Intervals)  # key: calendar, values: leave intervals (used for company calendars)
        new_slot_values = []
        # date utils variable
        start_dt_delta = start_dt + delta
        end_dt_delta = end_dt + delta
        start_dt_delta_utc = pytz.utc.localize(start_dt_delta)
        end_dt_delta_utc = pytz.utc.localize(end_dt_delta)
        # 1)
        # Search for all resource slots already planned
        resource_slots = self.search([
            ('start_datetime', '>=', start_dt_delta),
            ('end_datetime', '<=', end_dt_delta),
            ('resource_id', 'in', self.resource_id.ids)
        ])
        # And convert it into intervals
        for slot in resource_slots:
            unavailable_intervals_per_resource[slot.resource_id] |= Intervals([(
                pytz.utc.localize(slot.start_datetime),
                pytz.utc.localize(slot.end_datetime),
                self.env['resource.calendar.leaves'])])
        # 2)
        resource_calendar_validity_intervals = self.resource_id.sudo()._get_calendars_validity_within_period(
            start_dt_delta_utc, end_dt_delta_utc)
        for slot in self:
            if slot.resource_id:
                for calendar in resource_calendar_validity_intervals[slot.resource_id.id]:
                    resource_per_calendar[calendar] |= slot.resource_id
            company_calendar_id = slot.company_id.resource_calendar_id
            resource_per_calendar[company_calendar_id] |= self.env['resource.resource']  # ensures the company_calendar will be in resource_per_calendar keys.
        # 3)
        for calendar, resources in resource_per_calendar.items():
            # For each calendar, retrieves the work intervals of every resource
            attendances = calendar._attendance_intervals_batch(
                start_dt_delta_utc,
                end_dt_delta_utc,
                resources=resources
            )
            leaves = calendar._leave_intervals_batch(
                start_dt_delta_utc,
                end_dt_delta_utc,
                resources=resources
            )
            attendance_intervals_per_calendar[calendar] = attendances[False]
            leave_intervals_per_calendar[calendar] = leaves[False]
            for resource in resources:
                # for each resource, adds his/her attendances and unavailabilities for this calendar, during the calendar validity interval.
                attendance_intervals_per_resource[resource] |= (attendances[resource.id] & resource_calendar_validity_intervals[resource.id][calendar])
                unavailable_intervals_per_resource[resource] |= (leaves[resource.id] & resource_calendar_validity_intervals[resource.id][calendar])
        # 4)
        remaining_hours_to_plan = {}
        for slot in self:
            if not slot._init_remaining_hours_to_plan(remaining_hours_to_plan):
                continue
            values = slot.copy_data(default={'state': 'draft'})[0]
            if not values.get('start_datetime') or not values.get('end_datetime'):
                continue
            values['start_datetime'] = slot._add_delta_with_dst(values['start_datetime'], delta)
            values['end_datetime'] = slot._add_delta_with_dst(values['end_datetime'], delta)
            if any(
                new_slot['resource_id'] == values['resource_id'] and
                new_slot['start_datetime'] <= values['end_datetime'] and
                new_slot['end_datetime'] >= values['start_datetime']
                for new_slot in new_slot_values
            ):
                values['resource_id'] = False
            interval = Intervals([(
                pytz.utc.localize(values.get('start_datetime')),
                pytz.utc.localize(values.get('end_datetime')),
                self.env['resource.calendar.attendance']
            )])
            company_calendar = slot.company_id.resource_calendar_id
            # Check if interval is contained in the resource work interval
            attendance_resource = attendance_intervals_per_resource[slot.resource_id] if slot.resource_id else attendance_intervals_per_calendar[company_calendar]
            attendance_interval_resource = interval & attendance_resource
            # Check if interval is contained in the company attendances interval
            attendance_interval_company = interval & attendance_intervals_per_calendar[company_calendar]
            # Check if interval is contained in the company leaves interval
            unavailable_interval_company = interval & leave_intervals_per_calendar[company_calendar]
            if slot.allocation_type == 'planning' and not unavailable_interval_company and not attendance_interval_resource:
                # If the slot is not a forecast and there are no expected attendance, neither a company leave
                # check if the slot is planned during an afternoon or a morning during which the resource/company works/is opened

                # /!\ Name of such attendance is an "Extended Attendance", see hereafter
                interval = slot._get_half_day_interval(values)  # Get the afternoon and/or the morning whole interval where the planning slot exists.
                attendance_interval_resource = interval & attendance_resource
                attendance_interval_company = interval & attendance_intervals_per_calendar[company_calendar]
                unavailable_interval_company = interval & leave_intervals_per_calendar[company_calendar]
            unavailable_interval_resource = unavailable_interval_company if not slot.resource_id else (interval & unavailable_intervals_per_resource[slot.resource_id])
            if (attendance_interval_resource - unavailable_interval_company) or (attendance_interval_company - unavailable_interval_company):
                # Either the employee has, at least, some attendance that are not during the company unavailability
                # Either the company has, at least, some attendance that are not during the company unavailability

                if slot.allocation_type == 'planning':
                    # /!\ It can be an "Extended Attendance" (see hereabove), and the slot may be unassigned.
                    if unavailable_interval_resource or not attendance_interval_resource:
                        # if the slot is during an resourece unavailability, or the employee is not attending during the slot
                        if slot.resource_type != 'user':
                            # if the resource is not an employee and the resource is not available, do not copy it nor unassign it
                            continue
                        values['resource_id'] = False
                    if not slot._update_remaining_hours_to_plan_and_values(remaining_hours_to_plan, values):
                        # make sure the hours remaining are enough
                        continue
                    new_slot_values.append(values)
                else:
                    if attendance_interval_resource:
                        # if the resource has attendances, at least during a while of the future slot lifetime,
                        # 1) Work interval represents the availabilities of the employee
                        # 2) The unassigned intervals represents the slots where the employee should be unassigned
                        #    (when the company is not unavailable and the employee is unavailable)
                        work_interval_employee = (attendance_interval_resource - unavailable_interval_resource)
                        unassigned_interval = unavailable_interval_resource - unavailable_interval_company
                        split_slot_values = slot._get_split_slot_values(values, work_interval_employee, remaining_hours_to_plan)
                        if slot.resource_type == 'user':
                            split_slot_values += slot._get_split_slot_values(values, unassigned_interval, remaining_hours_to_plan, unassign=True)
                    elif slot.resource_type != 'user':
                        # If the resource type is not user and the slot can not be assigned to the resource, do not copy not unassign it
                        continue
                    else:
                        # When the employee has no attendance at all, we are in the case where the employee has a calendar different than the
                        # company (or no more calendar), so the slot will be unassigned
                        unassigned_interval = attendance_interval_company - unavailable_interval_company
                        split_slot_values = slot._get_split_slot_values(values, unassigned_interval, remaining_hours_to_plan, unassign=True)
                    # merge forecast slots in order to have visually bigger slots
                    new_slot_values += self._merge_slots_values(split_slot_values, unassigned_interval)
        return new_slot_values

    def _display_name_fields(self):
        """ List of fields that can be displayed in the display_name """
        return ['resource_id', 'role_id']

    def _get_fields_breaking_publication(self):
        """ Fields list triggering the `publication_warning` to True when updating shifts """
        return [
            'resource_id',
            'resource_type',
            'start_datetime',
            'end_datetime',
            'role_id',
        ]

    @api.model
    def _get_template_fields(self):
        # key -> field from template
        # value -> field from slot
        return {'role_id': 'role_id', 'start_time': 'start_datetime', 'duration': 'duration'}

    def _get_tz(self):
        return (self.env.user.tz
                or self.employee_id.tz
                or self.resource_id.tz
                or self._context.get('tz')
                or self.company_id.resource_calendar_id.tz
                or 'UTC')

    def _prepare_template_values(self):
        """ extract values from shift to create a template """
        # compute duration w/ tzinfo otherwise DST will not be taken into account
        destination_tz = pytz.timezone(self._get_tz())
        start_datetime = pytz.utc.localize(self.start_datetime).astimezone(destination_tz)
        end_datetime = pytz.utc.localize(self.end_datetime).astimezone(destination_tz)

        # convert time delta to hours and minutes
        total_seconds = (end_datetime - start_datetime).total_seconds()
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)

        return {
            'start_time': start_datetime.hour + start_datetime.minute / 60.0,
            'duration': h + (m / 60.0),
            'role_id': self.role_id.id
        }

    def _manage_archived_resources(self, departure_date):
        shift_vals_list = []
        shift_ids_to_remove_resource = []
        for slot in self:
            split_time = pytz.timezone(self._get_tz()).localize(departure_date).astimezone(pytz.utc).replace(tzinfo=None)
            if (slot.start_datetime < split_time) and (slot.end_datetime > split_time):
                shift_vals_list.append({
                    'start_datetime': split_time,
                    **slot._prepare_shift_vals(),
                })
                if split_time > slot.start_datetime:
                    slot.write({'end_datetime': split_time})
            elif slot.start_datetime >= split_time:
                shift_ids_to_remove_resource.append(slot.id)
        if shift_vals_list:
            self.sudo().create(shift_vals_list)
        if shift_ids_to_remove_resource:
            self.sudo().browse(shift_ids_to_remove_resource).write({'resource_id': False})

    def _group_expand_resource_id(self, resources, domain, order):
        dom_tuples = [(dom[0], dom[1]) for dom in domain if isinstance(dom, (tuple, list)) and len(dom) == 3]
        resource_ids = self.env.context.get('filter_resource_ids', False)
        if resource_ids:
            return self.env['resource.resource'].search([('id', 'in', resource_ids)], order=order)
        if self.env.context.get('planning_expand_resource') and ('start_datetime', '<=') in dom_tuples and ('end_datetime', '>=') in dom_tuples:
            if ('resource_id', '=') in dom_tuples or ('resource_id', 'ilike') in dom_tuples or ('resource_id', 'in') in dom_tuples:
                filter_domain = self._expand_domain_m2o_groupby(domain, 'resource_id')
                return self.env['resource.resource'].search(filter_domain, order=order)
            filters = self._expand_domain_dates(domain)
            resources = self.env['planning.slot'].search(filters).mapped('resource_id')
            return resources.search([('id', 'in', resources.ids)], order=order)
        return resources

    def _read_group_role_id(self, roles, domain, order):
        dom_tuples = [(dom[0], dom[1]) for dom in domain if isinstance(dom, list) and len(dom) == 3]
        if self._context.get('planning_expand_role') and ('start_datetime', '<=') in dom_tuples and ('end_datetime', '>=') in dom_tuples:
            if ('role_id', '=') in dom_tuples or ('role_id', 'ilike') in dom_tuples:
                filter_domain = self._expand_domain_m2o_groupby(domain, 'role_id')
                return self.env['planning.role'].search(filter_domain, order=order)
            filters = expression.AND([[('role_id.active', '=', True)], self._expand_domain_dates(domain)])
            return self.env['planning.slot'].search(filters).mapped('role_id')
        return roles

    @api.model
    def _expand_domain_m2o_groupby(self, domain, filter_field=False):
        filter_domain = []
        for dom in domain:
            if dom[0] == filter_field:
                field = self._fields[dom[0]]
                if field.type == 'many2one' and len(dom) == 3:
                    if dom[1] in ['=', 'in']:
                        filter_domain = expression.OR([filter_domain, [('id', dom[1], dom[2])]])
                    elif dom[1] == 'ilike':
                        rec_name = self.env[field.comodel_name]._rec_name
                        filter_domain = expression.OR([filter_domain, [(rec_name, dom[1], dom[2])]])
        return filter_domain

    def _expand_domain_dates(self, domain):
        filters = []
        for dom in domain:
            if len(dom) == 3 and dom[0] == 'start_datetime' and dom[1] == '<=':
                max_date = dom[2] if dom[2] else datetime.now()
                max_date = max_date if isinstance(max_date, date) else datetime.strptime(max_date, '%Y-%m-%d %H:%M:%S')
                max_date = max_date + timedelta(days=7)
                filters.append((dom[0], dom[1], max_date))
            elif len(dom) == 3 and dom[0] == 'end_datetime' and dom[1] == '>=':
                min_date = dom[2] if dom[2] else datetime.now()
                min_date = min_date if isinstance(min_date, date) else datetime.strptime(min_date, '%Y-%m-%d %H:%M:%S')
                min_date = min_date - timedelta(days=7)
                filters.append((dom[0], dom[1], min_date))
            else:
                filters.append(dom)
        return filters

    @api.model
    def _format_datetime_to_user_tz(self, datetime_without_tz, record_env, tz=None, lang_code=False):
        return format_datetime(record_env, datetime_without_tz, tz=tz, dt_format='short', lang_code=lang_code)

    def _send_slot(self, employee_ids, start_datetime, end_datetime, include_unassigned=True, message=None):
        if not include_unassigned:
            self = self.filtered(lambda s: s.resource_id)
        if not self:
            return False
        self.ensure_one()

        employee_with_backend = employee_ids.filtered(lambda e: e.user_id and e.user_id.has_group('planning.group_planning_user'))
        employee_without_backend = employee_ids - employee_with_backend
        planning = False
        if employee_without_backend:
            planning = self.env['planning.planning'].create({
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'include_unassigned': include_unassigned,
            })

        template = self.env.ref('planning.email_template_slot_single')
        employee_url_map = {**employee_without_backend.sudo()._planning_get_url(planning), **employee_with_backend._slot_get_url(self)}

        view_context = dict(self._context)
        view_context.update({
            'open_shift_available': not self.employee_id,
            'mail_subject': _('Planning: new open shift available on'),
        })

        if self.employee_id:
            employee_ids = self.employee_id
            if self.allow_self_unassign:
                if employee_ids.filtered(lambda e: e.user_id and e.user_id.has_group('planning.group_planning_user')):
                    unavailable_link = '/planning/unassign/%s/%s' % (self.employee_id.sudo().employee_token, self.id)
                else:
                    unavailable_link = '/planning/%s/%s/unassign/%s?message=1' % (planning.access_token, self.employee_id.sudo().employee_token, self.id)
                view_context.update({'unavailable_link': unavailable_link})
            view_context.update({'mail_subject': _('Planning: new shift on')})

        mails_to_send_ids = []
        for employee in employee_ids.filtered(lambda e: e.work_email):
            if not self.employee_id and employee in employee_with_backend:
                view_context.update({'available_link': '/planning/assign/%s/%s' % (employee.sudo().employee_token, self.id)})
            elif not self.employee_id:
                view_context.update({'available_link': '/planning/%s/%s/assign/%s?message=1' % (planning.access_token, employee.sudo().employee_token, self.id)})
            start_datetime = self._format_datetime_to_user_tz(self.start_datetime, employee.env, tz=employee.tz, lang_code=employee.user_partner_id.lang)
            end_datetime = self._format_datetime_to_user_tz(self.end_datetime, employee.env, tz=employee.tz, lang_code=employee.user_partner_id.lang)
            unassign_deadline = self._format_datetime_to_user_tz(self.unassign_deadline, employee.env, tz=employee.tz, lang_code=employee.user_partner_id.lang)
            # update context to build a link for view in the slot
            view_context.update({
                'link': employee_url_map[employee.id],
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'employee_name': employee.name,
                'work_email': employee.work_email,
                'unassign_deadline': unassign_deadline
            })
            mail_id = template.with_context(view_context).send_mail(self.id, email_layout_xmlid='mail.mail_notification_light')
            mails_to_send_ids.append(mail_id)

        mails_to_send = self.env['mail.mail'].sudo().browse(mails_to_send_ids)
        if mails_to_send:
            mails_to_send.send()

        self.write({
            'state': 'published',
            'publication_warning': False,
        })

    def _send_shift_assigned(self, slot, human_resource):
        email_from = slot.company_id.email or ''
        assignee = slot.resource_id.employee_id

        template = self.env.ref('planning.email_template_shift_switch_email', raise_if_not_found=False)
        start_datetime = self._format_datetime_to_user_tz(slot.start_datetime, assignee.env, tz=assignee.tz, lang_code=assignee.user_partner_id.lang)
        end_datetime = self._format_datetime_to_user_tz(slot.end_datetime, assignee.env, tz=assignee.tz, lang_code=assignee.user_partner_id.lang)
        template_context = {
            'old_assignee_name': assignee.name,
            'new_assignee_name': human_resource.employee_id.name,
            'start_datetime': start_datetime,
            'end_datetime': end_datetime,
        }
        if template and assignee != human_resource.employee_id:
            template.with_context(**template_context).send_mail(
                slot.id,
                email_values={
                    'email_to': assignee.work_email,
                    'email_from': email_from,
                },
                email_layout_xmlid='mail.mail_notification_light',
            )

    # ---------------------------------------------------
    # Slots generation/copy
    # ---------------------------------------------------

    @api.model
    def _merge_slots_values(self, slots_to_merge, unforecastable_intervals):
        """
            Return a list of merged slots

            - `slots_to_merge` is a sorted list of slots
            - `unforecastable_intervals` are the intervals where the employee cannot work

            Example:
                slots_to_merge = [{
                    'start_datetime': '2021-08-01 08:00:00',
                    'end_datetime': '2021-08-01 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-01 13:00:00',
                    'end_datetime': '2021-08-01 17:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-02 08:00:00',
                    'end_datetime': '2021-08-02 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-03 08:00:00',
                    'end_datetime': '2021-08-03 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-04 13:00:00',
                    'end_datetime': '2021-08-04 17:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }]
                unforecastable = Intervals([(
                    datetime.datetime(2021, 8, 2, 13, 0, 0, tzinfo='UTC')',
                    datetime.datetime(2021, 8, 2, 17, 0, 0, tzinfo='UTC')',
                    self.env['resource.calendar.attendance'],
                )])

                result : [{
                    'start_datetime': '2021-08-01 08:00:00',
                    'end_datetime': '2021-08-02 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 12.0,
                }, {
                    'start_datetime': '2021-08-03 08:00:00',
                    'end_datetime': '2021-08-03 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-04 13:00:00',
                    'end_datetime': '2021-08-04 17:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }]

            :return list of merged slots
        """
        if not slots_to_merge:
            return slots_to_merge
        # resulting vals_list of the merged slots
        new_slots_vals_list = []
        # accumulator for mergeable slots
        sum_allocated_hours = 0
        to_merge = []
        # invariants for mergeable slots
        common_allocated_percentage = slots_to_merge[0]['allocated_percentage']
        resource_id = slots_to_merge[0].get('resource_id')
        start_datetime = slots_to_merge[0]['start_datetime']
        previous_end_datetime = start_datetime
        for slot in slots_to_merge:
            mergeable = True
            if (not slot['start_datetime']
               or common_allocated_percentage != slot['allocated_percentage']
               or resource_id != slot['resource_id']
               or (slot['start_datetime'] - previous_end_datetime).total_seconds() > 3600 * 24):
                # last condition means the elapsed time between the previous end time and the
                # start datetime of the current slot should not be bigger than 24hours
                # if it's the case, then the slot can not be merged.
                mergeable = False
            if mergeable:
                end_datetime = slot['end_datetime']
                interval = Intervals([(
                    pytz.utc.localize(start_datetime),
                    pytz.utc.localize(end_datetime),
                    self.env['resource.calendar.attendance']
                )])
                if not (interval & unforecastable_intervals):
                    sum_allocated_hours += slot['allocated_hours']
                    if (end_datetime - start_datetime).total_seconds() < 3600 * 24:
                        # If the elapsed time between the first start_datetime and the
                        # current end_datetime is not higher than 24hours,
                        # slots cannot be merged as it won't be a forecast
                        to_merge.append(slot)
                    else:
                        to_merge = [{
                            **slot,
                            'start_datetime': start_datetime,
                            'allocated_hours': sum_allocated_hours,
                        }]
                else:
                    mergeable = False
            if not mergeable:
                new_slots_vals_list += to_merge
                to_merge = [slot]
                start_datetime = slot['start_datetime']
                common_allocated_percentage = slot['allocated_percentage']
                resource_id = slot.get('resource_id')
                sum_allocated_hours = slot['allocated_hours']
            previous_end_datetime = slot['end_datetime']
        new_slots_vals_list += to_merge
        return new_slots_vals_list

    def _get_working_hours_over_period(self, start_utc, end_utc, work_intervals, calendar_intervals):
        start = max(start_utc, pytz.utc.localize(self.start_datetime))
        end = min(end_utc, pytz.utc.localize(self.end_datetime))
        slot_interval = Intervals([(
            start, end, self.env['resource.calendar.attendance']
        )])
        working_intervals = work_intervals[self.resource_id.id] \
            if self.resource_id \
            else calendar_intervals[self.company_id.resource_calendar_id.id]
        return round(sum_intervals(slot_interval & working_intervals), 2)

    def _get_duration_over_period(self, start_utc, stop_utc, work_intervals, calendar_intervals, has_allocated_hours=True):
        assert start_utc.tzinfo and stop_utc.tzinfo
        self.ensure_one()
        start, stop = start_utc.replace(tzinfo=None), stop_utc.replace(tzinfo=None)
        if has_allocated_hours and self.start_datetime >= start and self.end_datetime <= stop:
            return self.allocated_hours
        # if the slot goes over the gantt period, compute the duration only within
        # the gantt period
        ratio = self.allocated_percentage / 100.0
        working_hours = self._get_working_hours_over_period(start_utc, stop_utc, work_intervals, calendar_intervals)
        return working_hours * ratio

    def _gantt_progress_bar_resource_id(self, res_ids, start, stop):
        start_naive, stop_naive = start.replace(tzinfo=None), stop.replace(tzinfo=None)

        resources = self.env['resource.resource'].with_context(active_test=False).search([('id', 'in', res_ids)])
        planning_slots = self.env['planning.slot'].search([
            ('resource_id', 'in', res_ids),
            ('start_datetime', '<=', stop_naive),
            ('end_datetime', '>=', start_naive),
        ])
        planned_hours_mapped = defaultdict(float)
        resource_work_intervals, calendar_work_intervals = resources.sudo()._get_valid_work_intervals(start, stop)
        for slot in planning_slots:
            planned_hours_mapped[slot.resource_id.id] += slot._get_duration_over_period(
                start, stop, resource_work_intervals, calendar_work_intervals
            )
        # Compute employee work hours based on its work intervals.
        work_hours = {
            resource_id: sum_intervals(work_intervals)
            for resource_id, work_intervals in resource_work_intervals.items()
        }
        return {
            resource.id: {
                'is_material_resource': resource.resource_type == 'material',
                'resource_color': resource.color,
                'value': planned_hours_mapped[resource.id],
                'max_value': work_hours.get(resource.id, 0.0),
                'employee_id': resource.employee_id.id,
                'employee_model': 'hr.employee' if self.env.user.has_group('hr.group_hr_user') else 'hr.employee.public',
            }
            for resource in resources
        }

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'resource_id':
            return dict(
                self._gantt_progress_bar_resource_id(res_ids, start, stop),
                warning=_("As there is no running contract during this period, this resource is not expected to work a shift. Planned hours:")
            )
        raise NotImplementedError(_("This Progress Bar is not implemented."))

    @api.model
    def gantt_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        if not self.user_has_groups("base.group_user"):
            return {field: {} for field in fields}

        start_utc, stop_utc = string_to_datetime(date_start_str), string_to_datetime(date_stop_str)

        progress_bars = {}
        for field in fields:
            progress_bars[field] = self._gantt_progress_bar(field, res_ids[field], start_utc, stop_utc)

        return progress_bars

    def _prepare_shift_vals(self):
        """ Generate shift vals"""
        self.ensure_one()
        return {
            'resource_id': False,
            'end_datetime': self.end_datetime,
            'role_id': self.role_id.id,
            'company_id': self.company_id.id,
            'allocated_percentage': self.allocated_percentage,
            'name': self.name,
            'recurrency_id': self.recurrency_id.id,
            'repeat': self.repeat,
            'repeat_interval': self.repeat_interval,
            'repeat_unit': self.repeat_unit,
            'repeat_type': self.repeat_type,
            'repeat_until': self.repeat_until,
            'repeat_number': self.repeat_number,
            'template_id': self.template_id.id,
        }

class PlanningRole(models.Model):
    _name = 'planning.role'
    _description = "Planning Role"
    _order = 'sequence'
    _rec_name = 'name'

    def _get_default_color(self):
        return randint(1, 11)

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer("Color", default=_get_default_color)
    resource_ids = fields.Many2many('resource.resource', 'resource_resource_planning_role_rel',
                                    'planning_role_id', 'resource_resource_id', 'Resources')
    sequence = fields.Integer()
    slot_properties_definition = fields.PropertiesDefinition('Planning Slot Properties')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _('%s (copy)', self.name)
        return super().copy(default=default)


class PlanningPlanning(models.Model):
    _name = 'planning.planning'
    _description = 'Schedule'

    @api.model
    def _default_access_token(self):
        return str(uuid.uuid4())

    start_datetime = fields.Datetime("Start Date", required=True)
    end_datetime = fields.Datetime("Stop Date", required=True)
    include_unassigned = fields.Boolean("Includes Open Shifts", default=True)
    access_token = fields.Char("Security Token", default=_default_access_token, required=True, copy=False, readonly=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company,
        help="Company linked to the material resource. Leave empty for the resource to be available in every company.")
    date_start = fields.Date('Date Start', compute='_compute_dates')
    date_end = fields.Date('Date End', compute='_compute_dates')
    allow_self_unassign = fields.Boolean('Let Employee Unassign Themselves', related='company_id.planning_allow_self_unassign')
    self_unassign_days_before = fields.Integer("Days before shift for unassignment", related="company_id.planning_self_unassign_days_before", help="Deadline in days for shift unassignment")

    @api.depends('start_datetime', 'end_datetime')
    @api.depends_context('uid')
    def _compute_dates(self):
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        for planning in self:
            planning.date_start = pytz.utc.localize(planning.start_datetime).astimezone(tz).replace(tzinfo=None)
            planning.date_end = pytz.utc.localize(planning.end_datetime).astimezone(tz).replace(tzinfo=None)

    def _compute_display_name(self):
        """ This override is need to have a human readable string in the email light layout header (`message.record_name`) """
        self.display_name = _('Planning')

    # ----------------------------------------------------
    # Business Methods
    # ----------------------------------------------------

    def _is_slot_in_planning(self, slot_sudo):
        return (
            self
            and slot_sudo.start_datetime > self.start_datetime
            and slot_sudo.end_datetime < self.end_datetime
            and slot_sudo.state == "published"
        )

    def _send_planning(self, slots, message=None, employees=False):
        email_from = self.env.user.email or self.env.user.company_id.email or ''
        # extract planning URLs
        employee_url_map = employees.sudo()._planning_get_url(self)

        # send planning email template with custom domain per employee
        template = self.env.ref('planning.email_template_planning_planning', raise_if_not_found=False)
        template_context = {
            'slot_unassigned': self.include_unassigned,
            'message': message,
        }
        if template:
            # /!\ For security reason, we only given the public employee to render mail template
            for employee in self.env['hr.employee.public'].browse(employees.ids):
                if employee.work_email:
                    template_context['employee'] = employee
                    template_context['start_datetime'] = self.date_start
                    template_context['end_datetime'] = self.date_end
                    template_context['planning_url'] = employee_url_map[employee.id]
                    template_context['assigned_new_shift'] = bool(slots.filtered(lambda slot: slot.employee_id.id == employee.id))
                    template.with_context(**template_context).send_mail(self.id, email_values={'email_to': employee.work_email, 'email_from': email_from}, email_layout_xmlid='mail.mail_notification_light')
        # mark as sent
        slots.write({
            'state': 'published',
            'publication_warning': False
        })
        return True
