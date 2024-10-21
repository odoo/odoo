import logging
import pytz

from collections import namedtuple, defaultdict

from datetime import datetime, timedelta, time
from dateutil.relativedelta import relativedelta
from math import ceil
from pytz import timezone, UTC

from odoo.addons.base.models.ir_model import MODULE_UNINSTALL_FLAG

from odoo import api, Command, fields, models, tools
from odoo.addons.base.models.res_partner import _tz_get
from odoo.addons.resource.models.utils import float_to_time, HOURS_PER_DAY
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.float_utils import float_round, float_compare
from odoo.tools.misc import format_date
from odoo.tools.translate import _
from odoo.osv import expression

_logger = logging.getLogger(__name__)

# Used to agglomerate the attendances in order to find the hour_from and hour_to
# See _compute_date_from_to
DummyAttendance = namedtuple('DummyAttendance', 'hour_from, hour_to, dayofweek, day_period, week_type')

def get_employee_from_context(values, context, user_employee_id):
    employee_ids_list = [value[2] for value in values.get('employee_ids', []) if len(value) == 3 and value[0] == Command.SET]
    employee_ids = employee_ids_list[-1] if employee_ids_list else []
    employee_id_value = employee_ids[0] if employee_ids else False
    return employee_id_value or context.get('default_employee_id', context.get('employee_id', user_employee_id))

class HolidaysRequest(models.Model):
    """ Time Off Requests Access specifications

     - a regular employee / user
      - can see all leaves;
      - cannot see name field of leaves belonging to other user as it may contain
        private information that we don't want to share to other people than
        HR people;
      - can modify only its own not validated leaves (except writing on state to
        bypass approval);
      - can discuss on its leave requests;
      - can reset only its own leaves;
      - cannot validate any leaves;
     - an Officer
      - can see all leaves;
      - can validate "HR" single validation leaves from people if
       - he is the employee manager;
       - he is the department manager;
       - he is member of the same department;
       - target employee has no manager and no department manager;
      - can validate "Manager" single validation leaves from people if
       - he is the employee manager;
       - he is the department manager;
       - target employee has no manager and no department manager;
      - can first validate "Both" double validation leaves from people like "HR"
        single validation, moving the leaves to validate1 state;
      - cannot validate its own leaves;
      - can reset only its own leaves;
      - can refuse all leaves;
     - a Manager
      - can do everything he wants

    On top of that multicompany rules apply based on company defined on the
    leave request leave type.
    """
    _name = "hr.leave"
    _description = "Time Off"
    _order = "date_from desc"
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']
    _mail_post_access = 'read'

    @api.model
    def default_get(self, fields_list):
        defaults = super(HolidaysRequest, self).default_get(fields_list)
        defaults = self._default_get_request_dates(defaults)

        lt = self.env['hr.leave.type']
        if self.env.context.get('holiday_status_display_name', True) and 'holiday_status_id' in fields_list and not defaults.get('holiday_status_id'):
            lt = self.env['hr.leave.type'].search(['|', ('requires_allocation', '=', 'no'), ('has_valid_allocation', '=', True)], limit=1, order='sequence')
            if lt:
                defaults['holiday_status_id'] = lt.id
                defaults['request_unit_custom'] = False

        if 'request_date_from' in fields_list and 'request_date_from' not in defaults:
            defaults['request_date_from'] = fields.Date.today()
        if 'request_date_to' in fields_list and 'request_date_to' not in defaults:
            defaults['request_date_to'] = fields.Date.today()

        return defaults

    def _default_get_request_dates(self, values):
        # The UI views initialize date_{from,to} due to how calendar views work.
        # However it is request_date_{from,to} that should be used instead.
        # Instead of overwriting all the javascript methods to use
        # request_date_{from,to} instead of date_{from,to}, we just convert
        # date_{from,to} to request_date_{from,to} here.

        # Request dates are determined during an onchange scenario.
        # To ensure that the values are correct in the client context (UI),
        # the timezone must be applied (because no processing is carried out
        # when these dates are received on the frontend).
        # Note:
        # Without the application of the timezone, days based on UTC datetimes
        # will be returned (and will therefore not be correct for the client).
        client_tz = timezone(self._context.get('tz') or self.env.user.tz or 'UTC')
        if values.get('date_from'):
            if not values.get('request_date_from'):
                values['request_date_from'] = pytz.utc.localize(values['date_from']).astimezone(client_tz)
            del values['date_from']
        if values.get('date_to'):
            if not values.get('request_date_to'):
                values['request_date_to'] = pytz.utc.localize(values['date_to']).astimezone(client_tz)
            del values['date_to']
        return values

    # description
    name = fields.Char('Description', compute='_compute_description', inverse='_inverse_description', search='_search_description', compute_sudo=False, copy=False)
    private_name = fields.Char('Time Off Description', groups='hr_holidays.group_hr_holidays_user')
    state = fields.Selection([
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved'),
        ('cancel', 'Cancelled'),
        ], string='Status', store=True, tracking=True, copy=False, readonly=False, default='confirm',
        help="The status is set to 'To Submit', when a time off request is created." +
        "\nThe status is 'To Approve', when time off request is confirmed by user." +
        "\nThe status is 'Refused', when time off request is refused by manager." +
        "\nThe status is 'Approved', when time off request is approved by manager.")
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id', related_sudo=True, compute_sudo=True, store=True, readonly=True, index=True)
    manager_id = fields.Many2one('hr.employee', compute='_compute_from_employee_id', store=True, readonly=False)
    # leave type configuration
    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_from_employee_id',
        store=True, string="Time Off Type",
        required=True, readonly=False,
        domain="""[
            ('company_id', 'in', [employee_company_id, False]),
            '|',
                ('requires_allocation', '=', 'no'),
                ('has_valid_allocation', '=', True),
        ]""",
        tracking=True)
    color = fields.Integer("Color", related='holiday_status_id.color')
    validation_type = fields.Selection(string='Validation Type', related='holiday_status_id.leave_validation_type', readonly=False)
    # HR data

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', index=True, ondelete="restrict", required=True,
        tracking=True, domain=lambda self: self._get_employee_domain(), default=lambda self: self.env.user.employee_id)
    employee_company_id = fields.Many2one(related='employee_id.company_id', string="Employee Company", store=True)
    company_id = fields.Many2one('res.company', compute='_compute_company_id', store=True)
    active_employee = fields.Boolean(related='employee_id.active', string='Employee Active')
    tz_mismatch = fields.Boolean(compute='_compute_tz_mismatch')
    tz = fields.Selection(_tz_get, compute='_compute_tz')
    department_id = fields.Many2one(
        'hr.department', compute='_compute_department_id', store=True, string='Department', readonly=False)
    notes = fields.Text('Reasons', readonly=False)
    # duration
    resource_calendar_id = fields.Many2one('resource.calendar', compute='_compute_resource_calendar_id', store=True, readonly=False, copy=False)
    # These dates are computed based on request_date_{to,from} and should
    # therefore never be set directly.
    date_from = fields.Datetime(
        'Start Date', compute='_compute_date_from_to', store=True, index=True, tracking=True)
    date_to = fields.Datetime(
        'End Date', compute='_compute_date_from_to', store=True, tracking=True)
    number_of_days = fields.Float(
        'Duration (Days)', compute='_compute_duration', store=True, tracking=True,
        help='Number of days of the time off request. Used in the calculation.')
    number_of_hours = fields.Float(
        'Duration (Hours)', compute='_compute_duration', store=True, tracking=True,
        help='Number of hours of the time off request. Used in the calculation.')
    last_several_days = fields.Boolean("All day", compute="_compute_last_several_days")
    duration_display = fields.Char('Requested (Days/Hours)', compute='_compute_duration_display', store=True,
        help="Field allowing to see the leave request duration in days or hours depending on the leave_type_request_unit")    # details
    # details
    meeting_id = fields.Many2one('calendar.event', string='Meeting', copy=False)
    first_approver_id = fields.Many2one(
        'hr.employee', string='First Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the time off')
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approval', readonly=True, copy=False,
        help='This area is automatically filled by the user who validate the time off with second level (If time off type need second validation)')
    can_reset = fields.Boolean('Can reset', compute='_compute_can_reset')
    can_approve = fields.Boolean('Can Approve', compute='_compute_can_approve')
    can_cancel = fields.Boolean('Can Cancel', compute='_compute_can_cancel')

    attachment_ids = fields.One2many('ir.attachment', 'res_id', string="Attachments")
    # To display in form view
    supported_attachment_ids = fields.Many2many(
        'ir.attachment', string="Attach File", compute='_compute_supported_attachment_ids',
        inverse='_inverse_supported_attachment_ids')
    supported_attachment_ids_count = fields.Integer(compute='_compute_supported_attachment_ids')
    # UX fields
    leave_type_request_unit = fields.Selection(related='holiday_status_id.request_unit', readonly=True)
    leave_type_support_document = fields.Boolean(related="holiday_status_id.support_document")
    # Interface fields used when not using hour-based computation
    # These are the fields that should be used to manipulate the start- and
    # end-dates of the leave request. date_from and date_to are computed and
    # should therefore not be set directly.
    request_date_from = fields.Date('Request Start Date')
    request_date_to = fields.Date('Request End Date')
    # Interface fields used when using hour-based computation
    request_hour_from = fields.Float(string='Hour from')
    request_hour_to = fields.Float(string='Hour to')
    # used only when the leave is taken in half days
    request_date_from_period = fields.Selection([
        ('am', 'Morning'), ('pm', 'Afternoon')],
        string="Date Period Start", default='am')
    # request type
    request_unit_half = fields.Boolean('Half Day', compute='_compute_request_unit_half', store=True, readonly=False)
    request_unit_hours = fields.Boolean('Custom Hours', compute='_compute_request_unit_hours', store=True, readonly=False)
    # view
    is_hatched = fields.Boolean('Hatched', compute='_compute_is_hatched')
    is_striked = fields.Boolean('Striked', compute='_compute_is_hatched')
    has_mandatory_day = fields.Boolean(compute='_compute_has_mandatory_day')
    leave_type_increases_duration = fields.Boolean(compute='_compute_leave_type_increases_duration')

    _sql_constraints = [
        ('date_check2', "CHECK ((date_from <= date_to))", "The start date must be before or equal to the end date."),
        ('date_check3', "CHECK ((request_date_from <= request_date_to))", "The request start date must be before or equal to the request end date."),
        ('duration_check', "CHECK ( number_of_days >= 0 )", "If you want to change the number of days you should use the 'period' mode"),
    ]

    def _auto_init(self):
        res = super(HolidaysRequest, self)._auto_init()
        tools.create_index(self._cr, 'hr_leave_date_to_date_from_index',
                           self._table, ['date_to', 'date_from'])
        return res

    @api.onchange('request_hour_from', 'request_hour_to')
    def _onchange_hours(self):
        # avoid negative or after midnight
        self.request_hour_from = min(self.request_hour_from, 23.99)
        self.request_hour_from = max(self.request_hour_from, 0.0)
        self.request_hour_to = min(self.request_hour_to, 24)
        self.request_hour_to = max(self.request_hour_to, 0.0)

        # avoid wrong order
        self.request_hour_to = max(self.request_hour_to, self.request_hour_from)

    @api.depends_context('uid')
    def _compute_description(self):
        self.check_access('read')

        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')

        for leave in self:
            if is_officer or leave.user_id == self.env.user or leave.employee_id.leave_manager_id == self.env.user:
                leave.name = leave.sudo().private_name
            else:
                leave.name = '*****'

    def _inverse_description(self):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')

        for leave in self:
            if is_officer or leave.user_id == self.env.user or leave.employee_id.leave_manager_id == self.env.user:
                leave.sudo().private_name = leave.name

    def _search_description(self, operator, value):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        domain = [('private_name', operator, value)]

        if not is_officer:
            domain = expression.AND([domain, [('user_id', '=', self.env.user.id)]])
        query = self.sudo()._search(domain)
        return [('id', 'in', query)]


    @api.depends('employee_id')
    def _compute_resource_calendar_id(self):
        employees_by_dates = defaultdict(lambda: self.env['hr.employee'])
        for leave in self:
            if leave.employee_id and leave.request_date_from:
                employees_by_dates[leave.request_date_from] += leave.employee_id
        calendar_by_dates = {date_from: employees._get_calendars(date_from) for date_from, employees in employees_by_dates.items()}
        for leave in self:
            calendar = False
            if leave.employee_id and leave.request_date_from:
                calendar = calendar_by_dates[leave.request_date_from][leave.employee_id.id]
            leave.resource_calendar_id = calendar or self.env.company.resource_calendar_id

    @api.depends('request_date_from_period', 'request_hour_from', 'request_hour_to', 'request_date_from', 'request_date_to',
                 'request_unit_half', 'request_unit_hours', 'employee_id')
    def _compute_date_from_to(self):
        for holiday in self:
            if not holiday.request_date_from:
                holiday.date_from = False
            elif not holiday.request_unit_half and not holiday.request_unit_hours and not holiday.request_date_to:
                holiday.date_to = False
            else:
                if (holiday.request_unit_half or holiday.request_unit_hours) and holiday.request_date_to != holiday.request_date_from:
                    holiday.request_date_to = holiday.request_date_from


                day_period = {
                    'am': 'morning',
                    'pm': 'afternoon'
                }.get(holiday.request_date_from_period, None) if holiday.request_unit_half else None


                compensated_request_date_from = holiday.request_date_from
                compensated_request_date_to = holiday.request_date_to

                if holiday.request_unit_hours:
                    hour_from = holiday.request_hour_from
                    hour_to = holiday.request_hour_to
                else:
                    hour_from, hour_to = holiday._get_hour_from_to(holiday.request_date_from, holiday.request_date_to,
                        day_period=day_period)

                holiday.date_from = self._to_utc(compensated_request_date_from, hour_from, holiday.employee_id or holiday)
                holiday.date_to = self._to_utc(compensated_request_date_to, hour_to, holiday.employee_id or holiday)

    @api.depends('holiday_status_id', 'request_unit_hours')
    def _compute_request_unit_half(self):
        for holiday in self:
            if holiday.holiday_status_id or holiday.request_unit_hours:
                holiday.request_unit_half = False

    @api.depends('holiday_status_id', 'request_unit_half')
    def _compute_request_unit_hours(self):
        for holiday in self:
            if holiday.holiday_status_id or holiday.request_unit_half:
                holiday.request_unit_hours = False

    def _get_employee_domain(self):
        domain = [
            ('active', '=', True),
            ('company_id', 'in', self.env.companies.ids),
        ]
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            domain += [
                '|',
                ('user_id', '=', self.env.uid),
                ('leave_manager_id', '=', self.env.uid),
            ]
        return domain

    @api.depends('employee_id')
    def _compute_from_employee_id(self):
        for holiday in self:
            holiday.manager_id = holiday.employee_id.parent_id.id
            if holiday.holiday_status_id.requires_allocation == 'no':
                continue
            if not holiday.employee_id:
                holiday.holiday_status_id = False
            elif holiday.employee_id.user_id != self.env.user and holiday._origin.employee_id != holiday.employee_id:
                if holiday.employee_id and not holiday.holiday_status_id.with_context(employee_id=holiday.employee_id.id).has_valid_allocation:
                    holiday.holiday_status_id = False

    @api.depends('employee_id')
    def _compute_department_id(self):
        for holiday in self:
            holiday.department_id = holiday.employee_id.department_id

    @api.depends('date_from', 'date_to', 'holiday_status_id')
    def _compute_has_mandatory_day(self):
        date_from, date_to = min(self.mapped('date_from')), max(self.mapped('date_to'))
        if date_from and date_to:
            mandatory_days = self.employee_id._get_mandatory_days(
                date_from.date(),
                date_to.date())

            for leave in self:
                domain = [
                    ('start_date', '<=', leave.date_to.date()),
                    ('end_date', '>=', leave.date_from.date()),
                    '|',
                        ('resource_calendar_id', '=', False),
                        ('resource_calendar_id', '=', leave.resource_calendar_id.id),
                ]

                if leave.holiday_status_id.company_id:
                    domain += [('company_id', '=', leave.holiday_status_id.company_id.id)]
                leave.has_mandatory_day = leave.date_from and leave.date_to and mandatory_days.filtered_domain(domain)
        else:
            self.has_mandatory_day = False

    @api.depends('leave_type_request_unit', 'number_of_days')
    def _compute_leave_type_increases_duration(self):
        durations = self._get_durations(check_leave_type=False)
        for leave in self:
            days = durations[leave.id][0]
            leave.leave_type_increases_duration = leave.leave_type_request_unit == 'day' and days < leave.number_of_days

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        """
        This method is factored out into a separate method from
        _compute_duration so it can be hooked and called without necessarily
        modifying the fields and triggering more computes of fields that
        depend on number_of_hours or number_of_days.
        """
        result = {}
        employee_leaves = self.filtered('employee_id')
        employees_by_dates_calendar = defaultdict(lambda: self.env['hr.employee'])
        for leave in employee_leaves:
            if not leave.date_from or not leave.date_to:
                continue
            employees_by_dates_calendar[(leave.date_from, leave.date_to, leave.holiday_status_id.include_public_holidays_in_duration, resource_calendar or leave.resource_calendar_id)] += leave.employee_id
        # We force the company in the domain as we are more than likely in a compute_sudo
        domain = [('time_type', '=', 'leave'),
                  ('company_id', 'in', self.env.companies.ids + self.env.context.get('allowed_company_ids', [])),
                  # When searching for resource leave intervals, we exclude the one that
                  # is related to the leave we're currently trying to compute for.
                  '|', ('holiday_id', '=', False), ('holiday_id', 'not in', employee_leaves.ids)]
        # Precompute values in batch for performance purposes
        work_time_per_day_mapped = {
            (date_from, date_to, calendar): employees.with_context(
                    compute_leaves=not include_public_holidays_in_duration)._list_work_time_per_day(date_from, date_to, domain=domain, calendar=calendar)
            for (date_from, date_to, include_public_holidays_in_duration, calendar), employees in employees_by_dates_calendar.items()
        }
        work_days_data_mapped = {
            (date_from, date_to, calendar): employees._get_work_days_data_batch(date_from, date_to, compute_leaves=not include_public_holidays_in_duration, domain=domain, calendar=calendar)
            for (date_from, date_to, include_public_holidays_in_duration, calendar), employees in employees_by_dates_calendar.items()
        }
        for leave in self:
            calendar = resource_calendar or leave.resource_calendar_id
            if not leave.date_from or not leave.date_to or not calendar:
                result[leave.id] = (0, 0)
                continue
            hours, days = (0, 0)
            if leave.employee_id:
                if leave.leave_type_request_unit == 'day' and check_leave_type:
                    # list of tuples (day, hours)
                    work_time_per_day_list = work_time_per_day_mapped[(leave.date_from, leave.date_to, calendar)][leave.employee_id.id]
                    days = len(work_time_per_day_list)
                    hours = sum(map(lambda t: t[1], work_time_per_day_list))
                else:
                    work_days_data = work_days_data_mapped[(leave.date_from, leave.date_to, calendar)][leave.employee_id.id]
                    hours, days = work_days_data['hours'], work_days_data['days']
            else:
                today_hours = calendar.get_work_hours_count(
                    datetime.combine(leave.date_from.date(), time.min),
                    datetime.combine(leave.date_from.date(), time.max),
                    False)
                hours = calendar.get_work_hours_count(leave.date_from, leave.date_to, compute_leaves=not leave.holiday_status_id.include_public_holidays_in_duration)
                days = hours / (today_hours or HOURS_PER_DAY)
            if leave.leave_type_request_unit == 'day' and check_leave_type:
                days = ceil(days)
            result[leave.id] = (days, hours)
        return result

    @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit')
    def _compute_duration(self):
        durations = self._get_durations()
        for leave in self:
            days, hours = durations[leave.id]
            leave.number_of_hours = hours
            leave.number_of_days = days

    @api.depends('employee_company_id')
    def _compute_company_id(self):
        for holiday in self:
            holiday.company_id = holiday.employee_company_id or holiday.department_id.company_id or self.env.company

    @api.depends('number_of_days')
    def _compute_last_several_days(self):
        for holiday in self:
            holiday.last_several_days = holiday.number_of_days > 1

    @api.depends('tz')
    @api.depends_context('uid')
    def _compute_tz_mismatch(self):
        for leave in self:
            leave.tz_mismatch = leave.tz != self.env.user.tz

    @api.depends('resource_calendar_id.tz')
    def _compute_tz(self):
        for leave in self:
            leave.tz = leave.resource_calendar_id.tz or self.env.company.resource_calendar_id.tz or self.env.user.tz or 'UTC'

    @api.depends('number_of_hours', 'number_of_days', 'leave_type_request_unit')
    def _compute_duration_display(self):
        for leave in self:
            duration = leave.number_of_days
            unit = _('days')
            display = "%g %s" % (float_round(duration, precision_digits=2), unit)
            if leave.leave_type_request_unit == "hour":
                hours, minutes = divmod(abs(leave.number_of_hours) * 60, 60)
                minutes = round(minutes)
                if minutes == 60:
                    minutes = 0
                    hours += 1
                duration = '%d:%02d' % (hours, minutes)
                unit = _("hours")
                display = f"{duration} {unit}"
            leave.duration_display = display

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_reset(self):
        for holiday in self:
            try:
                holiday._check_approval_update('confirm')
            except (AccessError, UserError):
                holiday.can_reset = False
            else:
                holiday.can_reset = True

    @api.depends('state', 'employee_id', 'department_id')
    def _compute_can_approve(self):
        for holiday in self:
            try:
                if holiday.state == 'confirm' and holiday.validation_type == 'both':
                    holiday._check_approval_update('validate1')
                else:
                    holiday._check_approval_update('validate')
            except (AccessError, UserError):
                holiday.can_approve = False
            else:
                holiday.can_approve = True

    @api.depends_context('uid')
    @api.depends('state', 'employee_id')
    def _compute_can_cancel(self):
        now = fields.Datetime.now().date()
        for leave in self:
            leave.can_cancel = leave.id and leave.employee_id.user_id == self.env.user and leave.state in ['validate', 'validate1'] and leave.date_from and leave.date_from.date() >= now

    @api.depends('state')
    def _compute_is_hatched(self):
        for holiday in self:
            holiday.is_striked = holiday.state == 'refuse'
            holiday.is_hatched = holiday.state not in ['refuse', 'validate']

    @api.depends('leave_type_support_document', 'attachment_ids')
    def _compute_supported_attachment_ids(self):
        for holiday in self:
            holiday.supported_attachment_ids = holiday.attachment_ids
            holiday.supported_attachment_ids_count = len(holiday.attachment_ids.ids)

    def _inverse_supported_attachment_ids(self):
        for holiday in self:
            holiday.attachment_ids = holiday.supported_attachment_ids

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date(self):
        if self.env.context.get('leave_skip_date_check', False):
            return

        all_leaves = self.search([
            ('date_from', '<', max(self.mapped('date_to'))),
            ('date_to', '>', min(self.mapped('date_from'))),
            ('employee_id', 'in', self.employee_id.ids),
            ('id', 'not in', self.ids),
            ('state', 'not in', ['cancel', 'refuse']),
        ])
        for holiday in self:
            domain = [
                ('employee_id', '=', holiday.employee_id.id),
                ('date_from', '<', holiday.date_to),
                ('date_to', '>', holiday.date_from),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
            ]
            conflicting_holidays = all_leaves.filtered_domain(domain)

            if conflicting_holidays:
                conflicting_holidays_list = []
                # Do not display the name of the employee if the conflicting holidays have an employee_id.user_id equivalent to the user id
                holidays_only_have_uid = bool(holiday.employee_id)
                holiday_states = dict(conflicting_holidays.fields_get(allfields=['state'])['state']['selection'])
                for conflicting_holiday in conflicting_holidays:
                    conflicting_holiday_data = {}
                    conflicting_holiday_data['employee_name'] = conflicting_holiday.employee_id.name
                    conflicting_holiday_data['date_from'] = format_date(self.env, min(conflicting_holiday.mapped('date_from')))
                    conflicting_holiday_data['date_to'] = format_date(self.env, min(conflicting_holiday.mapped('date_to')))
                    conflicting_holiday_data['state'] = holiday_states[conflicting_holiday.state]
                    if conflicting_holiday.employee_id.user_id.id != self.env.uid:
                        holidays_only_have_uid = False
                    if conflicting_holiday_data not in conflicting_holidays_list:
                        conflicting_holidays_list.append(conflicting_holiday_data)
                if not conflicting_holidays_list:
                    return
                conflicting_holidays_strings = []
                if holidays_only_have_uid:
                    for conflicting_holiday_data in conflicting_holidays_list:
                        conflicting_holidays_string = _('from %(date_from)s to %(date_to)s - %(state)s',
                                                        date_from=conflicting_holiday_data['date_from'],
                                                        date_to=conflicting_holiday_data['date_to'],
                                                        state=conflicting_holiday_data['state'])
                        conflicting_holidays_strings.append(conflicting_holidays_string)
                    raise ValidationError(_("""\
You've already booked time off which overlaps with this period:
%s
Attempting to double-book your time off won't magically make your vacation 2x better!
""",
                        "\n".join(conflicting_holidays_strings)))
                for conflicting_holiday_data in conflicting_holidays_list:
                    conflicting_holidays_string = "\n" + _('%(employee_name)s - from %(date_from)s to %(date_to)s - %(state)s',
                                                    employee_name=conflicting_holiday_data['employee_name'],
                                                    date_from=conflicting_holiday_data['date_from'],
                                                    date_to=conflicting_holiday_data['date_to'],
                                                    state=conflicting_holiday_data['state'])
                    conflicting_holidays_strings.append(conflicting_holidays_string)
                raise ValidationError(_(
                    "An employee already booked time off which overlaps with this period:%s",
                    "".join(conflicting_holidays_strings)))

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_date_state(self):
        if self.env.context.get('leave_skip_state_check'):
            return
        for holiday in self:
            if holiday.state in ['validate1', 'validate']:
                raise ValidationError(_("This modification is not allowed in the current state."))

    def _check_validity(self):
        sorted_leaves = defaultdict(lambda: self.env['hr.leave'])
        for leave in self:
            sorted_leaves[(leave.holiday_status_id, leave.date_from.date())] |= leave
        for (leave_type, date_from), leaves in sorted_leaves.items():
            if leave_type.requires_allocation == 'no':
                continue
            employees = leaves.employee_id
            leave_data = leave_type.get_allocation_data(employees, date_from)
            if leave_type.allows_negative:
                max_excess = leave_type.max_allowed_negative
                for employee in employees:
                    if leave_data[employee] and leave_data[employee][0][1]['virtual_remaining_leaves'] < -max_excess:
                        raise ValidationError(_("There is no valid allocation to cover that request."))
                continue

            previous_leave_data = leave_type.with_context(
                ignored_leave_ids=leaves.ids
            ).get_allocation_data(employees, date_from)
            for employee in employees:
                previous_emp_data = previous_leave_data[employee] and previous_leave_data[employee][0][1]['virtual_excess_data']
                emp_data = leave_data[employee] and leave_data[employee][0][1]['virtual_excess_data']
                if not previous_emp_data and not emp_data:
                    continue
                if previous_emp_data != emp_data and len(emp_data) >= len(previous_emp_data):
                    raise ValidationError(_("There is no valid allocation to cover that request."))

    ####################################################
    # ORM Overrides methods
    ####################################################

    @api.depends(
        'tz', 'date_from', 'date_to', 'employee_id',
        'holiday_status_id', 'number_of_hours',
        'leave_type_request_unit', 'number_of_days', 'department_id',
    )
    @api.depends_context('short_name', 'hide_employee_name', 'groupby')
    def _compute_display_name(self):
        for leave in self:
            user_tz = timezone(leave.tz)
            date_from_utc = leave.date_from and leave.date_from.astimezone(user_tz).date()
            date_to_utc = leave.date_to and leave.date_to.astimezone(user_tz).date()
            time_off_type_display = leave.holiday_status_id.name
            if self.env.context.get('short_name'):
                short_leave_name = leave.name or time_off_type_display or _('Time Off')
                leave.display_name = _("%(name)s: %(duration)s", name=short_leave_name, duration=leave.duration_display)
            else:
                target = leave.employee_id.name or ""
                display_date = format_date(self.env, date_from_utc) or ""
                if leave.number_of_days > 1 and date_from_utc and date_to_utc:
                    display_date += _(' to %(date_to_utc)s',
                        date_to_utc=format_date(self.env, date_to_utc) or ""
                    )
                if not target or self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
                    leave.display_name = _("%(leave_type)s: %(duration)s (%(start)s)",
                        leave_type=time_off_type_display,
                        duration=leave.duration_display,
                        start=display_date,
                    )
                elif not time_off_type_display:
                    leave.display_name = _("%(person)s: %(duration)s (%(start)s)",
                        person=target,
                        duration=leave.duration_display,
                        start=display_date,
                    )
                else:
                    leave.display_name = _("%(person)s on %(leave_type)s: %(duration)s (%(start)s)",
                        person=target,
                        leave_type=time_off_type_display,
                        duration=leave.duration_display,
                        start=display_date,
                    )

    def onchange(self, values, field_names, fields_spec):
        # Try to force the leave_type display_name when creating new records
        # This is called right after pressing create and returns the display_name for
        # most fields in the view.
        if values and 'employee_id' in fields_spec and 'employee_id' not in self._context:
            employee_id = get_employee_from_context(values, self._context, self.env.user.employee_id.id)
            self = self.with_context(employee_id=employee_id)
        return super().onchange(values, field_names, fields_spec)

    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            self.message_subscribe(partner_ids=employee.user_id.partner_id.ids)

    @api.constrains('date_from', 'date_to')
    def _check_mandatory_day(self):
        is_leave_user = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        if not is_leave_user and any(leave.has_mandatory_day for leave in self):
            raise ValidationError(_('You are not allowed to request time off on a Mandatory Day'))

    def _check_double_validation_rules(self, employees, state):
        if self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            return

        is_leave_user = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        if state == 'validate1':
            employees = employees.filtered(lambda employee: employee.leave_manager_id != self.env.user)
            if employees and not is_leave_user:
                raise AccessError(_('You cannot first approve a time off for %s, because you are not his time off manager', employees[0].name))
        elif state == 'validate' and not is_leave_user:
            # Is probably handled via ir.rule
            raise AccessError(_('You don\'t have the rights to apply second approval on a time off request'))

    @api.model_create_multi
    def create(self, vals_list):
        # Override to avoid automatic logging of creation
        if not self._context.get('leave_fast_create'):
            leave_types = self.env['hr.leave.type'].browse([values.get('holiday_status_id') for values in vals_list if values.get('holiday_status_id')])
            mapped_validation_type = {leave_type.id: leave_type.leave_validation_type for leave_type in leave_types}

            for values in vals_list:
                employee_id = values.get('employee_id', False)
                leave_type_id = values.get('holiday_status_id')

                # Handle double validation
                if mapped_validation_type[leave_type_id] == 'both':
                    self._check_double_validation_rules(employee_id, values.get('state', False))

        holidays = super(HolidaysRequest, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        holidays._check_validity()

        for holiday in holidays:
            if not self._context.get('leave_fast_create'):
                # Everything that is done here must be done using sudo because we might
                # have different create and write rights
                # eg : holidays_user can create a leave request with validation_type = 'manager' for someone else
                # but they can only write on it if they are leave_manager_id
                holiday_sudo = holiday.sudo()
                holiday_sudo.add_follower(holiday.employee_id.id)
                if holiday.validation_type == 'manager':
                    holiday_sudo.message_subscribe(partner_ids=holiday.employee_id.leave_manager_id.partner_id.ids)
                if holiday.validation_type == 'no_validation':
                    # Automatic validation should be done in sudo, because user might not have the rights to do it by himself
                    holiday_sudo.action_validate()
                    holiday_sudo.message_subscribe(partner_ids=holiday._get_responsible_for_approval().partner_id.ids)
                    holiday_sudo.message_post(body=_("The time off has been automatically approved"), subtype_xmlid="mail.mt_comment") # Message from OdooBot (sudo)
                elif not self._context.get('import_file'):
                    holiday_sudo.activity_update()
        return holidays

    def write(self, values):
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user') or self.env.is_superuser()
        if not is_officer and values.keys() - {'attachment_ids', 'supported_attachment_ids', 'message_main_attachment_id'}:
            if any(hol.date_from.date() < fields.Date.today() and hol.employee_id.leave_manager_id != self.env.user for hol in self):
                raise UserError(_('You must have manager rights to modify/validate a time off that already begun'))
            if any(leave.state == 'cancel' for leave in self):
                raise UserError(_('Only a manager can modify a canceled leave.'))

        # Unlink existing resource.calendar.leaves for validated time off
        if 'state' in values and values['state'] != 'validate':
            validated_leaves = self.filtered(lambda l: l.state == 'validate')
            validated_leaves._remove_resource_leave()

        employee_id = values.get('employee_id', False)
        if not self.env.context.get('leave_fast_create'):
            if values.get('state'):
                self._check_approval_update(values['state'])
                if any(holiday.validation_type == 'both' for holiday in self):
                    if values.get('employee_id'):
                        employees = self.env['hr.employee'].browse(values.get('employee_id'))
                    else:
                        employees = self.mapped('employee_id')
                    self._check_double_validation_rules(employees, values['state'])
            if 'date_from' in values:
                values['request_date_from'] = values['date_from']
            if 'date_to' in values:
                values['request_date_to'] = values['date_to']
        result = super(HolidaysRequest, self).write(values)
        if any(field in values for field in ['request_date_from', 'date_from', 'request_date_from', 'date_to', 'holiday_status_id', 'employee_id', 'state']):
            self._check_validity()
        if not self.env.context.get('leave_fast_create'):
            for holiday in self:
                if employee_id:
                    holiday.add_follower(employee_id)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        error_message = _('You cannot delete a time off which is in %s state')
        state_description_values = {elem[0]: elem[1] for elem in self._fields['state']._description_selection(self.env)}
        now = fields.Datetime.now().date()

        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            for hol in self:
                if hol.state not in ['confirm', 'validate1', 'cancel']:
                    raise UserError(error_message % state_description_values.get(self[:1].state))
                if hol.date_from.date() < now:
                    raise UserError(_('You cannot delete a time off which is in the past'))
        else:
            for holiday in self.filtered(lambda holiday: holiday.state not in ['cancel', 'confirm']):
                raise UserError(error_message % (state_description_values.get(holiday.state),))

    def unlink(self):
        self.sudo()._post_leave_cancel()
        return super(HolidaysRequest, self.with_context(leave_skip_date_check=True)).unlink()

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if default and 'request_date_from' in default and 'request_date_to' in default:
            return vals_list
        if all(leave.state in ['cancel', 'refuse'] for leave in self):  # No overlap constraint in these cases
            return vals_list
        raise UserError(_('A time off cannot be duplicated.'))

    def _get_redirect_suggested_company(self):
        return self.holiday_status_id.company_id

    ####################################################
    # Business methods
    ####################################################

    @api.model
    def action_open_records(self, leave_ids):
        if len(leave_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_id': leave_ids[0],
                'res_model': 'hr.leave',
            }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': [[False, 'list'], [False, 'form']],
            'domain': [('id', 'in', leave_ids.ids)],
            'res_model': 'hr.leave',
        }

    def _prepare_resource_leave_vals(self):
        """Hook method for others to inject data
        """
        self.ensure_one()
        return {
            'name': _("%s: Time Off", self.employee_id.name),
            'date_from': self.date_from,
            'holiday_id': self.id,
            'date_to': self.date_to,
            'resource_id': self.employee_id.resource_id.id,
            'calendar_id': self.resource_calendar_id.id,
            'time_type': self.holiday_status_id.time_type,
        }

    def _create_resource_leave(self):
        """ This method will create entry in resource calendar time off object at the time of holidays validated
        :returns: created `resource.calendar.leaves`
        """
        vals_list = [leave._prepare_resource_leave_vals() for leave in self]
        return self.env['resource.calendar.leaves'].sudo().create(vals_list)

    def _remove_resource_leave(self):
        """ This method will create entry in resource calendar time off object at the time of holidays cancel/removed """
        return self.env['resource.calendar.leaves'].search([('holiday_id', 'in', self.ids)]).unlink()

    def _validate_leave_request(self):
        """ Validate time off requests
        by creating a calendar event and a resource time off. """
        holidays = self.filtered("employee_id")
        holidays._create_resource_leave()
        meeting_holidays = holidays.filtered(lambda l: l.holiday_status_id.create_calendar_meeting)
        meetings = self.env['calendar.event']
        if meeting_holidays:
            meeting_values_for_user_id = meeting_holidays._prepare_holidays_meeting_values()
            Meeting = self.env['calendar.event']
            for user_id, meeting_values in meeting_values_for_user_id.items():
                meetings += Meeting.with_user(user_id or self.env.uid).with_context(
                                allowed_company_ids=[],
                                no_mail_to_attendees=True,
                                calendar_no_videocall=True,
                                active_model=self._name
                            ).create(meeting_values)
        Holiday = self.env['hr.leave']
        for meeting in meetings:
            Holiday.browse(meeting.res_id).meeting_id = meeting

        for holiday in holidays:
            user_tz = timezone(holiday.tz)
            utc_tz = pytz.utc.localize(holiday.date_from).astimezone(user_tz)
            notify_partner_ids = holiday.employee_id.user_id.partner_id.ids
            holiday.message_post(
                body=_(
                    'Your %(leave_type)s planned on %(date)s has been accepted',
                    leave_type=holiday.holiday_status_id.display_name,
                    date=utc_tz.replace(tzinfo=None)
                ),
                partner_ids=notify_partner_ids)


    def _prepare_holidays_meeting_values(self):
        result = defaultdict(list)
        for holiday in self:
            user = holiday.user_id
            meeting_name = _(
                "%(employee)s on Time Off : %(duration)s",
                employee=holiday.employee_id.name or holiday.category_id.name,
                duration=holiday.duration_display)
            allday_value = not holiday.request_unit_half
            if holiday.leave_type_request_unit == 'hour':
                allday_value = float_compare(holiday.number_of_days, 1.0, 1) >= 0
            meeting_values = {
                'name': meeting_name,
                'duration': holiday.number_of_days * (holiday.resource_calendar_id.hours_per_day or HOURS_PER_DAY),
                'description': holiday.notes,
                'user_id': user.id,
                'start': holiday.date_from,
                'stop': holiday.date_to,
                'allday': allday_value,
                'privacy': 'confidential',
                'event_tz': user.tz,
                'activity_ids': [(5, 0, 0)],
                'res_id': holiday.id,
            }
            # Add the partner_id (if exist) as an attendee
            partner_id = (user and user.partner_id) or (holiday.employee_id and holiday.employee_id.work_contact_id)
            if partner_id:
                meeting_values['partner_ids'] = [(4, partner_id.id)]
            result[user.id].append(meeting_values)
        return result

    def action_cancel(self):
        self.ensure_one()

        return {
            'name': _('Cancel Time Off'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_model': 'hr.holidays.cancel.leave',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'context': {
                'default_leave_id': self.id,
            }
        }

    def action_reset_confirm(self):
        if any(holiday.state not in ['cancel', 'refuse'] for holiday in self):
            raise UserError(_('Time off request state must be "Refused" or "Cancelled" in order to be reset to "Confirmed".'))
        self.write({
            'state': 'confirm',
            'first_approver_id': False,
            'second_approver_id': False,
        })
        self.activity_update()
        return True

    def action_approve(self, check_state=True):
        # if validation_type == 'both': this method is the first approval approval
        # if validation_type != 'both': this method calls action_validate() below

        # Do not check the state in case we are redirected from the dashboard
        if check_state and any(holiday.state != 'confirm' for holiday in self):
            raise UserError(_('Time off request must be confirmed ("To Approve") in order to approve it.'))

        current_employee = self.env.user.employee_id
        self.filtered(lambda hol: hol.validation_type == 'both').write({'state': 'validate1', 'first_approver_id': current_employee.id})

        self.filtered(lambda hol: hol.validation_type != 'both').action_validate(check_state)
        if not self.env.context.get('leave_fast_create'):
            self.activity_update()
        return True

    def _get_leaves_on_public_holiday(self):
        return self.filtered(lambda l: l.employee_id and not l.number_of_days)

    def _split_leaves(self, split_date_from, split_date_to):
        """
        Split leaves on the given full-day interval. The leaves will be split
        into two new leaves: the period up until (but not including)
        split_date_from and the period starting at (and including)
        split_date_to.

        This means that the period in between split_date_from and split_date_to
        will no longer be covered by the new leaves. In order to split a leave
        without losing any leave coverage, split_date_from and split_date_to
        should therefore be the same.

        Another important note to make is that this method only splits leaves
        on full-day intervals. Logic to split leaves on partial days or hours
        is not straightforward as you have to take into account working hours
        and timezones. It's also not clear that we would want to handle this
        automatically. The method will therefore also only work on leaves that
        are taken in full or half days (Though a half day leave in the interval
        will simply be refused - there are no multi-day spanning half-day
        leaves)

        The method creates one or two new leaves per leave that needs to be
        split and refuses the original leave.
        """
        # Keep track of the original states before refusing the leaves and creating new ones
        original_states = {l.id: l.state for l in self}

        # Refuse all original leaves
        self.action_refuse()
        split_leaves_vals = []

        # Only leaves that span a period outside of the split interval need
        # to be split.
        multi_day_leaves = self.filtered(lambda l: l.request_date_from < split_date_from or l.request_date_to >= split_date_to)

        for leave in multi_day_leaves:
            # Leaves in days
            new_leave_vals = []

            # Get the values to create the leave before the split
            if leave.request_date_from < split_date_from:
                new_leave_vals.append(leave.copy_data({
                    'request_date_from': leave.request_date_from,
                    'request_date_to': split_date_from + timedelta(days=-1),
                    'state': original_states[leave.id],
                })[0])

            # Do the same for the new leave after the split
            if leave.request_date_to >= split_date_to:
                new_leave_vals.append(leave.copy_data({
                    'request_date_from': split_date_to,
                    'request_date_to': leave.request_date_to,
                    'state': original_states[leave.id],
                })[0])

            # For those two new leaves, only create them if they actually
            # have a non-zero duration.
            for leave_vals in new_leave_vals:
                new_leave = self.env['hr.leave'].new(leave_vals)
                new_leave._compute_date_from_to()
                # Could happen for part-time contract, that time off is not necessary
                # anymore.
                # Imagine you work on monday-wednesday-friday only.
                # You take a time off on friday.
                # We create a company time off on friday.
                # By looking at the last attendance before the company time off
                # start date to compute the date_to, you would have a date_from > date_to.
                # Just don't create the leave at that time. That's the reason why we use
                # new instead of create. As the leave is not actually created yet, the sql
                # constraint didn't check date_from < date_to yet.
                if new_leave.date_from < new_leave.date_to:
                    split_leaves_vals.append(new_leave._convert_to_write(new_leave._cache))

        split_leaves = self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_fast_create=True,
            leave_skip_state_check=True
        ).create(split_leaves_vals)

        split_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()

    def action_validate(self, check_state=True):
        current_employee = self.env.user.employee_id
        leaves = self._get_leaves_on_public_holiday()
        if leaves:
            raise ValidationError(_('The following employees are not supposed to work during that period:\n %s') % ','.join(leaves.mapped('employee_id.name')))
        if check_state and any(holiday.state not in ['confirm', 'validate1'] and holiday.validation_type != 'no_validation' for holiday in self):
            raise UserError(_('Time off request must be confirmed in order to approve it.'))

        self.write({'state': 'validate'})

        leaves_second_approver = self.env['hr.leave']
        leaves_first_approver = self.env['hr.leave']

        for leave in self:
            if leave.validation_type == 'both':
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

        leaves_second_approver.write({'second_approver_id': current_employee.id})
        leaves_first_approver.write({'first_approver_id': current_employee.id})

        self._validate_leave_request()
        if not self.env.context.get('leave_fast_create'):
            self.filtered(lambda holiday: holiday.validation_type != 'no_validation').activity_update()
        return True

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(holiday.state not in ['confirm', 'validate', 'validate1'] for holiday in self):
            raise UserError(_('Time off request must be confirmed or validated in order to refuse it.'))

        self._notify_manager()
        validated_holidays = self.filtered(lambda hol: hol.state == 'validate1')
        validated_holidays.write({'state': 'refuse', 'first_approver_id': current_employee.id})
        (self - validated_holidays).write({'state': 'refuse', 'second_approver_id': current_employee.id})
        # Delete the meeting
        self.mapped('meeting_id').write({'active': False})
        # Post a second message, more verbose than the tracking message
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_('Your %(leave_type)s planned on %(date)s has been refused', leave_type=holiday.holiday_status_id.display_name, date=holiday.date_from),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids)

        self.activity_update()
        return True

    def _notify_manager(self):
        leaves = self.filtered(lambda hol: (hol.validation_type == 'both' and hol.state in ['validate1', 'validate']) or (hol.validation_type == 'manager' and hol.state == 'validate'))
        for holiday in leaves:
            responsible = holiday.employee_id.leave_manager_id.partner_id.ids
            if responsible:
                self.env['mail.thread'].sudo().message_notify(
                    partner_ids=responsible,
                    model_description='Time Off',
                    subject=_('Refused Time Off'),
                    body=_(
                        '%(holiday_name)s has been refused.',
                        holiday_name=holiday.display_name,
                    ),
                    email_layout_xmlid='mail.mail_notification_light',
                )

    def _action_user_cancel(self, reason):
        self.ensure_one()
        if not self.can_cancel:
            raise ValidationError(_('This time off cannot be cancelled.'))

        self._force_cancel(reason, 'mail.mt_note')

    def _force_cancel(self, reason, msg_subtype='mail.mt_comment', notify_responsibles=True):
        recs = self.browse() if self.env.context.get(MODULE_UNINSTALL_FLAG) else self
        for leave in recs:
            leave.message_post(
                body=_('The time off has been cancelled: %s', reason),
                subtype_xmlid=msg_subtype
            )

            if not notify_responsibles:
                continue

            responsibles = self.env['res.partner']
            # manager
            if (leave.holiday_status_id.leave_validation_type == 'manager' and leave.state == 'validate') or (leave.holiday_status_id.leave_validation_type == 'both' and leave.state == 'validate1'):
                responsibles = leave.employee_id.leave_manager_id.partner_id
            # officer
            elif leave.holiday_status_id.leave_validation_type == 'hr' and leave.state == 'validate':
                responsibles = leave.holiday_status_id.responsible_ids.partner_id
            # both
            elif leave.holiday_status_id.leave_validation_type == 'both' and leave.state == 'validate':
                responsibles = leave.employee_id.leave_manager_id.partner_id
                responsibles |= leave.holiday_status_id.responsible_ids.partner_id

            if responsibles:
                self.env['mail.thread'].sudo().message_notify(
                    partner_ids=responsibles.ids,
                    model_description='Time Off',
                    subject=_('Cancelled Time Off'),
                    body=_(
                        "%(leave_name)s has been cancelled with the justification: <br/> %(reason)s.",
                        leave_name=leave.display_name,
                        reason=reason
                    ),
                    email_layout_xmlid='mail.mail_notification_light',
                )
        leave_sudo = self.sudo()
        leave_sudo.state = 'cancel'
        leave_sudo.activity_update()
        leave_sudo._post_leave_cancel()

    def _post_leave_cancel(self):
        self.meeting_id.active = False
        self._remove_resource_leave()

    def action_documents(self):
        domain = [('id', 'in', self.attachment_ids.ids)]
        return {
            'name': _("Supporting Documents"),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'context': {'create': False},
            'view_mode': 'kanban',
            'domain': domain
        }

    def _check_approval_update(self, state):
        """ Check if target state is achievable. """
        if self.env.is_superuser():
            return

        current_employee = self.env.user.employee_id
        is_officer = self.env.user.has_group('hr_holidays.group_hr_holidays_user')
        is_manager = self.env.user.has_group('hr_holidays.group_hr_holidays_manager')

        for holiday in self:
            val_type = holiday.validation_type

            if not is_manager:
                if holiday.state == 'cancel' and state != 'confirm':
                    raise UserError(_('A cancelled leave cannot be modified.'))
                if state == 'confirm':
                    if holiday.state == 'refuse':
                        raise UserError(_('Only a Time Off Manager can reset a refused leave.'))
                    if holiday.date_from and holiday.date_from.date() <= fields.Date.today():
                        raise UserError(_('Only a Time Off Manager can reset a started leave.'))
                    if holiday.employee_id != current_employee:
                        raise UserError(_('Only a Time Off Manager can reset other people leaves.'))
                else:
                    if val_type == 'no_validation' and current_employee == holiday.employee_id and (is_officer or is_manager):
                        continue
                    # use ir.rule based first access check: department, members, ... (see security.xml)
                    holiday.check_access('write')

                    # This handles states validate1 validate and refuse
                    if holiday.employee_id == current_employee\
                            and self.env.user != holiday.employee_id.leave_manager_id\
                            and not is_officer:
                        raise UserError(_('Only a Time Off Officer or Manager can approve/refuse its own requests.'))

                    if (state == 'validate1' and val_type == 'both'):
                        if not is_officer and self.env.user != holiday.employee_id.leave_manager_id:
                            raise UserError(_('You must be either %s\'s manager or Time off Manager to approve this leave') % (holiday.employee_id.name))

                    if (state == 'validate' and val_type == 'manager')\
                            and self.env.user != holiday.employee_id.leave_manager_id\
                            and not is_officer:
                        raise UserError(_("You must be %s's Manager to approve this leave", holiday.employee_id.name))

                    if not is_officer and (state == 'validate' and val_type == 'hr'):
                        raise UserError(_('You must either be a Time off Officer or Time off Manager to approve this leave'))

    @api.model
    def open_pending_requests(self):
        user_employee = self.env.user.employee_id
        employee = self.env['hr.employee']._get_contextual_employee()
        context = {'search_default_approve': True, 'search_default_second_approval': True}
        domain = []
        if employee != user_employee:
            view_name = 'hr_holidays.hr_leave_allocation_view_tree'
            context.update({'search_default_employee_id': employee.id})
        else:
            view_name = 'hr_holidays.hr_leave_allocation_view_tree_my'
            domain = [('employee_id', '=', employee.id)]
        return {
            'name': _('Allocation Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.allocation',
            'views': [[self.env.ref(view_name).id, 'list']],
            'domain': domain,
            'context': context,
        }
    # ------------------------------------------------------------
    # Activity methods
    # ------------------------------------------------------------

    def _get_responsible_for_approval(self):
        self.ensure_one()
        responsible = self.env.user
        if self.validation_type == 'manager' or (self.validation_type == 'both' and self.state == 'confirm'):
            if self.employee_id.leave_manager_id:
                responsible = self.employee_id.leave_manager_id
            elif self.employee_id.parent_id.user_id:
                responsible = self.employee_id.parent_id.user_id
        elif self.validation_type == 'hr' or (self.validation_type == 'both' and self.state == 'validate1'):
            if self.holiday_status_id.responsible_ids:
                responsible = self.holiday_status_id.responsible_ids
        return responsible

    def activity_update(self):
        to_clean, to_do, to_do_confirm_activity = self.env['hr.leave'], self.env['hr.leave'], self.env['hr.leave']
        activity_vals = []
        today = fields.Date.today()
        model_id = self.env.ref('hr_holidays.model_hr_leave').id
        confirm_activity = self.env.ref('hr_holidays.mail_act_leave_approval')
        approval_activity = self.env.ref('hr_holidays.mail_act_leave_second_approval')
        for holiday in self:
            if holiday.state in ['confirm', 'validate1']:
                if holiday.holiday_status_id.leave_validation_type != 'no_validation':
                    if holiday.state == 'confirm':
                        activity_type = confirm_activity
                        note = _(
                            'New %(leave_type)s Request created by %(user)s',
                            leave_type=holiday.holiday_status_id.name,
                            user=holiday.create_uid.name,
                        )
                    else:
                        activity_type = approval_activity
                        note = _(
                            'Second approval request for %(leave_type)s',
                            leave_type=holiday.holiday_status_id.name,
                        )
                        to_do_confirm_activity |= holiday
                    user_ids = holiday.sudo()._get_responsible_for_approval().ids or self.env.user.ids
                    for user_id in user_ids:
                        date_deadline = (
                            (holiday.date_from -
                             relativedelta(**{activity_type.delay_unit: activity_type.delay_count or 0})).date()
                            if holiday.date_from else today)
                        if date_deadline < today:
                            date_deadline = today
                        activity_vals.append({
                            'activity_type_id': activity_type.id,
                            'automated': True,
                            'date_deadline': date_deadline,
                            'note': note,
                            'user_id': user_id,
                            'res_id': holiday.id,
                            'res_model_id': model_id,
                        })
            elif holiday.state == 'validate':
                to_do |= holiday
            elif holiday.state in ['refuse', 'cancel']:
                to_clean |= holiday
        if to_clean:
            to_clean.activity_unlink(['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])
        if to_do_confirm_activity:
            to_do_confirm_activity.activity_feedback(['hr_holidays.mail_act_leave_approval'])
        if to_do:
            to_do.activity_feedback(['hr_holidays.mail_act_leave_approval', 'hr_holidays.mail_act_leave_second_approval'])
        self.env['mail.activity'].with_context(short_name=False).create(activity_vals)

    ####################################################
    # Messaging methods
    ####################################################

    def _notify_change(self, message, subtype_xmlid='mail.mt_note'):
        for leave in self:
            leave.message_post(body=message, subtype_xmlid=subtype_xmlid)

            recipient = None
            if leave.user_id:
                recipient = leave.user_id.partner_id.id
            elif leave.employee_id:
                recipient = leave.employee_id.work_contact_id.id

            if recipient:
                self.env['mail.thread'].sudo().message_notify(
                    body=message,
                    partner_ids=[recipient],
                    subject=_('Your Time Off'),
                )

    def _track_subtype(self, init_values):
        if 'state' in init_values and self.state == 'validate':
            leave_notif_subtype = self.holiday_status_id.leave_notif_subtype_id
            return leave_notif_subtype or self.env.ref('hr_holidays.mt_leave')
        return super(HolidaysRequest, self)._track_subtype(init_values)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ Handle HR users and officers recipients that can validate or refuse holidays
        directly from email. """
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        local_msg_vals = dict(msg_vals or {})

        self.ensure_one()
        hr_actions = []
        if self.state == 'confirm':
            app_action = self._notify_get_action_link('controller', controller='/leave/approve', **local_msg_vals)
            hr_actions += [{'url': app_action, 'title': _('Approve')}]
        if self.state == 'validate1':
            app_action = self._notify_get_action_link('controller', controller='/leave/validate', **local_msg_vals)
            hr_actions += [{'url': app_action, 'title': _('Validate')}]
        if self.state in ['confirm', 'validate', 'validate1']:
            ref_action = self._notify_get_action_link('controller', controller='/leave/refuse', **local_msg_vals)
            hr_actions += [{'url': ref_action, 'title': _('Refuse')}]

        holiday_user_group_id = self.env.ref('hr_holidays.group_hr_holidays_user').id
        new_group = (
            'group_hr_holidays_user',
            lambda pdata: pdata['type'] == 'user' and holiday_user_group_id in pdata['groups'],
            {
                'actions': hr_actions,
                'active': True,
                'has_button_access': True,
            }
        )

        return [new_group] + groups

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # due to record rule can not allow to add follower and mention on validated leave so subscribe through sudo
        if any(holiday.state in ['validate', 'validate1'] for holiday in self):
            self.check_access('read')
            return super(HolidaysRequest, self.sudo()).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)
        return super(HolidaysRequest, self).message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        employee_id = self.env.context.get('employee_id', False)
        employee = self.env['hr.employee'].browse(employee_id) if employee_id else self.env.user.employee_id
        return employee.sudo(False)._get_unusual_days(date_from, date_to)

    def _to_utc(self, date, hour, resource):
        hour = float_to_time(float(hour))
        holiday_tz = timezone(resource.tz or self.env.user.tz or 'UTC')
        return holiday_tz.localize(datetime.combine(date, hour)).astimezone(UTC).replace(tzinfo=None)

    def _get_hour_from_to(self, request_date_from, request_date_to, day_period=None):
        """
        Return the hour_from and hour_to for the given request dates, based on
        the resource calendar.

        If there are no attendances on the exact days of the request, return
        the earliest hour_from and latest hour_to that exist in the schedule.
        """
        self.ensure_one()
        domain = [
            ('calendar_id', '=', self.resource_calendar_id.id),
            ('display_type', '=', False),
            ('day_period', '!=', 'lunch'),
        ]
        if day_period:
            domain.append(('day_period', '=', day_period))
        attendances = self.env['resource.calendar.attendance']._read_group(domain,
            ['week_type', 'dayofweek'],
            ['hour_from:min', 'hour_to:max'])

        # Must be sorted by dayofweek ASC and day_period DESC
        attendances = sorted([DummyAttendance(hour_from, hour_to, dayofweek, None, week_type) for week_type, dayofweek, hour_from, hour_to in attendances], key=lambda att: att.dayofweek)

        # If we can't find any attendances on the exact days of the request,
        # we default to the widest possible range that exists in the schedule.
        default_start = min((attendance.hour_from for attendance in attendances), default=0)
        default_end = max((attendance.hour_to for attendance in attendances), default=0)

        start_week_type = 0
        end_week_type = 0
        if self.resource_calendar_id.two_weeks_calendar:
            start_week_type = self.env['resource.calendar.attendance'].get_week_type(request_date_from)
            end_week_type = self.env['resource.calendar.attendance'].get_week_type(request_date_to)

        hour_from = next((att.hour_from for att in attendances if int(att.dayofweek) == request_date_from.weekday() and (int(att.week_type) == start_week_type)),
                         default_start)
        hour_to = next((att.hour_to for att in attendances if int(att.dayofweek) == request_date_to.weekday() and (int(att.week_type) == end_week_type)),
                       default_end)

        return (hour_from, hour_to)

    ####################################################
    # Cron methods
    ####################################################

    @api.model
    def _cancel_invalid_leaves(self):
        inspected_date = fields.Date.today() + timedelta(days=31)
        start_datetime = datetime.combine(fields.Date.today(), datetime.min.time())
        end_datetime = datetime.combine(inspected_date, datetime.max.time())
        concerned_leaves = self.search([
            ('date_from', '>=', start_datetime),
            ('date_from', '<=', end_datetime),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
        ], order='date_from desc')
        accrual_allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', concerned_leaves.employee_id.ids),
            ('holiday_status_id', 'in', concerned_leaves.holiday_status_id.ids),
            ('allocation_type', '=', 'accrual'),
            ('date_from', '<=', end_datetime),
            '|',
            ('date_to', '>=', start_datetime),
            ('date_to', '=', False),
        ])
        # only take leaves linked to accruals
        concerned_leaves = concerned_leaves\
            .filtered(lambda leave: leave.holiday_status_id in accrual_allocations.holiday_status_id)\
            .sorted('date_from', reverse=True)
        reason = _("the accruated amount is insufficient for that duration.")
        for leave in concerned_leaves:
            leave_type = leave.holiday_status_id
            date = leave.date_from.date()
            leave_type_data = leave_type.get_allocation_data(leave.employee_id, date)
            exceeding_duration = leave_type_data[leave.employee_id][0][1]['total_virtual_excess']
            excess_limit = leave_type.max_allowed_negative if leave_type.allows_negative else 0
            if exceeding_duration <= excess_limit:
                continue
            leave._force_cancel(reason, 'mail.mt_note')
