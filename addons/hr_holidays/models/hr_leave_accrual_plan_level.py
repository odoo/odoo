from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.date_utils import get_timedelta

# The user-facing cadence choice, over what is stored: a period, whether it has a
# second anchor, and whether the accrued amount is per period or per hour.
FREQUENCY_CADENCE = {
    "hourly": ("day", False, "hour"),
    "daily": ("day", False, "period"),
    "weekly": ("week", False, "period"),
    "bimonthly": ("month", True, "period"),
    "monthly": ("month", False, "period"),
    "biyearly": ("year", True, "period"),
    "yearly": ("year", False, "period"),
}


class HrLeaveAccrualLevel(models.Model):
    _name = "hr.leave.accrual.level"
    _inherit = ["mixin.recurrence.anchored"]
    _description = "Accrual Plan Level"
    _order = "sequence asc"

    sequence = fields.Integer(
        string="sequence",
        compute="_compute_sequence",
        store=True,
        help="Sequence is generated automatically by start time delta.",
    )
    accrual_plan_id = fields.Many2one(
        comodel_name="hr.leave.accrual.plan",
        default=lambda self: self.env.context.get("active_id", None),
        index=True,
        required=True,
        ondelete="cascade",
    )
    is_based_on_worked_time = fields.Boolean(
        related="accrual_plan_id.is_based_on_worked_time",
        export_string_translation=False,
    )
    accrued_gain_time = fields.Selection(
        related="accrual_plan_id.accrued_gain_time",
        export_string_translation=False,
    )
    start_count = fields.Integer(
        export_string_translation=False,
        help="The accrual starts after a defined period from the allocation start date. This field defines the number of days, months or years after which accrual is used.",
    )
    start_type = fields.Selection(
        selection=[("day", "Days"), ("month", "Months"), ("year", "Years")],
        export_string_translation=False,
        default="day",
        required=True,
        help="This field defines the unit of time after which the accrual starts.",
    )
    milestone_date = fields.Selection(
        selection=[("creation", "At allocation creation"), ("after", "After")],
        export_string_translation=False,
        compute="_compute_milestone_date",
        inverse="_inverse_milestone_date",
        default="creation",
        store=True,
        readonly=False,
        required=True,
    )
    added_value = fields.Float(
        export_string_translation=False,
        digits=(16, 5),
        default=1,
        required=True,
    )
    added_value_type = fields.Selection(
        selection=[("day", "Day(s)"), ("hour", "Hour(s)")],
        export_string_translation=False,
        compute="_compute_added_value_type",
        inverse="_inverse_added_value_type",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    accrual_basis = fields.Selection(
        selection=[("period", "Per Period"), ("hour", "Per Hour")],
        export_string_translation=False,
        default="period",
        required=True,
        help="Whether the added value is granted once per period or for each hour"
        " planned in it.",
    )
    frequency = fields.Selection(
        selection=[
            ("hourly", "Hourly"),
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("bimonthly", "Twice a month"),
            ("monthly", "Monthly"),
            ("biyearly", "Twice a year"),
            ("yearly", "Yearly"),
        ],
        compute="_compute_frequency",
        inverse="_inverse_frequency",
    )
    cap_accrued_time = fields.Boolean(
        export_string_translation=False,
        help="When the field is checked the balance of an allocation using this accrual plan will never exceed the specified amount.",
    )
    maximum_leave = fields.Float(
        export_string_translation=False,
        digits=(16, 2),
        compute="_compute_maximum_leave",
        default=0,
        store=True,
        readonly=False,
        help="Choose a cap for this accrual.",
    )
    cap_accrued_time_yearly = fields.Boolean(
        export_string_translation=False,
        store=True,
        readonly=False,
        help="When the field is checked the total amount accrued each year will be capped at the specified amount",
    )
    maximum_leave_yearly = fields.Float(
        export_string_translation=False,
        digits=(16, 2),
    )
    yearly_gain = fields.Float(
        compute="_compute_yearly_gain",
        export_string_translation=False,
    )
    can_be_carryover = fields.Boolean(
        related="accrual_plan_id.can_be_carryover",
        export_string_translation=False,
        readonly=True,
    )
    action_with_unused_accruals = fields.Selection(
        selection=[("lost", "Lost"), ("all", "Carried over")],
        export_string_translation=False,
        compute="_compute_action_with_unused_accruals",
        default="lost",
        store=True,
        # The compute only forces "lost" when carry-over is off; the rest of the
        # time this is the user's choice in the form.  Without readonly=False the
        # ORM reports it readonly and the import-compatible export drops it, so a
        # reimported plan loses what happens to unused time.
        readonly=False,
        required=True,
        help="When the Carry-Over Time is reached, according to Plan's setting, select what you want "
        "to happen with the unused time off: Lost (time will be reset to zero), Carried over (accrued time carried over to "
        "the next period.)",
    )
    carryover_options = fields.Selection(
        selection=[("unlimited", "Unlimited"), ("limited", "Up to")],
        export_string_translation=False,
        compute="_compute_carryover_options",
        default="unlimited",
        store=True,
        readonly=False,
        required=True,
        help="You can limit the accrued time carried over for the next period.",
    )
    postpone_max_days = fields.Integer(
        export_string_translation=False,
        help="Set a maximum of accruals an allocation keeps at the end of the year.",
    )
    can_modify_value_type = fields.Boolean(
        export_string_translation=False,
        compute="_compute_can_modify_value_type",
        default=False,
    )
    accrual_validity = fields.Boolean(
        export_string_translation=False,
        compute="_compute_accrual_validity",
        store=True,
        readonly=False,
    )
    accrual_validity_count = fields.Integer(
        export_string_translation=False,
        default="1",
        help="You can define a period of time where the days carried over will be available",
    )
    accrual_validity_type = fields.Selection(
        selection=[("day", "Days"), ("month", "Months")],
        export_string_translation=False,
        default="day",
        required=True,
        help="This field defines the unit of time after which the accrual ends.",
    )

    _start_count_check = models.Constraint(
        "CHECK((start_count > 0 AND milestone_date = 'after') OR (start_count = 0 AND milestone_date = 'creation'))",
        "You can not start an accrual in the past.",
    )
    _added_value_greater_than_zero = models.Constraint(
        "CHECK(added_value > 0)",
        "You must give a rate greater than 0 in accrual plan levels.",
    )
    _valid_postpone_max_days_value = models.Constraint(
        "CHECK(action_with_unused_accruals <> 'all' OR carryover_options <> 'limited' OR COALESCE(postpone_max_days, 0) > 0)",
        "You cannot have a maximum quantity to carryover set to 0.",
    )
    _valid_accrual_validity_value = models.Constraint(
        "CHECK(accrual_validity IS NOT TRUE OR COALESCE(accrual_validity_count, 0) > 0)",
        "You cannot have an accrual validity time set to 0.",
    )
    _valid_yearly_cap_value = models.Constraint(
        "CHECK(cap_accrued_time_yearly IS NOT TRUE OR COALESCE(maximum_leave_yearly, 0) > 0)",
        "You cannot have a cap on yearly accrued time without setting a maximum amount.",
    )

    @api.constrains("cap_accrued_time", "maximum_leave")
    def _check_maximum_leaves(self):
        for level in self:
            if level.cap_accrued_time and level.maximum_leave <= 0:
                raise ValidationError(
                    self.env._(
                        "You cannot have a balance cap on accrued time set to 0."
                    )
                )

    @api.depends("start_count", "start_type")
    def _compute_sequence(self):
        # Approximate day-equivalents for list ordering only; the actual
        # transition date uses real calendar arithmetic (see
        # _get_level_transition_date), so a tie/inversion here only affects
        # display order, never accrual dates.
        start_type_multipliers = {
            "day": 1,
            "month": 30,
            "year": 365,
        }
        for level in self:
            level.sequence = (
                level.start_count * start_type_multipliers[level.start_type]
            )

    @api.depends(
        "accrual_plan_id",
        "accrual_plan_id.level_ids",
        "accrual_plan_id.time_off_type_id",
    )
    def _compute_can_modify_value_type(self):
        for level in self:
            level.can_modify_value_type = (
                not level.accrual_plan_id.time_off_type_id
                and level.accrual_plan_id.level_ids
                and level.accrual_plan_id.level_ids[0] == level
            )

    def _inverse_added_value_type(self):
        for level in self:
            if (
                level.accrual_plan_id.level_ids
                and level.accrual_plan_id.level_ids[0] == level
            ):
                level.accrual_plan_id.added_value_type = level.added_value_type

    @api.depends(
        "accrual_plan_id",
        "accrual_plan_id.level_ids",
        "accrual_plan_id.added_value_type",
        "accrual_plan_id.time_off_type_id",
    )
    def _compute_added_value_type(self):
        for level in self:
            if level.accrual_plan_id.time_off_type_id:
                level.added_value_type = (
                    "day"
                    if level.accrual_plan_id.time_off_type_id.request_unit
                    in ["day", "half_day"]
                    else "hour"
                )
            elif (
                level.accrual_plan_id.level_ids
                and level.accrual_plan_id.level_ids[0] != level
            ):
                level.added_value_type = level.accrual_plan_id.level_ids[
                    0
                ].added_value_type
            elif not level.added_value_type:
                level.added_value_type = "day"

    def _get_frequency_cadences(self):
        return FREQUENCY_CADENCE

    @api.depends("repeat_unit", "repeat_twice", "accrual_basis")
    def _compute_frequency(self):
        by_cadence = {
            cadence: code for code, cadence in self._get_frequency_cadences().items()
        }
        for level in self:
            level.frequency = by_cadence.get(
                (level.repeat_unit, level.repeat_twice, level.accrual_basis)
            )

    def _inverse_frequency(self):
        cadences = self._get_frequency_cadences()
        for level in self:
            if level.frequency in cadences:
                (
                    level.repeat_unit,
                    level.repeat_twice,
                    level.accrual_basis,
                ) = cadences[level.frequency]

    @api.depends("cap_accrued_time")
    def _compute_maximum_leave(self):
        for level in self:
            if not level.cap_accrued_time:
                level.maximum_leave = 0

    @api.depends("frequency", "added_value", "is_based_on_worked_time")
    def _compute_yearly_gain(self):
        company_calendar = self.env.company.resource_calendar_id
        hours_per_week = company_calendar.hours_per_week
        days_per_week = company_calendar._get_days_per_week()
        for level in self:
            if level.frequency == "hourly":
                gain = level.added_value * 52 * hours_per_week
            elif level.frequency == "daily":
                # Accruing on worked time only credits the days actually worked;
                # otherwise every day of the year counts.
                if level.is_based_on_worked_time:
                    gain = level.added_value * 52 * days_per_week
                else:
                    gain = level.added_value * 365
            elif level.frequency == "weekly":
                gain = level.added_value * 52
            elif level.frequency == "bimonthly":
                gain = level.added_value * 24
            elif level.frequency == "monthly":
                gain = level.added_value * 12
            elif level.frequency == "biyearly":
                gain = level.added_value * 2
            elif level.frequency == "yearly":
                gain = level.added_value
            else:
                gain = 0
            level.yearly_gain = gain

    @api.depends("can_be_carryover")
    def _compute_action_with_unused_accruals(self):
        for level in self:
            if not level.can_be_carryover:
                level.action_with_unused_accruals = "lost"

    @api.depends("action_with_unused_accruals")
    def _compute_carryover_options(self):
        for level in self:
            if level.action_with_unused_accruals == "lost":
                level.carryover_options = "unlimited"

    @api.depends("action_with_unused_accruals")
    def _compute_accrual_validity(self):
        for level in self:
            if level.action_with_unused_accruals == "lost":
                level.accrual_validity = False

    @api.depends("start_count", "milestone_date")
    def _compute_milestone_date(self):
        for level in self:
            if level.start_count == 0:
                level.milestone_date = "creation"

    def _inverse_milestone_date(self):
        for level in self:
            if level.milestone_date == "creation":
                level.start_count = 0

    def _get_hourly_bases(self):
        return ["hour"]

    def _get_level_transition_date(self, allocation_start):
        return allocation_start + get_timedelta(self.start_count, self.start_type)

    def action_save_new(self):
        return self.accrual_plan_id.action_create_accrual_plan_level()
