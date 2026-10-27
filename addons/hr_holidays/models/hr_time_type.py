# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)

import logging
import operator as py_operator
from collections import defaultdict
from datetime import date, datetime, time, UTC

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.tools import format_date
from odoo.tools.translate import _
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)

PY_OPERATORS = {
    '>': py_operator.gt,
    '<': py_operator.lt,
    '>=': py_operator.ge,
    '<=': py_operator.le,
    '=': py_operator.eq,
    '!=': py_operator.ne,
    'in': lambda elem, container: elem in container,
}


class HrTimeType(models.Model):
    _inherit = 'hr.time.type'

    @api.model
    def _model_sorting_key(self, time_type):
        """Return the sort key of the types in :meth:`_search` (``sequence``)."""
        return time_type.sequence

    create_calendar_meeting = fields.Boolean(
        string="Display Time Off in Calendar",
        default=True,
        tracking=True,
        help="If this field is checked, every leave request of this type will have a corresponding entry in the calendar application. There will be no entry if this stays unchecked.",
    )
    color = fields.Integer(string='Color', help="The color selected here will be used in every screen with the time type.")
    hide_on_dashboard = fields.Boolean(default=False, string="Hide On Dashboard", tracking=True, help="Non-visible allocations can still be selected when taking a leave, but will simply not be displayed on the leave dashboard.")

    # employee specific computed data
    max_leaves = fields.Float(compute='_compute_leaves', string='Maximum Allowed', search='_search_max_leaves',
        help='This value is given by the sum of all time off requests with a positive value.')
    leaves_taken = fields.Float(
        compute='_compute_leaves', string='Time off Already Taken',
        help='This value is given by the sum of all time off requests with a negative value.')
    virtual_remaining_leaves = fields.Float(
        compute='_compute_leaves', search='_search_virtual_remaining_leaves', string='Virtual Remaining Time Off',
        help='Maximum Time Off Allowed - Time Off Already Taken - Time Off Waiting Approval')

    allocation_count = fields.Integer(
        compute='_compute_allocation_count', string='Allocations')
    group_days_leave = fields.Float(
        compute='_compute_group_days_leave', string='Group Time Off')
    is_used = fields.Boolean(compute="_compute_is_used")
    country_id = fields.Many2one('res.country', string='Country',
                                 default=lambda self: self.env.company.country_id,
                                 tracking=True,
                                 domain=lambda self: [('id', 'in', self.env.companies.country_id.ids)])
    country_code = fields.Char(related='country_id.code', depends=['country_id'], readonly=True)
    leave_validation_type = fields.Selection([
        ('no_validation', 'None'),
        ('hr', 'By HR Responsible'),
        ('manager', "By Time Off Approver"),
        ('both', "By HR Responsible and Time Off Approver")], default='hr', string='Time Off Validation', tracking=True)
    requires_allocation = fields.Boolean(default=True, required=True, string='Requires Allocation', tracking=True)
    employee_requests = fields.Boolean(default=False, required=True, string="Allow Employee Requests",
        tracking=True,
        help="""Extra Days Requests Allowed: User can request an allocation for himself.\n
        Not Allowed: User cannot request an allocation.""")
    allocation_validation_type = fields.Selection([
        ('no_validation', 'None'),
        ('hr', 'By HR Responsible'),
        ('manager', "By Time Off Approver"),
        ('both', "By HR Responsible and Time Off Approver")], default='hr', string='Approval',
        tracking=True,
        help="""Select the level of approval needed in case of request by employee
            #     - No validation needed: The employee's request is automatically approved.
            #     - Approved by Time Off Officer: The employee's request need to be manually approved
            #       by the Time Off Officer, Employee's Approver or both.""")

    has_valid_allocation = fields.Boolean(compute='_compute_valid', search='_search_valid', help='This indicates if it is still possible to use this type of leave')
    request_unit = fields.Selection([
        ('day', 'Full Day'),
        ('half_day', 'Half-Day'),
        ('hour', 'Custom Hours')], default='day', string='Duration Type', required=True,
        tracking=True,
        help="""Define the minimum time off duration in which an employee can take when requesting a leave""")
    unit_of_measure = fields.Selection([('hour', 'Hours'), ('day', 'Days')], default="hour", string="Unit", required=True,
                                       tracking=True,
                                       help="Define if the time type will be allocated/accrued in hours or days")
    unpaid = fields.Boolean('Is Unpaid', default=False, tracking=True)
    include_public_holidays_in_duration = fields.Boolean('Ignore Public Holidays', default=False, tracking=True, help="Public holidays should be counted in the leave duration when applying for leaves")
    leave_notif_subtype_id = fields.Many2one('mail.message.subtype', string='Time Off Notification Subtype', tracking=True, default=lambda self: self.env.ref('hr_holidays.mt_leave', raise_if_not_found=False))
    allocation_notif_subtype_id = fields.Many2one('mail.message.subtype', string='Allocation Notification Subtype', tracking=True, default=lambda self: self.env.ref('hr_holidays.mt_leave_allocation', raise_if_not_found=False))
    support_document = fields.Boolean(string='Supporting Document Expected', tracking=True, help="When enabled, employees will see a notice that this leave type requires a supporting document.")
    allow_request_on_top = fields.Boolean(string='Allow Request on Top', default=False,
        tracking=True,
        help="If checked, users can request another leave on top of the ones of this type.")
    elligible_for_accrual_rate = fields.Boolean(string='Eligible for Accrual Rate', compute="_compute_eligible_for_accrual_rate", store=True, readonly=False,
        tracking=True,
        help="If checked, this time type will be taken into account for accruals computation.")
    count_days_as = fields.Selection([
        ('working', 'Working Days'),
        ('calendar', 'Calendar Days'),
        ], string='Count Days as', default='working', tracking=True,
        help="If you take a leave on the whole week, worked days will result in a various number based on the working hours of the employee, calendar days will result in 7 in every case.")
    # negative time off
    allows_negative = fields.Boolean(string='Allow Negative',
        tracking=True,
        help="If checked, users request can exceed the allocated days and balance can go in negative.")
    max_allowed_negative = fields.Integer(string="Maximum Excess Amount",
        tracking=True,
        help="Define the maximum level of negative days this kind of time off can reach. Value must be at least 1.")

    _check_negative = models.Constraint(
        'CHECK(NOT allows_negative OR max_allowed_negative > 0)',
        'The maximum excess amount should be greater than 0. If you want to set 0, disable the negative cap instead.'
    )
    time_off_selectable = fields.Boolean(string="Selectable in Time Off", default=True, tracking=True)

    @api.model
    def _search_valid(self, operator, value):
        """Search ``has_valid_allocation``: types with a validated allocation for an employee.

        The employee is the context's ``default_employee_id``, ``employee_id`` or the user's
        employee; the period is ``default_date_from``/``default_date_to`` (with ``tz``) from the
        context, or the current year.
        """
        if operator not in ('in', 'not in'):
            return NotImplemented

        if {'default_date_from', 'default_date_to', 'tz'} <= set(self.env.context):
            default_date_from_dt = fields.Datetime.to_datetime(self.env.context.get('default_date_from'))
            default_date_to_dt = fields.Datetime.to_datetime(self.env.context.get('default_date_to'))

            # Cast: Datetime -> Date using user's tz
            date_from = fields.Date.context_today(self, default_date_from_dt)
            date_to = fields.Date.context_today(self, default_date_to_dt)

        else:
            current_year = fields.Date.context_today(self).year
            date_from = date(current_year, 1, 1)
            date_to = date(current_year, 12, 31)

        employee_id = self.env.context.get('default_employee_id', self.env.context.get('employee_id')) or self.env.user.employee_id.id

        time_types = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', employee_id),
            ('state', '=', 'validate'),
            ('date_from', '<=', date_to),
            '|',
            ('date_to', '>=', date_from),
            ('date_to', '=', False),
        ]).time_type_id

        return [('id', operator, time_types.ids)]

    @api.constrains('allow_request_on_top')
    def _check_allow_request_on_top(self):
        """Forbid requests on top of absences."""
        for leave in self:
            if leave.count_as == "absence" and leave.allow_request_on_top:
                raise ValidationError(self.env._("You cannot allow requests on top of leaves of type 'Absence'."))

    @api.constrains('elligible_for_accrual_rate')
    def _check_elligible_for_accrual_rate(self):
        """Working time types always count for the accruals."""
        for leave in self:
            if leave.count_as == "working_time" and not leave.elligible_for_accrual_rate:
                raise ValidationError(self.env._("leaves of type 'Worked Time' should be always eligible for accrual rate."))

    @api.constrains('include_public_holidays_in_duration')
    def _check_overlapping_public_holidays(self):
        """Forbid changing whether public holidays count when this year's requests overlap one."""
        # checking for the current user's company too
        public_holidays = self.env['resource.calendar.leaves'].search([
            ('resource_id', '=', False),
            ('company_id', '=', self.env.company.id),
        ])

        # Define the date range for the current year
        min_datetime = fields.Datetime.to_string(datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))
        max_datetime = fields.Datetime.to_string(datetime.now().replace(month=12, day=31, hour=23, minute=59, second=59))

        leaves = self.env['hr.leave'].search([
            ('time_type_id', 'in', self.ids),
            ('date_from', '>=', min_datetime),
            ('date_from', '<=', max_datetime),
            ('state', 'in', ('validate', 'validate1', 'confirm')),
        ])

        for leave in leaves:
            leave_from_date = leave.date_from.date()
            leave_to_date = leave.date_to.date()

            for public_holiday in public_holidays:
                public_holiday_from_date = public_holiday.date_from.date()
                public_holiday_to_date = public_holiday.date_to.date()

                if leave_from_date <= public_holiday_to_date and leave_to_date >= public_holiday_from_date:
                    raise ValidationError(self.env._("You cannot modify the 'Public Holiday Included' setting since one or more leaves for that \
time type are overlapping with public holidays, meaning that the balance of those employees would be affected by this change."))

    @api.constrains('count_days_as')
    def _check_leaves_for_count_days_as(self):
        """Forbid changing ``count_days_as`` once requests of the type exist."""
        leave_count = self.env['hr.leave'].search_count([
            ('time_type_id', 'in', self.ids),
            ('state', 'in', ('validate', 'validate1', 'confirm')),
        ], limit=1)
        if leave_count:
            raise ValidationError(self.env._("You cannot modify the 'Duration Count' setting because one or more leaves have already \
been taken for this time off type. Changing it now would affect existing employee balances."))

    def get_time_types_with_valid_allocations(self, date_from, date_to, employee_id):
        """Return the types of ``self`` the employee can request time off of during a period.

        Types without allocation always; types requiring an allocation when a validated one
        covers the whole period and is an accrual or has a positive balance (within the negative
        cap).

        :param date_from: first day
        :param date_to: last day
        :param int employee_id: employee id
        :rtype: hr.time.type
        """
        allocation_by_time_type = dict(self.env['hr.leave.allocation']._read_group(
            domain=Domain([
                ('time_type_id', 'in', self.filtered(lambda time_type: time_type.requires_allocation).ids),
                ('employee_id', '=', employee_id),
                ('state', '=', 'validate'),
                ('date_from', '<=', date_from),
                '|',
                    ('date_to', '>=', date_to),
                    ('date_to', '=', False),
            ]),
            groupby=['time_type_id'],
            aggregates=['id:recordset'],
        ))
        valid_types = self.env['hr.time.type']
        for time_type in self:
            if time_type.requires_allocation:
                allocations = allocation_by_time_type.get(time_type, self.env['hr.leave.allocation'])
                allowed_excess = time_type.max_allowed_negative if time_type.allows_negative else 0
                allocations = allocations.filtered(lambda alloc:
                    alloc.accrual_plan_id
                    or (alloc.max_leaves > 0 and alloc.virtual_remaining_leaves > -allowed_excess)
                )
                if allocations:
                    valid_types += time_type
            else:
                valid_types += time_type
        return valid_types

    @api.depends('requires_allocation', 'max_leaves', 'virtual_remaining_leaves')
    def _compute_valid(self):
        self.has_valid_allocation = False
        date_from = self.env.context.get('default_date_from', self.env.context.get('date_from', fields.Datetime.today()))
        date_to = self.env.context.get('default_date_to', self.env.context.get('date_to', fields.Datetime.today()))
        employee_id = self.env.context.get('default_employee_id', self.env.context.get('employee_id', self.env.user.employee_id.id))
        valid_types = self.get_time_types_with_valid_allocations(date_from, date_to, employee_id)
        valid_types.has_valid_allocation = True

    def _load_records_write(self, values):
        if 'requires_allocation' in values and self.requires_allocation == values['requires_allocation']:
            values.pop('requires_allocation')
        return super()._load_records_write(values)

    @api.constrains('requires_allocation')
    def check_allocation_requirement_edit_validity(self):
        """Forbid changing ``requires_allocation`` once requests of the type exist."""
        if not self.env.context.get('install_mode') and self.env['hr.leave'].search_count([('time_type_id', 'in', self.ids)], limit=1):
            raise UserError(_("The allocation requirement of a time type cannot be changed once leaves of that type have been taken. You should create a new time type instead."))

    def _search_max_leaves(self, operator, value):
        op = PY_OPERATORS.get(operator)
        if not op:
            return NotImplemented
        if operator != 'in':
            value = float(value)
        employee = self.env['hr.employee']._get_contextual_employee()
        leaves = defaultdict(int)

        if employee:
            allocations = self.env['hr.leave.allocation'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate')
            ])
            for allocation in allocations:
                leaves[allocation.time_type_id.id] += allocation.number_of_days
        valid_leaves = [leaf for leaf, number in leaves.items() if op(number, value)]
        return [('id', 'in', valid_leaves)]

    def _search_virtual_remaining_leaves(self, operator, value):
        def is_valid(time_type):
            return not time_type.requires_allocation or op(time_type.virtual_remaining_leaves, value)
        op = PY_OPERATORS.get(operator)
        if not op:
            return NotImplemented
        if operator != 'in':
            value = float(value)
        time_types = self.env['hr.time.type'].search([])
        return [('id', 'in', time_types.filtered(is_valid).ids)]

    @api.depends_context('uid', 'employee_id', 'default_employee_id', 'leave_date_from', 'default_date_from')
    def _compute_leaves(self):
        employee = self.env['hr.employee']._get_contextual_employee()
        # This is a workaround to save the date value in context for next triggers
        # when context gets cleaned and 'default_' context keys gets removed
        target_date = self.env.context.get('leave_date_from') or self.env.context.get('default_date_from')
        data_days = self.get_allocation_data(employee, target_date)[employee]
        for time_type in self:
            result = [item for item in data_days if item[3] == time_type.id]
            time_type_tuple = result[0] if result else ('', {})
            time_type.max_leaves = time_type_tuple[1].get('max_leaves', 0)
            time_type.leaves_taken = time_type_tuple[1].get('leaves_taken', 0)
            time_type.virtual_remaining_leaves = time_type_tuple[1].get('virtual_remaining_leaves', 0)

    def _compute_allocation_count(self):
        today = fields.Date.to_string(date.today())
        domain = [
            ('time_type_id', 'in', self.ids),
            ('date_from', '<=', today),
            '|', ('date_to', '=', False), ('date_to', '>=', today),
            ('state', 'in', ('confirm', 'validate')),
        ]

        grouped_res = self.env['hr.leave.allocation']._read_group(
            domain,
            ['time_type_id'],
            ['__count'],
        )
        grouped_dict = {time_type.id: count for time_type, count in grouped_res}
        for allocation in self:
            allocation.allocation_count = grouped_dict.get(allocation.id, 0)

    def _compute_group_days_leave(self):
        min_datetime = fields.Datetime.to_string(datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0))
        max_datetime = fields.Datetime.to_string(datetime.now().replace(month=12, day=31, hour=23, minute=59, second=59))
        domain = [
            ('time_type_id', 'in', self.ids),
            ('date_from', '>=', min_datetime),
            ('date_from', '<=', max_datetime),
            ('state', 'in', ('validate', 'validate1', 'confirm')),
        ]
        grouped_res = self.env['hr.leave']._read_group(
            domain,
            ['time_type_id'],
            ['__count'],
        )
        grouped_dict = {time_type.id: count for time_type, count in grouped_res}
        for allocation in self:
            allocation.group_days_leave = grouped_dict.get(allocation.id, 0)

    def _compute_is_used(self):
        leaves_count = self._leaves_count_by_time_type_id()
        allocations_count = self._allocations_count_by_time_type_id()
        for time_type in self:
            time_type.is_used = leaves_count.get(time_type.id, 0) or allocations_count.get(time_type.id, 0)

    def _leaves_count_by_time_type_id(self):
        leave_domain = [
            ('time_type_id', 'in', self.ids),
        ]
        leaves_count = self.env['hr.leave']._read_group(
            leave_domain,
            ['time_type_id'],
            ['__count'],
        )
        return {time_type.id: count for time_type, count in leaves_count}

    def _allocations_count_by_time_type_id(self):
        allocation_domain = [
            ('time_type_id', 'in', self.ids),
        ]
        allocations_count = self.env['hr.leave.allocation']._read_group(
            allocation_domain,
            ['time_type_id'],
            ['__count'],
        )
        return {time_type.id: count for time_type, count in allocations_count}

    def requested_display_name(self):
        return self.env.context.get('time_type_display_name', True) and self.env.context.get('employee_id')

    @api.depends('requires_allocation', 'virtual_remaining_leaves', 'max_leaves', 'unit_of_measure', 'country_id')
    @api.depends_context('time_type_display_name', 'employee_id', 'company')
    def _compute_display_name(self):
        display_country_name = not bool(self.env.companies and len(self.env.companies.mapped('country_id')) == 1)
        for record in self:
            if not record.requested_display_name():
                # leave counts is based on employee_id, would be inaccurate if not based on correct employee
                if display_country_name:
                    record.display_name = f"{record.name} ({record.country_id.name or self.env._("Generic")})"
                else:
                    record.display_name = record.name
                continue
            name = record.name
            if record.time_off_selectable and record.requires_allocation:
                remaining_time = float_round(record.virtual_remaining_leaves, precision_digits=2) or 0.0
                maximum = float_round(record.max_leaves, precision_digits=2) or 0.0

                is_popover = self.env.context.get("is_popover", False)
                is_hour = record.unit_of_measure == "hour"
                if is_popover and is_hour:
                    name = self.env._("%(name)s (%(time)g hours left)", name=record.name, time=remaining_time)
                elif is_popover:
                    name = self.env._("%(name)s (%(time)g days left)", name=record.name, time=remaining_time)
                elif is_hour:
                    name = self.env._("%(name)s (%(time)g remaining out of %(maximum)g hours)", name=record.name, time=remaining_time, maximum=maximum)
                else:
                    name = self.env._("%(name)s (%(time)g remaining out of %(maximum)g days)", name=record.name, time=remaining_time, maximum=maximum)
            if display_country_name:
                record.display_name = f"{name} ({record.country_id.name or self.env._("Generic")})"
            else:
                record.display_name = name
        return None

    @api.depends('count_as')
    def _compute_eligible_for_accrual_rate(self):
        for time_type in self:
            time_type.elligible_for_accrual_rate = time_type.count_as != 'absence'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        """Sort the types with :meth:`_model_sorting_key` when an employee is in the context.

        Only when the default order is requested; the sort is done in Python before offset and
        limit are applied.
        """
        employee = self.env['hr.employee']._get_contextual_employee()
        if order == self._order and employee:
            # retrieve all leaves, sort them, then apply offset and limit
            leaves = self.browse(super()._search(domain, **kwargs))
            leaves = leaves.sorted(key=self._model_sorting_key)
            leaves = leaves[offset:(offset + limit) if limit else None]
            return leaves._as_query()
        return super()._search(domain, offset, limit, order, **kwargs)

    def action_see_days_allocated(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_allocation_action_all")
        action['domain'] = [
            ('time_type_id', 'in', self.ids),
        ]
        action['context'] = {
            'employee_id': False,
            'default_time_type_id': self.ids[0],
            'search_default_approved_state': 1,
            'search_default_year': 1,
        }
        return action

    def action_see_group_leaves(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_holidays.hr_leave_action_action_approve_department")
        action['domain'] = [
            ('time_type_id', '=', self.ids[0]),
        ]
        action['context'] = {
            'default_time_type_id': self.ids[0],
        }
        return action

    # ------------------------------------------------------------
    # Leave - Allocation link methods
    # ------------------------------------------------------------

    @api.model
    def get_allocation_data_request(self, target_date=None, hidden_allocations=True, same_year_only=False):
        """Return the balances of the contextual employee for every type.

        With the context key ``from_dashboard``, types without allocated time are left out.

        :param target_date: date of the balances, today by default
        :param bool hidden_allocations: include the types hidden on the dashboard
        :param bool same_year_only: see :meth:`get_allocation_data`
        :return: list of tuples, see :meth:`get_allocation_data`
        :rtype: list
        """
        employee = self.env["hr.employee"]._get_contextual_employee()
        if not employee:
            return defaultdict(list)
        domain = []
        if not hidden_allocations:
            domain.append(('hide_on_dashboard', '=', False))
        time_types = self.search(domain, order='id')
        employee_time_type_infos = time_types.get_allocation_data(employee, target_date, same_year_only=same_year_only)[
            employee
        ]
        # We only need to filter allocation_data for the dashboard
        if not self.env.context.get("from_dashboard", False):
            return employee_time_type_infos
        filtered_employee_time_type_infos = [
            time_type_info
            for time_type_info in employee_time_type_infos
            if time_type_info[1]["max_leaves"]
        ]
        return filtered_employee_time_type_infos

    def get_allocation_data(self, employees, target_date=None, same_year_only=False):
        """Return the balance of the employees for each type of ``self`` on a date.

        Sums the data of
        :meth:`~odoo.addons.hr_holidays.models.hr_employee.HrEmployee._get_consumed_leaves` over
        the allocations valid on ``target_date``. Amounts are in the ``unit_of_measure`` of
        the type, rounded to 2 digits. Requests listed in the context key ``ignored_leave_ids``
        are ignored.

        :param employees: ``hr.employee`` records
        :param target_date: ``date``, ``datetime`` or ISO string, today by default
        :param bool same_year_only: only count the allocations starting in the year of
            ``target_date`` and the requests starting that year
        :return: ``{employee: [(type name, data, requires_allocation, type id), ...]}``, where
            ``data`` holds ``max_leaves``, ``leaves_taken`` and ``remaining_leaves`` (approved),
            ``virtual_leaves_taken`` and ``virtual_remaining_leaves`` (also to approve),
            ``leaves_requested``, ``leaves_approved``, ``accrual_bonus``,
            ``closest_allocation_expire`` (formatted date), ``closest_allocation_remaining``,
            ``closest_allocation_duration``, ``holds_changes``, ``total_virtual_excess``,
            ``virtual_excess_data``, ``exceeding_duration`` and type information
            (``request_unit``, ``unit_of_measure``, ``allows_negative``,
            ``max_allowed_negative``, ``color``, ...)
        :rtype: dict
        """
        allocation_data = defaultdict(list)
        if target_date and isinstance(target_date, str):
            target_date = datetime.fromisoformat(target_date).date()
        elif target_date and isinstance(target_date, datetime):
            target_date = target_date.date()
        elif not target_date:
            target_date = fields.Date.context_today(self)

        allocations_leaves_consumed, extra_data = employees.with_context(
            ignored_leave_ids=self.env.context.get('ignored_leave_ids')
        )._get_consumed_leaves(self, target_date, same_year_only=same_year_only)

        today = fields.Date.context_today(self)
        for employee in employees:
            for time_type in self:
                lt_info = (
                    time_type.name,
                    {
                        'remaining_leaves': 0,
                        'virtual_remaining_leaves': 0,
                        'max_leaves': 0,
                        'accrual_bonus': 0,
                        'leaves_taken': 0,
                        'virtual_leaves_taken': 0,
                        'leaves_requested': 0,
                        'leaves_approved': 0,
                        'closest_allocation_remaining': 0,
                        'closest_allocation_expire': False,
                        'holds_changes': False,
                        'total_virtual_excess': 0,
                        'virtual_excess_data': {},
                        'exceeding_duration': extra_data[employee][time_type]['exceeding_duration'],
                        'request_unit': time_type.request_unit,
                        'unit_of_measure': time_type.unit_of_measure,
                        'allows_negative': time_type.allows_negative,
                        'max_allowed_negative': time_type.max_allowed_negative,
                        'employee_company': employee.company_id.id,
                        'employee_country': employee.company_id.country_id.id,
                        'color': time_type.color,
                    },
                    time_type.requires_allocation,
                    time_type.id)
                for excess_date, excess_days in extra_data[employee][time_type]['excess_days'].items():
                    amount = excess_days['amount']
                    lt_info[1]['virtual_excess_data'].update({
                        excess_date.strftime('%Y-%m-%d'): excess_days
                    })
                    lt_info[1]['total_virtual_excess'] += amount
                    if not time_type.allows_negative:
                        continue
                    lt_info[1]['virtual_leaves_taken'] += amount
                    lt_info[1]['virtual_remaining_leaves'] -= amount
                    if excess_days['is_virtual']:
                        lt_info[1]['leaves_requested'] += amount
                    else:
                        lt_info[1]['leaves_approved'] += amount
                        lt_info[1]['leaves_taken'] += amount
                        lt_info[1]['remaining_leaves'] -= amount
                allocations_now = self.env['hr.leave.allocation']
                allocations_date = self.env['hr.leave.allocation']
                allocations_with_remaining_leaves = self.env['hr.leave.allocation']
                primary_unit = 'hours' if time_type.unit_of_measure == 'hour' else 'days'
                for allocation, data in allocations_leaves_consumed[employee][time_type].items():
                    # We only need the allocation that are valid at the given date
                    if allocation:
                        if allocation.date_from <= today and (not allocation.date_to or allocation.date_to >= today):
                            # we get each allocation available now to indicate visually if
                            # the future evaluation holds changes compared to now
                            allocations_now |= allocation
                        if allocation.date_from <= target_date and (not allocation.date_to or allocation.date_to >= target_date):
                            # we get each allocation available now to indicate visually if
                            # the future evaluation holds changes compared to now
                            allocations_date |= allocation
                        if allocation.date_from > target_date:
                            continue
                        if allocation.date_to and allocation.date_to < target_date:
                            continue
                        if same_year_only and allocation.date_from.year != target_date.year:
                            continue
                    lt_info[1]['remaining_leaves'] += data[f'{primary_unit}_remaining_leaves']
                    lt_info[1]['virtual_remaining_leaves'] += data[f'{primary_unit}_virtual_remaining_leaves']
                    lt_info[1]['max_leaves'] += data[f'{primary_unit}_max_leaves']
                    lt_info[1]['accrual_bonus'] += data[f'{primary_unit}_accrual_bonus']
                    lt_info[1]['leaves_taken'] += data[f'{primary_unit}_leaves_taken']
                    lt_info[1]['virtual_leaves_taken'] += data[f'{primary_unit}_virtual_leaves_taken']
                    lt_info[1]['leaves_requested'] += data[f'{primary_unit}_virtual_leaves_taken'] - data[f'{primary_unit}_leaves_taken']
                    lt_info[1]['leaves_approved'] += data[f'{primary_unit}_leaves_taken']
                    if data[f'{primary_unit}_virtual_remaining_leaves'] > 0:
                        allocations_with_remaining_leaves |= allocation
                closest_expiration_date, closest_allocation_remaining = self._get_closest_expiring_leaves_date_and_count(
                                                                            allocations_with_remaining_leaves,
                                                                            allocations_leaves_consumed[employee][time_type],
                                                                            target_date,
                                                                            primary_unit,
                                                                        )
                if closest_expiration_date:
                    closest_allocation_expire = format_date(self.env, closest_expiration_date)
                    calendar = employee.resource_calendar_id
                    start_datetime = datetime.combine(target_date, time.min, tzinfo=UTC)
                    end_datetime = datetime.combine(closest_expiration_date, time.max, tzinfo=UTC)
                    closest_allocation_dict = {}
                    if employee.sudo()._is_flexible(target_date):
                        closest_allocation_dict['hours'] = float_round((end_datetime - start_datetime).total_seconds() / 3600, precision_rounding=0.001)
                        closest_allocation_dict['days'] = (end_datetime - start_datetime).days + 1
                    else:
                        # closest_allocation_duration corresponds to the time remaining before the allocation expires
                        resources_per_tz = employee._get_resources_per_tz(start_datetime)
                        calendar_attendance = calendar._work_intervals_batch(start_datetime, end_datetime, resources_per_tz=resources_per_tz)
                        closest_allocation_dict = calendar._get_attendance_intervals_days_data(calendar_attendance[employee.resource_id.id])
                    if time_type.unit_of_measure in ['hour']:
                        closest_allocation_duration = closest_allocation_dict['hours']
                    else:
                        closest_allocation_duration = closest_allocation_dict['days']
                else:
                    closest_allocation_expire = False
                    closest_allocation_duration = False
                # the allocations are assumed to be different from today's allocations if there is any
                # accrual days granted or if there is any difference between allocations now and on the selected date
                holds_changes = (lt_info[1]['accrual_bonus'] > 0
                    or bool(allocations_date - allocations_now)
                    or bool(allocations_now - allocations_date))\
                    and target_date != today
                lt_info[1].update({
                    'closest_allocation_remaining': closest_allocation_remaining,
                    'closest_allocation_expire': closest_allocation_expire,
                    'closest_allocation_duration': closest_allocation_duration,
                    'holds_changes': holds_changes,
                })
                # format all float fields
                for key, value in lt_info[1].items():
                    if isinstance(value, float):
                        lt_info[1][key] = round(value, 2)
                allocation_data[employee].append(lt_info)
        return allocation_data

    def _get_closest_expiring_leaves_date_and_count(self, allocations, remaining_leaves, target_date, primary_unit):
        """Return the next date some remaining time expires, and how much.

        Time expires at the end of an allocation, on a carry-over date when unused time is lost
        or limited, and at the end of the validity of carried over time.

        :param allocations: ``hr.leave.allocation`` with remaining time
        :param dict remaining_leaves: ``{allocation: data}`` of
            :meth:`~odoo.addons.hr_holidays.models.hr_employee.HrEmployee._get_consumed_leaves`
        :param datetime.date target_date: reference date
        :param str primary_unit: ``'days'`` or ``'hours'``
        :return: ``(date, amount)``, ``(None, 0)`` when nothing expires
        :rtype: tuple
        """
        # Get the expiration date and carryover date of all allocations and compute the closest expiration date
        expiration_dates_per_allocation = {}
        expiration_dates = list()
        carried_over_days_expiration_data = self._get_carried_over_days_expiration_data(allocations, target_date)
        for allocation in allocations:
            expiration_date = allocation.date_to

            current_lvl, _ = allocation.sudo()._get_current_accrual_plan_level_idx(target_date)
            carryover_date = None
            if current_lvl and (current_lvl.action_with_unused_accruals == 'lost' or current_lvl.carryover_options == 'limited'):
                carryover_date = allocation.sudo()._get_next_carryover_date(target_date, date_from_included=False)

            carried_over_days_expiration_date = carried_over_days_expiration_data[allocation]['expiration_date']

            expiration_dates.extend([expiration_date, carryover_date, carried_over_days_expiration_date])
            expiration_dates_per_allocation[allocation] = {
                'expiration_date': expiration_date,
                'carryover_date': carryover_date,
                'carried_over_days_expiration_date': carried_over_days_expiration_date,
            }

        expiration_dates = list(filter(bool, expiration_dates))
        expiration_dates.sort()
        # Compute the number of expiring leaves
        for closest_expiration_date in expiration_dates:
            expiring_leaves_count = 0
            for allocation in allocations:
                expiration_date = expiration_dates_per_allocation[allocation]['expiration_date']
                carryover_date = expiration_dates_per_allocation[allocation]['carryover_date']
                carried_over_days_expiration_date = expiration_dates_per_allocation[allocation]['carried_over_days_expiration_date']

                if expiration_date and expiration_date == closest_expiration_date:
                    expiring_leaves_count += remaining_leaves[allocation][f'{primary_unit}_virtual_remaining_leaves']
                elif carryover_date and carryover_date == closest_expiration_date:
                    current_lvl = allocation.sudo()._get_current_accrual_plan_level_idx(target_date)[0]
                    max_carried_over_duration = allocation._convert_from_type_request_unit(
                        current_lvl.max_carriedover_duration, allocation.time_type_id.unit_of_measure)
                    expiring_leaves_count += max(0, remaining_leaves[allocation][f'{primary_unit}_virtual_remaining_leaves'] - max_carried_over_duration)
                elif carried_over_days_expiration_date and carried_over_days_expiration_date == closest_expiration_date:
                    expiring_leaves_count += carried_over_days_expiration_data[allocation]['no_expiring_days']

            if expiring_leaves_count != 0:
                return closest_expiration_date, expiring_leaves_count

        # No leaves will expire
        return None, 0

    def _get_carried_over_days_expiration_data(self, allocations, target_date):
        """Return when the time carried over by accrual allocations expires, and how much.

        :return: ``{allocation: {'expiration_date': date or None, 'no_expiring_days': float}}``
        :rtype: dict
        """
        updated_alloc_data = allocations.sudo()._process_accrual_plans(target_date)
        carried_over_days_expiration_data = {}
        for allocation in allocations:
            if not allocation.accrual_plan_id:
                carried_over_days_expiration_data[allocation] = {
                    'expiration_date': None,
                    'no_expiring_days': 0,
                }
                continue
            allocation_data = updated_alloc_data[allocation]
            prev_carryover_allocated_duration = allocation._convert_from_type_request_unit(
                allocation_data['previous_carryover_allocated_duration'], allocation.time_type_id.unit_of_measure, allocation_data)
            leaves_taken = allocation_data['leaves_taken']
            carried_over_days_expiration_data[allocation] = {
                'expiration_date': allocation_data['carried_over_days_expiration_date'],
                'no_expiring_days':
                    max(0, prev_carryover_allocated_duration - leaves_taken),
            }
        return carried_over_days_expiration_data
