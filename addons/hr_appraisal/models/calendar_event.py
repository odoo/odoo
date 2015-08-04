# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models


class CalendarEvent(models.Model):
    """ Model for Calendar Event """
    _inherit = 'calendar.event'

    @api.model
    def create(self, vals):
        result = super(CalendarEvent, self).create(vals)
        if self.env.context.get('active_model') == 'hr.appraisal':
            appraisal = self.env['hr.appraisal'].browse(self.env.context.get('active_id'))
            if appraisal:
                appraisal.write({
                    'meeting_id': result.id,
                    'date_final_interview': result.start_date if result.allday else result.start_datetime
                })
        return result
