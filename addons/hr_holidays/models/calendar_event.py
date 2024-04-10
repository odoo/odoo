from odoo import models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def _need_video_call(self):
        """ Determine if the event needs a video call or not depending
        on the model of the event.

        This method, implemented and invoked in google_calendar, is necessary
        due to the absence of a bridge module between google_calendar and hr_holidays.
        """
        self.ensure_one()
        if self.res_model == 'hr.leave':
            return False
        return super()._need_video_call()
