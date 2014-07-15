# -*- coding: utf-8 -*-

from openerp import api, models


class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    @api.model
    def create(self, vals):
        result = super(CalendarEvent, self).create(vals)
        if self.env.context.get('active_model') == 'hr.appraisal':
            appraisal = self.env['hr.appraisal'].browse(self.env.context.get('active_id'))
            appraisal.write({
                'meeting_id': result.id,
                'interview_deadline': result.start_date if result.allday else result.start_datetime
            })
        return result
