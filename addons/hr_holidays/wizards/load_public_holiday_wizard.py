import csv
from collections import defaultdict
from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from markupsafe import Markup, escape

from odoo import Command, api, fields, models
from odoo.tools import file_open, file_path

# The data files only go so far into the future; anything outside this is a
# typo rather than a request.
FIRST_YEAR = 2026
LAST_YEAR = 2050


class LoadPublicHolidayWizard(models.TransientModel):
    _name = "load.public.holiday.wizard"
    _description = "Load Public Holidays"

    year = fields.Integer(
        required=True, default=lambda self: fields.Date.context_today(self).year
    )
    warning_message = fields.Html(compute="_compute_warning_message")
    line_ids = fields.One2many(
        "load.public.holiday.wizard.line",
        "wizard_id",
        string="Public Holidays",
        compute="_compute_line_ids",
        store=True,
        readonly=False,
    )

    @api.depends("year")
    def _compute_warning_message(self):
        for wizard in self:
            messages = wizard._get_warning_messages(wizard._prepare_public_holidays())
            wizard.warning_message = messages and Markup(
                '<ul class="mb-0">%s</ul>'
            ) % Markup("").join(Markup("<li>%s</li>") % escape(m) for m in messages)

    @api.depends("year")
    def _compute_line_ids(self):
        for wizard in self:
            commands = [Command.clear()]
            prepared = wizard._prepare_public_holidays()
            commands.extend(
                Command.create(values)
                for company_values in prepared["holidays_by_company"].values()
                for values in company_values
            )
            wizard.line_ids = commands

    def _companies(self):
        return self.env.companies

    def _existing_holidays(self, companies):
        """Public holidays already covering the wizard's year, per company."""
        return dict(
            self.env["resource.schedule.exception"]._read_group(
                domain=[
                    ("company_id", "in", companies.ids),
                    ("resource_id", "=", False),
                    ("date_from", "<=", datetime(self.year, 12, 31, 23, 59, 59)),
                    ("date_to", ">=", datetime(self.year, 1, 1)),
                ],
                groupby=["company_id"],
                aggregates=["id:recordset"],
            )
        )

    def _company_day_bounds(self, company, day):
        """The UTC instants that bracket `day` as the company lives it.

        A public holiday is a whole working day for everyone in the company, so
        the timezone that decides where that day starts and ends is the one of
        the company's working schedule -- res.company itself carries none here.
        """
        company_tz = ZoneInfo(
            company.resource_calendar_id.tz or self.env.user.tz or "UTC"
        )
        start = datetime.combine(day, time.min).replace(tzinfo=company_tz)
        # Second precision, like every other public holiday in the module: a
        # Datetime column keeps no microseconds anyway.
        stop = datetime.combine(day, time.max.replace(microsecond=0)).replace(
            tzinfo=company_tz
        )
        return (
            start.astimezone(UTC).replace(tzinfo=None),
            stop.astimezone(UTC).replace(tzinfo=None),
        )

    def _prepare_public_holidays(self):
        self.ensure_one()
        companies = self._companies()
        holidays_by_company = {}
        without_country = self.env["res.company"]
        without_data = self.env["res.company"]
        already_complete = self.env["res.company"]

        if not (self.year and FIRST_YEAR <= self.year <= LAST_YEAR):
            return {
                "holidays_by_company": holidays_by_company,
                "without_country": without_country,
                "without_data": without_data,
                "already_complete": already_complete,
            }

        existing = self._existing_holidays(companies)
        for company in companies:
            if not company.country_code:
                without_country |= company
                continue
            try:
                data_file = file_path(
                    "hr_holidays/data/public_holidays/public_holidays_%s.csv"
                    % company.country_code.lower()
                )
            except FileNotFoundError:
                without_data |= company
                continue

            values_by_day = {}
            has_rows = False
            with file_open(data_file) as data:
                for row in csv.DictReader(data):
                    if not row.get("date") or not row.get("holiday"):
                        continue
                    day = datetime.strptime(row["date"], "%Y-%m-%d").date()
                    if day.year > self.year:
                        break
                    if day.year != self.year:
                        continue

                    has_rows = True
                    start, stop = self._company_day_bounds(company, day)
                    if any(
                        holiday.date_from <= stop and holiday.date_to >= start
                        for holiday in existing.get(company, [])
                    ):
                        continue

                    name = row["holiday"].strip()
                    if day in values_by_day:
                        # Two holidays on one day read better joined than as two
                        # overlapping records, which our own constraint refuses.
                        values_by_day[day]["name"] += " / %s" % name
                    else:
                        values_by_day[day] = {
                            "name": name,
                            "start_date": day,
                            "company_id": company.id,
                        }

            if values_by_day:
                holidays_by_company[company.id] = list(values_by_day.values())
            elif has_rows:
                already_complete |= company
            else:
                without_data |= company

        return {
            "holidays_by_company": holidays_by_company,
            "without_country": without_country,
            "without_data": without_data,
            "already_complete": already_complete,
        }

    def _get_warning_messages(self, prepared):
        self.ensure_one()
        messages = []
        if prepared["already_complete"]:
            messages.append(
                self.env._(
                    "Every public holiday for %(year)s is already there for: %(companies)s.",
                    year=self.year,
                    companies=", ".join(prepared["already_complete"].mapped("name")),
                )
            )
        if prepared["without_country"]:
            messages.append(
                self.env._(
                    "These companies have no country set: %(companies)s.",
                    companies=", ".join(prepared["without_country"].mapped("name")),
                )
            )
        if prepared["without_data"]:
            messages.append(
                self.env._(
                    "No public holiday data is available for %(year)s for: %(companies)s.",
                    year=self.year,
                    companies=", ".join(prepared["without_data"].mapped("name")),
                )
            )
        return messages

    def _get_create_values(self):
        self.ensure_one()
        companies = self._companies()
        values_by_company = defaultdict(list)
        for line in self.line_ids:
            if line.company_id not in companies:
                continue
            date_from, date_to = self._company_day_bounds(
                line.company_id, line.start_date
            )
            values_by_company[line.company_id].append(
                {
                    "name": line.name,
                    "date_from": date_from,
                    "date_to": date_to,
                    "company_id": line.company_id.id,
                }
            )
        return values_by_company

    def action_add_public_holidays(self):
        self.ensure_one()
        messages = []
        for company, values in self._get_create_values().items():
            created = self.env["resource.schedule.exception"].create(values)
            if created:
                messages.append(
                    self.env._(
                        "Created %(count)s public holiday(s) for %(company)s.",
                        count=len(created),
                        company=company.name,
                    )
                )
        warnings = self._get_warning_messages(self._prepare_public_holidays())
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success" if messages and not warnings else "warning",
                "message": "\n".join(messages + warnings)
                or self.env._("No public holiday was added."),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
