from collections import defaultdict
from datetime import timedelta
from itertools import groupby

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrWorkEntryRegenerationWizard(models.TransientModel):
    _name = "hr.work.entry.regeneration.wizard"
    _description = "Regenerate Employee Work Entries"

    earliest_available_date = fields.Date(
        string="Earliest date",
        compute="_compute_available_dates",
    )
    earliest_available_date_message = fields.Char(
        default="",
        store=False,
        readonly=True,
    )
    latest_available_date = fields.Date(
        string="Latest date",
        compute="_compute_available_dates",
    )
    latest_available_date_message = fields.Char(
        default="",
        store=False,
        readonly=True,
    )
    date_from = fields.Date(
        string="From",
        default=lambda self: self.env.context.get("date_start"),
        required=True,
    )
    date_to = fields.Date(
        string="To",
        compute="_compute_date_to",
        default=lambda self: self.env.context.get("date_end"),
        store=True,
        readonly=False,
        required=True,
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
        required=True,
        domain=lambda self: [("company_id", "in", self.env.companies.ids)],
    )
    validated_work_entry_employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        export_string_translation=False,
        compute="_compute_validated_work_entry_employee_ids",
    )
    search_criteria_completed = fields.Boolean(
        compute="_compute_search_criteria_completed"
    )
    valid = fields.Boolean(compute="_compute_valid")

    @api.depends("date_from")
    def _compute_date_to(self):
        for wizard in self:
            wizard.date_to = wizard.date_from and wizard.date_from + relativedelta(
                months=+1, day=1, days=-1
            )

    @api.depends("employee_ids")
    def _compute_available_dates(self):
        for wizard in self:
            versions = wizard.employee_ids.version_ids
            generated_from = versions.mapped("date_generated_from")
            generated_to = versions.mapped("date_generated_to")
            wizard.earliest_available_date = min(generated_from, default=None)
            wizard.latest_available_date = max(generated_to, default=None)

    @api.depends("date_from", "date_to", "employee_ids", "search_criteria_completed")
    def _compute_validated_work_entry_employee_ids(self):
        for wizard in self:
            employees = self.env["hr.employee"]
            if wizard.search_criteria_completed:
                for [employee] in self.env["hr.work.entry"]._read_group(  # noqa: E8507 - a transient wizard: one record
                    [
                        ("employee_id", "in", wizard.employee_ids.ids),
                        ("date", ">=", wizard.date_from),
                        ("date", "<=", wizard.date_to),
                        ("state", "=", "validated"),
                    ],
                    ["employee_id"],
                ):
                    employees |= employee
            wizard.validated_work_entry_employee_ids = employees

    @api.depends(
        "validated_work_entry_employee_ids",
        "employee_ids",
        "search_criteria_completed",
    )
    def _compute_valid(self):
        for wizard in self:
            wizard.valid = wizard.search_criteria_completed and bool(
                wizard.employee_ids - wizard.validated_work_entry_employee_ids
            )

    @api.depends(
        "date_from",
        "date_to",
        "employee_ids",
        "earliest_available_date",
        "latest_available_date",
    )
    def _compute_search_criteria_completed(self):
        for wizard in self:
            wizard.search_criteria_completed = bool(
                wizard.date_from
                and wizard.date_to
                and wizard.employee_ids
                and wizard.earliest_available_date
                and wizard.latest_available_date
            )

    @api.onchange("date_from", "date_to", "employee_ids")
    def _onchange_dates(self):
        for wizard in self:
            wizard.earliest_available_date_message = ""
            wizard.latest_available_date_message = ""
            if not wizard.search_criteria_completed:
                continue
            if wizard.date_from > wizard.date_to:
                wizard.date_from, wizard.date_to = wizard.date_to, wizard.date_from
            if wizard.date_from < wizard.earliest_available_date:
                wizard.date_from = wizard.earliest_available_date
                wizard.earliest_available_date_message = self.env._(
                    "The earliest available date is %s",
                    self._date_to_string(wizard.earliest_available_date),
                )
            if wizard.date_to > wizard.latest_available_date:
                wizard.date_to = wizard.latest_available_date
                wizard.latest_available_date_message = self.env._(
                    "The latest available date is %s",
                    self._date_to_string(wizard.latest_available_date),
                )

    @api.model
    def _date_to_string(self, date):
        if not date:
            return ""
        user_date_format = (
            self.env["res.lang"]._get_data(code=self.env.user.lang).date_format
        )
        return date.strftime(user_date_format)

    def _check_regeneration_range(self):
        self.check_singleton()
        if not self.search_criteria_completed:
            _debug.logic("regeneration_refused", reason="incomplete_criteria")
            raise ValidationError(
                self.env._(
                    "In order to regenerate the work entries, you need to provide the wizard with an employee_id, a date_from and a date_to."
                )
            )
        if (
            self.date_from < self.earliest_available_date
            or self.date_to > self.latest_available_date
        ):
            _debug.logic("regeneration_refused", reason="out_of_generated_range")
            raise ValidationError(
                self.env._(
                    "The from date must be >= '%(earliest_available_date)s' and the to date must be <= '%(latest_available_date)s', which correspond to the generated work entries time interval.",
                    earliest_available_date=self._date_to_string(
                        self.earliest_available_date
                    ),
                    latest_available_date=self._date_to_string(
                        self.latest_available_date
                    ),
                )
            )
        if not self.valid:
            _debug.logic("regeneration_refused", reason="nothing_regenerable")
            raise ValidationError(
                self.env._(
                    "No work entry can be regenerated in this range of dates and these employees."
                )
            )

    def _regenerate_wizard_range(self):
        self.check_singleton()
        if not self.env.context.get("work_entry_skip_validation"):
            self._check_regeneration_range()
        employees = self.employee_ids - self.validated_work_entry_employee_ids
        if not employees:
            _debug.logic(
                "regeneration_empty",
                reason="all_validated",
                employees=self.employee_ids,
            )
            return self.env["hr.work.entry"]
        date_from = max(filter(None, [self.date_from, self.earliest_available_date]))
        date_to = min(filter(None, [self.date_to, self.latest_available_date]))
        _debug.pipeline(
            "regeneration_wizard_range",
            employees=employees,
            date_from=str(date_from),
            date_to=str(date_to),
        )
        return employees.generate_work_entries(date_from, date_to, True)

    @api.model
    def _group_slots_into_ranges(self, slots):
        employee_ids_by_range = defaultdict(list)
        slots = sorted(slots, key=lambda d: (d["employee_id"], d["date"]))
        for employee_id, employee_slots in groupby(slots, lambda d: d["employee_id"]):
            dates = [fields.Date.to_date(slot["date"]) for slot in employee_slots]
            start = end = dates[0]
            for current in dates[1:]:
                if current - end != timedelta(days=1):
                    employee_ids_by_range[start, end].append(employee_id)
                    start = current
                end = current
            employee_ids_by_range[start, end].append(employee_id)
        return employee_ids_by_range

    @api.model
    def _filter_out_validated_slots(self, slots):
        if not slots:
            return slots
        employee_ids = {slot["employee_id"] for slot in slots}
        dates = [fields.Date.to_date(slot["date"]) for slot in slots]
        validated = (
            self.env["hr.work.entry"]
            .sudo()
            .search_fetch(
                [
                    ("employee_id", "in", list(employee_ids)),
                    ("date", ">=", min(dates)),
                    ("date", "<=", max(dates)),
                    ("state", "=", "validated"),
                ],
                ["employee_id", "date"],
            )
        )
        validated_pairs = {(w.employee_id.id, w.date) for w in validated}
        return [
            slot
            for slot in slots
            if (slot["employee_id"], fields.Date.to_date(slot["date"]))
            not in validated_pairs
        ]

    @api.model
    def _regenerate_slots(self, slots):
        work_entries = self.env["hr.work.entry"]
        slots = self._filter_out_validated_slots(slots)
        _debug.pipeline("regeneration_slots", slots=len(slots))
        for (date_from, date_to), employee_ids in self._group_slots_into_ranges(
            slots
        ).items():
            work_entries += (
                self.env["hr.employee"]
                .browse(employee_ids)
                .generate_work_entries(date_from, date_to, True)
            )
        return work_entries

    def regenerate_work_entries(self, slots=None):
        if slots:
            return self._regenerate_slots(slots)
        return self._regenerate_wizard_range()
