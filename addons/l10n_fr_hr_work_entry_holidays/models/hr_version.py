from collections import defaultdict
from datetime import UTC

from odoo import models
from odoo.libs.datetime import timezone
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrVersion(models.Model):
    _inherit = "hr.version"

    def _prepare_version_work_entries_values(self, date_start, date_stop):
        # Add the work entries difference for french payroll
        # Work entries by default are not generated on days the employee does not work
        # So we have to fill the gaps with work entries for those periods
        result = super()._prepare_version_work_entries_values(date_start, date_stop)
        fr_contracts = self.filtered(
            lambda c: (
                c.company_id.country_id.code == "FR"
                and c.resource_calendar_id != c.company_id.resource_calendar_id
            )
        )
        if not fr_contracts:
            _debug.logic(
                "fr_work_entry_gap_skipped",
                reason="no_french_part_time_version",
                versions=self,
            )
            return result
        start_dt = (
            date_start.replace(tzinfo=UTC) if not date_start.tzinfo else date_start
        )
        end_dt = date_stop.replace(tzinfo=UTC) if not date_stop.tzinfo else date_stop
        # l10n_fr_date_to_changed is False when no adjustment had to be done
        all_leaves = self.env["hr.leave"].search(
            [
                ("employee_id", "in", fr_contracts.employee_id.ids),
                ("state", "=", "validate"),
                ("date_from", "<=", end_dt.astimezone(UTC).replace(tzinfo=None)),
                ("date_to", ">=", start_dt.astimezone(UTC).replace(tzinfo=None)),
                ("l10n_fr_date_to_changed", "=", True),
            ]
        )
        leaves_per_employee = defaultdict(lambda: self.env["hr.leave"])
        for leave in all_leaves:
            leaves_per_employee[leave.employee_id] |= leave
        _debug.pipeline(
            "fr_work_entry_gap_start",
            versions=self,
            french=fr_contracts,
            adjusted_leaves=all_leaves,
            employees=len(leaves_per_employee),
            entries_so_far=len(result),
        )
        for contract in fr_contracts:
            employee = contract.employee_id
            company = contract.company_id
            company_calendar = company.resource_calendar_id
            resource = employee.resource_id
            tz = timezone(resource.tz)

            for leave in leaves_per_employee[employee]:
                leave_start_dt = max(start_dt, leave.date_from.astimezone(tz))
                leave_end_dt_fr = min(end_dt, leave.date_to.astimezone(tz))

                # Compute the attendances for the company calendar and the employee calendar
                # and then compute and keep the difference between those two
                company_attendances = company_calendar._attendance_intervals_batch(
                    leave_start_dt,
                    leave_end_dt_fr,
                    resources=resource,
                    tz=tz,
                )[resource.id]
                # Dates on which work entries should already be generated
                employee_dates = set()
                for vals in result:
                    employee_dates.add(vals["date_start"].date())
                    employee_dates.add(vals["date_stop"].date())
                leave_work_entry_type = leave.holiday_status_id.work_entry_type_id
                result += [
                    {
                        "name": "%s%s"
                        % (
                            leave_work_entry_type.name + ": "
                            if leave_work_entry_type
                            else "",
                            employee.name,
                        ),
                        "date_start": interval[0].astimezone(UTC).replace(tzinfo=None),
                        "date_stop": interval[1].astimezone(UTC).replace(tzinfo=None),
                        "work_entry_type_id": leave_work_entry_type.id,
                        "employee_id": employee.id,
                        "company_id": contract.company_id.id,
                        "state": "draft",
                        "version_id": contract.id,
                        "leave_id": leave.id,
                    }
                    for interval in company_attendances
                    if interval[0].date() not in employee_dates
                ]
                _debug.perf.count(
                    "fr_work_entry_gap_filled",
                    leave=leave,
                    employee=employee,
                    company_intervals=len(company_attendances),
                    already_covered_dates=len(employee_dates),
                    entries_total=len(result),
                )

        _debug.pipeline("fr_work_entry_gap_done", versions=self, entries=len(result))
        return result
