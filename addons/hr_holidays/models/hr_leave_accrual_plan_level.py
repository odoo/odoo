# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero
from psycopg2 import IntegrityError

DAYS = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']
MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
# Used for displaying the days and reversing selection -> integer
DAY_SELECT_VALUES = [str(i) for i in range(1, 29)] + ['last']
DAY_SELECT_SELECTION_NO_LAST = tuple(zip(DAY_SELECT_VALUES, (str(i) for i in range(1, 29))))

def _get_selection_days(self):
    return DAY_SELECT_SELECTION_NO_LAST + (("last", _("last day")),)


class HrLeaveAccrualLevel(models.Model):
    _name = 'hr.leave.accrual.level'
    _description = "Accrual Plan Level"
    _order = 'sequence asc'

    sequence = fields.Integer(
        string='sequence', compute='_compute_sequence', store=True,
        help='Sequence is generated automatically by start time delta.')
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan', "Accrual Plan", required=True, index=True, ondelete="cascade", default=lambda self: self.env.context.get("active_id", None))
    accrued_gain_time = fields.Selection(related='accrual_plan_id.accrued_gain_time', store=True)
    start_count = fields.Integer(
        "Start after",
        compute='_compute_start_count', store=True, readonly=False,
        help="The accrual starts after a defined period from the allocation start date. This field defines the number of days, months or years after which accrual is used.", default="1")
    start_type = fields.Selection(
        [('day', 'Days'),
         ('month', 'Months'),
         ('year', 'Years')],
        default='day', string=" ", required=True,
        help="This field defines the unit of time after which the accrual starts.")
    milestone_date = fields.Selection(
        [('creation', 'At allocation creation'),
         ('after', 'After')],
        compute='_compute_milestone_date', inverse='_inverse_start_count', readonly=False,
        store=True,
        default='after', required=True
    )
    # Accrue of
    added_value = fields.Float(
        "Rate", digits=(16, 5), required=True, default=1)
    added_value_type = fields.Selection([
        ('day', 'Day(s)'),
        ('hour', 'Hour(s)')
    ], compute="_compute_added_value_type", inverse="_inverse_added_value_type", store=True, required=True, readonly=False, default=lambda self: self.env.context.get("added_value_type","day"))
    frequency = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('bimonthly', 'Twice a month'),
        ('monthly', 'Monthly'),
        ('biyearly', 'Twice a year'),
        ('yearly', 'Yearly'),
    ], default='daily', required=True, string="Frequency")
    week_day = fields.Selection([
        ('mon', 'Monday'),
        ('tue', 'Tuesday'),
        ('wed', 'Wednesday'),
        ('thu', 'Thursday'),
        ('fri', 'Friday'),
        ('sat', 'Saturday'),
        ('sun', 'Sunday'),
    ], default="mon")
    first_day = fields.Integer(default=1)
    first_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_first_day_display')
    second_day = fields.Integer(default=15)
    second_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_second_day_display')
    first_month_day = fields.Integer(default=1)
    first_month_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_first_month_day_display')
    first_month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
    ], default="jan")
    second_month_day = fields.Integer(default=1)
    second_month_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_second_month_day_display')
    second_month = fields.Selection([
        ('jul', 'July'),
        ('aug', 'August'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ], default="jul")
    yearly_month = fields.Selection([
        ('jan', 'January'),
        ('feb', 'February'),
        ('mar', 'March'),
        ('apr', 'April'),
        ('may', 'May'),
        ('jun', 'June'),
        ('jul', 'July'),
        ('aug', 'August'),
        ('sep', 'September'),
        ('oct', 'October'),
        ('nov', 'November'),
        ('dec', 'December')
    ], default="jan")
    yearly_day = fields.Integer(default=1)
    yearly_day_display = fields.Selection(
        _get_selection_days, compute='_compute_days_display', inverse='_inverse_yearly_day_display')
    cap_accrued_time = fields.Boolean("Cap accrued time", default=True,
        help="When the field is checked the balance of an allocation using this accrual plan will never exceed the specified amount.")
    maximum_leave = fields.Float(
        'Limit to', digits=(16, 2), compute="_compute_maximum_leave", default=100, readonly=False, store=True,
        help="Choose a cap for this accrual.")
    cap_accrued_time_yearly = fields.Boolean(string="Yearly cap",
        store=True, readonly=False,
        help="When the field is checked the total amount accrued each year will be capped at the specified amount")
    maximum_leave_yearly = fields.Float(string="Yearly limit to", digits=(16, 2))
    can_be_carryover = fields.Boolean(related='accrual_plan_id.is_carryover', readonly=True)
    action_with_unused_accruals = fields.Selection(
        [('lost', 'Lost'),
         ('all', 'Carried over')],
        compute="_compute_action_with_unused_accruals",
        store=True,
        string="Carry over",
        default='all', required=True,
        help="When the Carry-Over Time is reached, according to Plan's setting, select what you want "
        "to happen with the unused time off: Lost (time will be reset to zero), Carried over (accrued time carried over to "
        "the next period.)")
    carryover_options = fields.Selection(
        [('unlimited', 'Unlimited'),
         ('limited', 'Up to')],
        store=True, readonly=False,
        compute="_compute_carryover_options",
        default='unlimited', required=True,
        help="You can limit the accrued time carried over for the next period."
    )
    postpone_max_days = fields.Integer("Maximum amount of accruals to transfer", store=True, readonly=False,
        help="Set a maximum of accruals an allocation keeps at the end of the year.")
    can_modify_value_type = fields.Boolean(compute="_compute_can_modify_value_type", default=lambda self: self.env.context.get("can_modify_value_type", None))
    accrual_validity = fields.Boolean("Accrual Validity", compute="_compute_accrual_validity", store=True, readonly=False)
    accrual_validity_count = fields.Integer(
        "Accrual Validity Count",
        help="You can define a period of time where the days carried over will be available", default="1")
    accrual_validity_type = fields.Selection(
        [('day', 'Days'),
         ('month', 'Months')],
        default='day', string="Accrual Validity Type", required=True,
        help="This field defines the unit of time after which the accrual ends.")

    _check_dates = models.Constraint(
        "CHECK((frequency NOT IN ('weekly', 'bimonthly', 'monthly', 'biyearly', 'yearly')) or (week_day IS NOT NULL AND frequency = 'weekly') or (first_day > 0 AND second_day > first_day AND first_day <= 31 AND second_day <= 31 AND frequency = 'bimonthly') or (first_day > 0 AND first_day <= 31 AND frequency = 'monthly')or (first_month_day > 0 AND first_month_day <= 31 AND second_month_day > 0 AND second_month_day <= 31 AND frequency = 'biyearly') or (yearly_day > 0 AND yearly_day <= 31 AND frequency = 'yearly'))",
        "The dates you've set up aren't correct. Please check them.",
    )

    _start_count_check = models.Constraint(
        'CHECK( start_count >= 0 )',
        'You can not start an accrual in the past.',
    )
    _added_value_greater_than_zero = models.Constraint(
        'CHECK(added_value > 0)',
        'You must give a rate greater than 0 in accrual plan levels.',
    )
    _valid_postpone_max_days_value = models.Constraint(
        "CHECK(action_with_unused_accruals <> 'all' OR carryover_options <> 'limited' OR COALESCE(postpone_max_days, 0) > 0)",
        'You cannot have a maximum quantity to carryover set to 0.',
    )
    _valid_accrual_validity_value = models.Constraint(
        'CHECK(accrual_validity IS NOT TRUE OR COALESCE(accrual_validity_count, 0) > 0)',
        'You cannot have an accrual validity time set to 0.',
    )
    _valid_yearly_cap_value = models.Constraint(
        'CHECK(cap_accrued_time_yearly IS NOT TRUE OR COALESCE(maximum_leave_yearly, 0) > 0)',
        'You cannot have a cap on yearly accrued time without setting a maximum amount.',
    )

    @api.constrains('cap_accrued_time', 'maximum_leave')
    def _check_maximum_leaves(self):
        for level in self:
            if level.cap_accrued_time and level.maximum_leave <= 0:
                raise(IntegrityError("You cannot have a milestone cap on accrued time set to 0."))

    @api.depends('start_count', 'start_type')
    def _compute_sequence(self):
        # Not 100% accurate because of odd months/years, but good enough
        start_type_multipliers = {
            'day': 1,
            'month': 30,
            'year': 365,
        }
        for level in self:
            level.sequence = level.start_count * start_type_multipliers[level.start_type]

    @api.depends('accrual_plan_id', 'accrual_plan_id.level_ids', 'accrual_plan_id.time_off_type_id')
    def _compute_can_modify_value_type(self):
        for level in self:
            level.can_modify_value_type = not level.accrual_plan_id.time_off_type_id and level.accrual_plan_id.level_ids and level.accrual_plan_id.level_ids[0] == level

    def _inverse_added_value_type(self):
        for level in self:
            if level.accrual_plan_id.level_ids[0] == level:
                level.accrual_plan_id.added_value_type = level.added_value_type

    @api.depends('accrual_plan_id', 'accrual_plan_id.level_ids', 'accrual_plan_id.added_value_type', 'accrual_plan_id.time_off_type_id')
    def _compute_added_value_type(self):
        for level in self:
            if level.accrual_plan_id.time_off_type_id:
                level.added_value_type = "day" if level.accrual_plan_id.time_off_type_id.request_unit in ["day", "half_day"] else "hour"
            elif level.accrual_plan_id.level_ids and level.accrual_plan_id.level_ids[0] != level:
                level.added_value_type = level.accrual_plan_id.level_ids[0].added_value_type

    @api.depends('first_day', 'second_day', 'first_month_day', 'second_month_day', 'yearly_day')
    def _compute_days_display(self):
        days_select = _get_selection_days(self)
        for level in self:
            level.first_day_display = days_select[min(level.first_day - 1, 28)][0]
            level.second_day_display = days_select[min(level.second_day - 1, 28)][0]
            level.first_month_day_display = days_select[min(level.first_month_day - 1, 28)][0]
            level.second_month_day_display = days_select[min(level.second_month_day - 1, 28)][0]
            level.yearly_day_display = days_select[min(level.yearly_day - 1, 28)][0]

    @api.depends('cap_accrued_time')
    def _compute_maximum_leave(self):
        for level in self:
            if not level.cap_accrued_time:
                level.maximum_leave = 0

    @api.depends('can_be_carryover')
    def _compute_action_with_unused_accruals(self):
        for level in self:
            if not level.can_be_carryover:
                level.action_with_unused_accruals = 'lost'

    @api.depends('action_with_unused_accruals')
    def _compute_carryover_options(self):
        for level in self:
            if level.action_with_unused_accruals == 'lost':
                level.carryover_options = 'unlimited'

    @api.depends('action_with_unused_accruals')
    def _compute_accrual_validity(self):
        for level in self:
            if level.action_with_unused_accruals == 'lost':
                level.accrual_validity = False

    @api.depends('start_count')
    def _compute_milestone_date(self):
        for level in self:
            if level.start_count == 0:
                level.milestone_date = 'creation'

    @api.depends('milestone_date')
    def _compute_start_count(self):
        for level in self:
            if level.milestone_date == 'creation':
                level.start_count = 0

    def _inverse_start_count(self):
        for level in self:
            if level.start_count == 0:
                level.milestone_date = 'creation'

    def _inverse_first_day_display(self):
        for level in self:
            if level.first_day_display == 'last':
                level.first_day = 31
            elif int(level.first_day_display) in range(1,29):
                level.first_day = DAY_SELECT_VALUES.index(level.first_day_display) + 1
            else:
                level.first_day = False

    def _inverse_second_day_display(self):
        for level in self:
            if level.second_day_display == 'last':
                level.second_day = 31
            elif int(level.second_day_display) in range(1,29):
                level.second_day = DAY_SELECT_VALUES.index(level.second_day_display) + 1
            else:
                level.second_day = False

    def _inverse_first_month_day_display(self):
        for level in self:
            if level.first_month_day_display == 'last':
                level.first_month_day = 31
            elif int(level.first_month_day_display) in range(1,29):
                level.first_month_day = DAY_SELECT_VALUES.index(level.first_month_day_display) + 1
            else:
                level.first_month_day = False

    def _inverse_second_month_day_display(self):
        for level in self:
            if level.second_month_day_display == 'last':
                level.second_month_day = 31
            elif int(level.second_month_day_display) in range(1,29):
                level.second_month_day = DAY_SELECT_VALUES.index(level.second_month_day_display) + 1
            else:
                level.second_month_day = False

    def _inverse_yearly_day_display(self):
        for level in self:
            if level.yearly_day_display == 'last':
                level.yearly_day = 31
            elif int(level.yearly_day_display) in range(1,29):
                level.yearly_day = DAY_SELECT_VALUES.index(level.yearly_day_display) + 1
            else:
                level.yearly_day = False

    def _get_next_date(self, last_call):
        """
        Returns the next date with the given last call
        """
        self.ensure_one()
        if self.frequency in ['hourly', 'daily']:
            return last_call + relativedelta(days=1)
        elif self.frequency == 'weekly':
            daynames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            weekday = daynames.index(self.week_day)
            return last_call + relativedelta(days=1, weekday=weekday)
        elif self.frequency == 'bimonthly':
            first_date = last_call + relativedelta(day=self.first_day)
            second_date = last_call + relativedelta(day=self.second_day)
            if last_call < first_date:
                return first_date
            elif last_call < second_date:
                return second_date
            else:
                return last_call + relativedelta(months=1, day=self.first_day)
        elif self.frequency == 'monthly':
            date = last_call + relativedelta(day=self.first_day)
            if last_call < date:
                return date
            else:
                return last_call + relativedelta(months=1, day=self.first_day)
        elif self.frequency == 'biyearly':
            first_month = MONTHS.index(self.first_month) + 1
            second_month = MONTHS.index(self.second_month) + 1
            first_date = last_call + relativedelta(month=first_month, day=self.first_month_day)
            second_date = last_call + relativedelta(month=second_month, day=self.second_month_day)
            if last_call < first_date:
                return first_date
            elif last_call < second_date:
                return second_date
            else:
                return last_call + relativedelta(years=1, month=first_month, day=self.first_month_day)
        elif self.frequency == 'yearly':
            month = MONTHS.index(self.yearly_month) + 1
            date = last_call + relativedelta(month=month, day=self.yearly_day)
            if last_call < date:
                return date
            else:
                return last_call + relativedelta(years=1, month=month, day=self.yearly_day)
        else:
            return False

    def _get_previous_date(self, last_call):
        """
        Returns the date a potential previous call would have been at
        For example if you have a monthly level giving 16/02 would return 01/02
        Contrary to `_get_next_date` this function will return the 01/02 if that date is given
        """
        self.ensure_one()
        if self.frequency in ['hourly', 'daily']:
            return last_call
        elif self.frequency == 'weekly':
            daynames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
            weekday = daynames.index(self.week_day)
            return last_call + relativedelta(days=-6, weekday=weekday)
        elif self.frequency == 'bimonthly':
            second_date = last_call + relativedelta(day=self.second_day)
            first_date = last_call + relativedelta(day=self.first_day)
            if last_call >= second_date:
                return second_date
            elif last_call >= first_date:
                return first_date
            else:
                return last_call + relativedelta(months=-1, day=self.second_day)
        elif self.frequency == 'monthly':
            date = last_call + relativedelta(day=self.first_day)
            if last_call >= date:
                return date
            else:
                return last_call + relativedelta(months=-1, day=self.first_day)
        elif self.frequency == 'biyearly':
            first_month = MONTHS.index(self.first_month) + 1
            second_month = MONTHS.index(self.second_month) + 1
            first_date = last_call + relativedelta(month=first_month, day=self.first_month_day)
            second_date = last_call + relativedelta(month=second_month, day=self.second_month_day)
            if last_call >= second_date:
                return second_date
            elif last_call >= first_date:
                return first_date
            else:
                return last_call + relativedelta(years=-1, month=second_month, day=self.second_month_day)
        elif self.frequency == 'yearly':
            month = MONTHS.index(self.yearly_month) + 1
            year_date = last_call + relativedelta(month=month, day=self.yearly_day)
            if last_call >= year_date:
                return year_date
            else:
                return last_call + relativedelta(years=-1, month=month, day=self.yearly_day)
        else:
            return False

    def _get_level_transition_date(self, allocation_start):
        if self.start_type == 'day':
            return allocation_start + relativedelta(days=self.start_count)
        if self.start_type == 'month':
            return allocation_start + relativedelta(months=self.start_count)
        if self.start_type == 'year':
            return allocation_start + relativedelta(years=self.start_count)

    def action_save_new(self):
        return self.accrual_plan_id.action_create_accrual_plan_level()
