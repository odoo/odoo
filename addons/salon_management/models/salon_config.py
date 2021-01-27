# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2019-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#
#    Author: AVINASH NK(<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

import re
from odoo import models, fields, api


class SalonWorkingHours(models.Model):
    _name = 'salon.working.hours'

    name = fields.Char(string="Name")
    from_time = fields.Float(string="Starting Time")
    to_time = fields.Float(string="Closing Time")


class SalonHoliday(models.Model):
    _name = 'salon.holiday'

    name = fields.Char(string="Name")
    holiday = fields.Boolean(string="Holiday")



class ConfigurationSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def booking_chairs(self):
        return self.env['salon.chair'].search([('active_booking_chairs', '=', True)])

    @api.model
    def holidays(self):
        return self.env['salon.holiday'].search([('holiday', '=', True)])

    @api.model
    def durations(self):
        return self.env['salon.duration'].search([('time_available','=',True)])
    
    @api.model
    def booking_activate_payment(self):
        return self.env['salon.booking.payment'].search([('activate_payment','=',True)]).activate_payment

    salon_booking_chairs = fields.Many2many('salon.chair', string="Booking Chairs", default=booking_chairs)
    salon_holidays = fields.Many2many('salon.holiday', string="Holidays", default=holidays)
    salon_durations = fields.Many2many('salon.duration',string="Duration",default=durations)
    salon_activate_payment = fields.Boolean(string="Activate Booking Payment", default=booking_activate_payment)

    def execute(self):
        salon_chair_obj = self.env['salon.chair'].search([])
        book_chair = []
        for chairs in self.salon_booking_chairs:
            book_chair.append(chairs.id)

        for records in salon_chair_obj:
            if records.id in book_chair:
                records.active_booking_chairs = True
            else:
                records.active_booking_chairs = False

        salon_holiday_obj = self.env['salon.holiday'].search([])
        holiday = []
        for days in self.salon_holidays:
            holiday.append(days.id)
        for records in salon_holiday_obj:
            if records.id in holiday:
                records.holiday = True
            else:
                records.holiday = False
        
        # Selecting the available time 
        salon_duration_obj = self.env['salon.duration'].search([])
        duration_list = []
        for durations in self.salon_durations:
            duration_list.append(durations.id)
        for records in salon_duration_obj:
            if records.id in duration_list:
                records.time_available = True
            else:
                records.time_available = False
        
        # Activate the QR Code Booking Payment
        salon_booking_payment_obj = self.env['salon.booking.payment'].search([])
        salon_booking_payment_obj.activate_payment = self.salon_activate_payment
