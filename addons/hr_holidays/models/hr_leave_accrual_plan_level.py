# Part of Odoo. See LICENSE file for full copyright and licensing details.
from calendar import monthrange
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


def _get_selection_days(self):
    return [(str(i), str(i)) for i in range(1, 32)]


class HrLeaveAccrualLevel(models.Model):
    _name = 'hr.leave.accrual.level'
    _description = "Accrual Plan Level"
    _order = 'sequence asc'

    sequence = fields.Integer(
        string='sequence', compute='_compute_sequence', store=True,
        help='Sequence is generated automatically by start time delta.')
    accrual_plan_id = fields.Many2one('hr.leave.accrual.plan', "Accrual Plan", required=True, index=True, ondelete="cascade", default=lambda self: self.env.context.get("active_id", None))
    accrued_gain_time = fields.Selection(related='accrual_plan_id.accrued_gain_time', export_string_translation=False)
    start_count = fields.Integer(export_string_translation=False,
        help="The accrual starts after a defined period from the allocation start date. This field defines the number of days, months or years after which accrual is used.")
    start_type = fields.Selection(
        [('day', 'Days'),
         ('month', 'Months'),
         ('year', 'Years')],
        default='day', required=True, export_string_translation=False,
        help="This field defines the unit of time after which the accrual starts.")
    milestone_date = fields.Selection(
        [('creation', 'At allocation creation'),
         ('after', 'After')],
        compute='_compute_milestone_date', inverse='_inverse_milestone_date', readonly=False,
        store=True, export_string_translation=False,
        default='creation', required=True
    )
    # Accrue of
    added_value = fields.Float(digits=(16, 5), required=True, default=1, export_string_translation=False)
    added_value_type = fields.Selection([
        ('day', 'Day(s)'),
        ('hour', 'Hour(s)')
    ], compute="_compute_added_value_type", inverse="_inverse_added_value_type", precompute=True, store=True, required=True,
        readonly=False, export_string_translation=False)
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
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday'),
    ], default='0', required=True, string="Allocation on")
    first_day = fields.Selection(_get_selection_days, default='1', export_string_translation=False)
    second_day = fields.Selection(_get_selection_days, default='15', export_string_translation=False)
    first_month_day = fields.Selection(
        _get_selection_days, compute='_compute_first_month_day', store=True, readonly=False, default='1',
        export_string_translation=False)
    first_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
    ], default="1", export_string_translation=False)
    second_month_day = fields.Selection(
        _get_selection_days, compute='_compute_second_month_day', store=True, readonly=False, default='1',
        export_string_translation=False)
    second_month = fields.Selection([
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ], default="7", export_string_translation=False)
    yearly_month = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')
    ], default="1", export_string_translation=False)
    yearly_day = fields.Selection(
        _get_selection_days, compute='_compute_yearly_day', store=True, readonly=False, default='1',
        export_string_translation=False)
    cap_accrued_time = fields.Boolean(export_string_translation=False,
        help="When the field is checked the balance of an allocation using this accrual plan will never exceed the specified amount.")
    maximum_leave = fields.Float(
        digits=(16, 2), compute="_compute_maximum_leave", default=0, readonly=False, store=True,
        help="Choose a cap for this accrual.", export_string_translation=False)
    cap_accrued_time_yearly = fields.Boolean(export_string_translation=False,
        store=True, readonly=False,
        help="When the field is checked the total amount accrued each year will be capped at the specified amount")
    maximum_leave_yearly = fields.Float(digits=(16, 2), export_string_translation=False)
    can_be_carryover = fields.Boolean(related='accrual_plan_id.can_be_carryover', readonly=True,
        export_string_translation=False)
    action_with_unused_accruals = fields.Selection(
        [('lost', 'Lost'),
         ('all', 'Carried over')],
        compute="_compute_action_with_unused_accruals",
        store=True,
        export_string_translation=False,
        default='lost', required=True,
        help="When the Carry-Over Time is reached, according to Plan's setting, select what you want "
        "to happen with the unused time off: Lost (time will be reset to zero), Carried over (accrued time carried over to "
        "the next period.)")
    carryover_options = fields.Selection(
        [('unlimited', 'Unlimited'),
         ('limited', 'Up to')],
        store=True, readonly=False,
        export_string_translation=False,
        compute="_compute_carryover_options",
        default='unlimited', required=True,
        help="You can limit the accrued time carried over for the next period."
    )
    postpone_max_days = fields.Integer(export_string_translation=False,
        help="Set a maximum of accruals an allocation keeps at the end of the year.")
    can_modify_value_type = fields.Boolean(compute="_compute_can_modify_value_type", default=False,
        export_string_translation=False)
    accrual_validity = fields.Boolean(export_string_translation=False, compute="_compute_accrual_validity", store=True, readonly=False)
    accrual_validity_count = fields.Integer(
        export_string_translation=False,
        help="You can define a period of time where the days carried over will be available", default="1")
    accrual_validity_type = fields.Selection(
        [('day', 'Days'),
         ('month', 'Months')],
        default='day', export_string_translation=False, required=True,
        help="This field defines the unit of time after which the accrual ends.")

    _start_count_check = models.Constraint(
        "CHECK((start_count > 0 AND milestone_date = 'after') OR (start_count = 0 AND milestone_date = 'creation'))",
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

    @api.constrains('first_day', 'second_day', 'week_day', 'frequency')
    def _check_dates(self):
        error_message = ''
        for level in self:
            if level.frequency == 'weekly' and not level.week_day:
                error_message = _("Weekday must be selected to use the frequency weekly")
            elif level.frequency == 'bimonthly' and int(level.first_day) >= int(level.second_day):
                error_message = _("The first day must be lower than the second day.")
        if error_message:
            raise ValidationError(error_message)

    @api.constrains('cap_accrued_time', 'maximum_leave')
    def _check_maximum_leaves(self):
        for level in self:
            if level.cap_accrued_time and level.maximum_leave <= 0:
                raise UserError(self.env._("You cannot have a balance cap on accrued time set to 0."))

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
            elif not level.added_value_type:
                level.added_value_type = "day"  # default value

    def _set_day(self, day_field, month_field):
        for level in self:
            # 2020 is a leap year, so monthrange(2020, february) will return [2, 29]
            level[day_field] = str(min(monthrange(2020, int(level[month_field]))[1], int(level[day_field])))

    @api.depends("first_month")
    def _compute_first_month_day(self):
        self._set_day("first_month_day", "first_month")

    @api.depends("second_month")
    def _compute_second_month_day(self):
        self._set_day("second_month_day", "second_month")

    @api.depends("yearly_month")
    def _compute_yearly_day(self):
        self._set_day("yearly_day", "yearly_month")

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

    @api.depends('start_count', 'milestone_date')
    def _compute_milestone_date(self):
        for level in self:
            if level.start_count == 0:
                level.milestone_date = 'creation'

    def _inverse_milestone_date(self):
        for level in self:
            if level.milestone_date == 'creation':
                level.start_count = 0

    def _get_hourly_frequencies(self):
        return ['hourly']

    def _get_next_date(self, last_call):
        """
        Returns the next date with the given last call
        """
        self.ensure_one()
        if self.frequency in self._get_hourly_frequencies() + ['daily']:
            return last_call + relativedelta(days=1)

        if self.frequency == 'weekly':
            return last_call + relativedelta(days=1, weekday=int(self.week_day))

        if self.frequency == 'bimonthly':
            first_date = last_call + relativedelta(day=int(self.first_day))
            second_date = last_call + relativedelta(day=int(self.second_day))
            if last_call < first_date:
                return first_date
            if last_call < second_date:
                return second_date
            return last_call + relativedelta(day=int(self.first_day), months=1)

        if self.frequency == 'monthly':
            date = last_call + relativedelta(day=int(self.first_day))
            if last_call < date:
                return date
            return last_call + relativedelta(day=int(self.first_day), months=1)

        if self.frequency == 'biyearly':
            first_date = last_call + relativedelta(month=int(self.first_month), day=int(self.first_month_day))
            second_date = last_call + relativedelta(month=int(self.second_month), day=int(self.second_month_day))
            if last_call < first_date:
                return first_date
            if last_call < second_date:
                return second_date
            return last_call + relativedelta(month=int(self.first_month), day=int(self.first_month_day), years=1)

        if self.frequency == 'yearly':
            date = last_call + relativedelta(month=int(self.yearly_month), day=int(self.yearly_day))
            if last_call < date:
                return date
            return last_call + relativedelta(month=int(self.yearly_month), day=int(self.yearly_day), years=1)

        raise ValidationError(_("Your frequency selection is not correct: please choose a frequency between theses options:"
            "Hourly, Daily, Weekly, Twice a month, Monthly, Twice a year and Yearly."))

    def _get_previous_date(self, last_call):
        """
        Returns the date a potential previous call would have been at
        For example if you have a monthly level giving 16/02 would return 01/02
        Contrary to `_get_next_date` this function will return the 01/02 if that date is given
        """
        self.ensure_one()
        if self.frequency in self._get_hourly_frequencies() + ['daily']:
            return last_call

        if self.frequency == 'weekly':
            return last_call + relativedelta(days=-6, weekday=int(self.week_day))

        if self.frequency == 'bimonthly':
            first_date = last_call + relativedelta(day=int(self.first_day))
            second_date = last_call + relativedelta(day=int(self.second_day))
            if last_call >= second_date:
                return second_date
            if last_call >= first_date:
                return first_date
            return last_call + relativedelta(day=int(self.second_day), months=-1)

        if self.frequency == 'monthly':
            date = last_call + relativedelta(day=int(self.first_day))
            if last_call >= date:
                return date
            return last_call + relativedelta(day=int(self.first_day), months=-1, days=1)

        if self.frequency == 'biyearly':
            first_date = last_call + relativedelta(month=int(self.first_month), day=int(self.first_month_day))
            second_date = last_call + relativedelta(month=int(self.second_month), day=int(self.second_month_day))
            if last_call >= second_date:
                return second_date
            if last_call >= first_date:
                return first_date
            return last_call + relativedelta(month=int(self.second_month), day=int(self.second_month_day), years=-1)

        if self.frequency == 'yearly':
            year_date = last_call + relativedelta(month=int(self.yearly_month), day=int(self.yearly_day))
            if last_call >= year_date:
                return year_date
            return last_call + relativedelta(month=int(self.yearly_month), day=int(self.yearly_day), years=-1)

        raise ValidationError(_("Your frequency selection is not correct: please choose a frequency between theses options:"
            "Hourly, Daily, Weekly, Twice a month, Monthly, Twice a year and Yearly."))

    def _get_level_transition_date(self, allocation_start):
        if self.start_type == 'day':
            return allocation_start + relativedelta(days=self.start_count)
        if self.start_type == 'month':
            return allocation_start + relativedelta(months=self.start_count)
        if self.start_type == 'year':
            return allocation_start + relativedelta(years=self.start_count)

    def action_save_new(self):
        return self.accrual_plan_id.action_create_accrual_plan_level()
