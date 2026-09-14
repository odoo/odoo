from datetime import UTC

from odoo import api, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrVersion(models.Model):
    _inherit = "hr.version"
    _description = "Employee Contract"

    def _get_leave_work_entry_type(self, leave):
        if leave.holiday_id:
            return leave.holiday_id.holiday_status_id.work_entry_type_id
        else:
            return leave.work_entry_type_id

    def _get_more_vals_leave_interval(self, interval, leaves):
        result = super()._get_more_vals_leave_interval(interval, leaves)
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1]:
                if leave[2].holiday_id.id:
                    result.append(("leave_id", leave[2].holiday_id.id))
                    break
        return result

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        self.check_singleton()
        if "work_entry_type_id" in interval[2]:
            work_entry_types = interval[2].work_entry_type_id
            if work_entry_types and work_entry_types[:1].code in bypassing_codes:
                return work_entry_types[:1]

        interval_start = interval[0].astimezone(UTC).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(UTC).replace(tzinfo=None)
        including_rcleaves = [
            l[2]
            for l in leaves
            if l[2]
            and interval_start >= l[2].date_from
            and interval_stop <= l[2].date_to
        ]
        including_global_rcleaves = [l for l in including_rcleaves if not l.holiday_id]
        including_holiday_rcleaves = [l for l in including_rcleaves if l.holiday_id]
        rc_leave = False

        if bypassing_codes:
            bypassing_rc_leave = [
                l
                for l in including_holiday_rcleaves
                if l.holiday_id.holiday_status_id.work_entry_type_id.code
                in bypassing_codes
            ]
        else:
            bypassing_rc_leave = []

        by = "none"  # debuglog
        if bypassing_rc_leave:
            rc_leave = bypassing_rc_leave[0]
            by = "bypassing"  # debuglog
        elif including_global_rcleaves:
            rc_leave = including_global_rcleaves[0]
            by = "global"  # debuglog
        elif including_holiday_rcleaves:
            rc_leave = including_holiday_rcleaves[0]
            by = "holiday"  # debuglog
        _debug.logic("leave_work_entry_type", by=by, version=self)
        if rc_leave:
            return self._get_leave_work_entry_type_dates(
                rc_leave, interval_start, interval_stop, self.employee_id
            )
        return self.env.ref("hr_work_entry.work_entry_type_leave")

    def _get_domain_sub_leave(self):
        return super()._get_domain_sub_leave() | Domain(
            "holiday_id.employee_id", "in", self.employee_id.ids
        )

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        res = super()._generate_work_entries_postprocess_adapt_to_calendar(vals)
        return res or ("work_entry_type_id" in vals and vals.get("leave_id"))
