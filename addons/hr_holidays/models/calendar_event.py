from odoo import models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    def _is_video_call_required(self):
        self.check_singleton()
        if self.res_model == "hr.leave":
            return False
        return super()._is_video_call_required()

    def _prepare_reservation_vals_list(self):
        self.check_singleton()
        # A leave reaches the resource as a schedule exception, which removes
        # the time from availability; booking it too charges the absence twice.
        if self.res_model == "hr.leave":
            return []
        return super()._prepare_reservation_vals_list()
