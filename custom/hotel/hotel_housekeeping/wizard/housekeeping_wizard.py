# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class HotelHousekeepingWizard(models.TransientModel):
    _name = 'hotel.housekeeping.wizard'

    date_start = fields.Datetime('Activity Start Date', required=True)
    date_end = fields.Datetime('Activity End Date', required=True)
    room_no = fields.Many2one('hotel.room', 'Room No', required=True)

    @api.multi
    def print_report(self):
        data = {
            'ids': self.ids,
            'model': 'hotel.housekeeping',
            'form': self.read(['date_start', 'date_end', 'room_no'])[0]
        }
        return self.env['report'
                        ].get_action(self,
                                     'hotel_housekeeping.report_housekeeping',
                                     data=data)
