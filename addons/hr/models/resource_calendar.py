from odoo import fields, models
from odoo.fields import Domain

from ..tools import debug_log as dbg


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    def _transfer_leaves_to_calendar(
        self, other_calendar, resources=None, from_date=None
    ):
        from_date = from_date or fields.Datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        domain = [
            ("calendar_id", "in", self.ids),
            ("date_from", ">=", from_date),
        ]
        domain = (
            Domain.AND([domain, [("resource_id", "in", resources.ids)]])
            if resources
            else domain
        )

        leaves = self.env["resource.schedule.exception"].search(domain)
        dbg.pipeline.debug(
            "resource.calendar %s -> %s: moving %s from %s (resources %s)",
            dbg.rec(self),
            other_calendar.id,
            dbg.rec(leaves),
            from_date,
            dbg.rec(resources) if resources else "all",
        )
        leaves.write(
            {
                "calendar_id": other_calendar.id,
            }
        )
