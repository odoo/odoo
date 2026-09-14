from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

from .hr_homeworking import DAYS

_debug = DebugLog(__name__)


class HrWorkLocation(models.Model):
    _inherit = "hr.work.location"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_by_employee(self):
        # sudo and active_test=False on purpose: a location this user cannot see
        # in use -- another company's employee, an archived one -- is still in
        # use, and the foreign key is ON DELETE SET NULL, so letting the unlink
        # through empties that employee's week with nothing to show for it.
        employees = self.env["hr.employee"].sudo().with_context(active_test=False)
        domain = ["|"] * (len(DAYS) - 1) + [(day, "in", self.ids) for day in DAYS]
        if employees.search_count(domain, limit=1):
            blocked = self.browse(sorted(self._weekly_location_ids(employees, domain)))
            _debug.logic(
                "work_location.unlink_refused", requested=self, blocked=blocked
            )
            raise UserError(
                _(
                    "You cannot delete a work location that is a weekly work "
                    "location for an employee: %(locations)s",
                    locations=", ".join(blocked.mapped("name")),
                )
            )
        exceptions = (
            self.env["hr.employee.location"]
            .sudo()
            .search([("work_location_id", "in", self.ids)])
        )
        _debug.lifecycle(
            "work_location.unlink_cascades_exceptions",
            locations=self,
            exceptions=len(exceptions),
        )
        exceptions.unlink()

    def _weekly_location_ids(self, employees, domain):
        blocking = employees.search(domain)
        blocking.fetch(DAYS)
        requested = set(self.ids)
        return {
            blocker[day].id
            for blocker in blocking
            for day in DAYS
            if blocker[day].id in requested
        }
