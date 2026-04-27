from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _timesheet_create_task_prepare_values(self, project):
        res = super()._timesheet_create_task_prepare_values(project)
        if self.calendar_event_id:
            res |= {
                "planned_date_begin": self.calendar_event_id.start,
                "date_deadline": self.calendar_event_id.stop,
            }
            res.pop("description", None)
        return res
