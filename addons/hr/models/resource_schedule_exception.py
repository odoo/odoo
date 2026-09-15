from datetime import UTC, datetime, timedelta

from odoo import api, models
from odoo.libs.datetime import timezone

from ..tools import debug_log as dbg


class ResourceScheduleException(models.Model):
    _inherit = "resource.schedule.exception"

    @api.depends("date_from")
    def _compute_calendar_id(self):
        def date_to_datetime(date, tz):
            dt = datetime.fromordinal(date.toordinal())
            return dt.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)

        leaves_by_contract = self.grouped(
            lambda leave: leave.resource_id.employee_id[:1].version_id
        )
        remaining = leaves_by_contract.pop(
            self.env["hr.version"],
            self.env["resource.schedule.exception"],
        )
        dbg.logic.debug(
            "resource.schedule.exception._compute_calendar_id on %s: %d contract "
            "group(s), %s without a contract",
            dbg.rec(self),
            len(leaves_by_contract),
            dbg.rec(remaining),
        )
        for contract, leaves in leaves_by_contract.items():
            tz = timezone(
                contract.employee_id.tz or contract.resource_calendar_id.tz or "UTC"
            )
            start_dt = date_to_datetime(contract.date_start, tz)
            end_dt = (
                date_to_datetime(contract.date_end + timedelta(days=1), tz)
                if contract.date_end
                else datetime.max  # noqa: DTZ901 - naive sentinel, compared only
            )
            in_contract = leaves.filtered(
                lambda leave, start_dt=start_dt, end_dt=end_dt: (
                    leave.date_from and start_dt <= leave.date_from < end_dt
                )
            )
            dbg.logic.debug(
                "[version:%s] %s of %s fall in %s..%s, calendar -> %s",
                contract.id,
                dbg.rec(in_contract),
                dbg.rec(leaves),
                start_dt,
                end_dt,
                contract.resource_calendar_id.id,
            )
            in_contract.calendar_id = contract.resource_calendar_id

        super(ResourceScheduleException, remaining)._compute_calendar_id()
