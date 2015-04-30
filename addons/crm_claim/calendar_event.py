# -*- coding: utf-8 -*-

import datetime

from openerp import api, fields, models

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    claim_id = fields.Many2one('crm.claim', string="Claim", ondelete='cascade')
    start_datetime = fields.Datetime(default= lambda self: fields.Datetime.now())

    @api.onchange('start_datetime', 'stop_datetime')
    def onchange_startdatetime(self):
        if self.start_datetime:
           self.stop_datetime = fields.Datetime.from_string(self.start_datetime) + datetime.timedelta(hours=1)