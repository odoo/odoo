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

import json
from datetime import datetime, date, time , timedelta

import pytz
from odoo import http
from odoo.http import request
from .booking_email import send_receive_booking_email
import time
class SalonBookingWeb(http.Controller):

    @http.route('/page/salon_details', csrf=False, type="http", methods=['POST', 'GET'], auth="public", website=True)
    def salon_details(self, **kwargs):
        name = kwargs['name']
        dates = kwargs['date']
        time = kwargs['time']
        phone = kwargs['phone']
        chair = kwargs['chair']
        duration = kwargs['duration']
        j = 0
        dates_time = dates+" "+time+":00"
        date_and_time = datetime.strptime(dates_time, '%m/%d/%Y %H:%M:%S')
        
        # This block of function might not included if timzone configuration is right when deployed 
        local = pytz.timezone ("Asia/Phnom_Penh")
        local_booking_dt = local.localize(date_and_time,is_dst=None)
        utc_date_time = local_booking_dt.astimezone(pytz.utc)
        utc_date_time = datetime.strftime(utc_date_time,"%Y-%m-%d %H:%M:%S")
        utc_date_time_strp = datetime.strptime(utc_date_time,"%Y-%m-%d %H:%M:%S")
        # This block of function might not included if timzone configuration is right when deployed 

        salon_booking = request.env['salon.booking']
        booking_data = {
            'name': name,
            'phone': phone,
            'time': utc_date_time_strp,
            'chair_id': chair,
            'duration_id':duration
        }
        
        # IF THERE IS EMAIL IN THE RES.COMPANY, WE SEND THE COMPANY NOTIFICATION EMAIL THAT THERE IS BOOKING  
        email_notify_obj = request.env['salon.booking.email'].search([])
        if email_notify_obj.booking_email_sender and email_notify_obj.booking_email_pass and email_notify_obj.booking_email_receiver and email_notify_obj.booking_smtp_host and email_notify_obj.booking_smtp_port:
            chair_name = request.env['salon.chair'].search([('id','=',chair)]).name
            duration_name = request.env['salon.duration'].search([('id','=',duration)]).name
            email_booking_data ={
                'sender_email': email_notify_obj.booking_email_sender,
                'sender_pass': email_notify_obj.booking_email_pass,
                'receiver_email':email_notify_obj.booking_email_receiver,
                'smtp_host':email_notify_obj.booking_smtp_host,
                'smtp_port':email_notify_obj.booking_smtp_port,
                'chair_name':chair_name,
                'time':date_and_time,
                'name':name,
                'phone':phone,
                'duration':duration_name
            }
            send_receive_booking_email(email_booking_data)
        
        salon_booking.create(booking_data)
        
        return json.dumps({'result': True})

    @http.route('/page/salon_check_date', type='json', auth="public", website=True)
    def salon_check(self, **kwargs):
        date_check = str(kwargs.get('check_date'))
        order_obj = request.env['salon.order'].search([('chair_id.active_booking_chairs', '=', True),
                                                       ('stage_id', 'in', [1, 2, 3]),
                                                       ('start_date_only', '=', datetime.strptime(date_check, '%m/%d/%Y').strftime('%Y-%m-%d'))])
        order_details = {}
        for orders in order_obj:
            # This block of function might not included if timzone configuration is right when deployed 
            time_start_local_pp = ((datetime.strptime(orders.start_time_only,"%H:%M") + timedelta(hours=7)).time()).strftime("%H:%M")
            time_end_local_pp = ((datetime.strptime(orders.end_time_only,"%H:%M") + timedelta(hours=7)).time()).strftime("%H:%M")
            # This block of function might not included if timzone configuration is right when deployed 
            data = {
                'number': orders.id,
                'start_time_only': time_start_local_pp,
                'end_time_only': time_end_local_pp
            }
            if orders.chair_id.id not in order_details:
                order_details[orders.chair_id.id] = {'name': orders.chair_id.name, 'orders': [data]}
            else:
                order_details[orders.chair_id.id]['orders'].append(data)
        return order_details

    @http.route('/page/sport_management.sport_booking_thank_you', type='http', auth="public", website=True)
    def thank_you(self, **post):
        return request.render('salon_management.salon_booking_thank_you', {})

    @http.route('/page/sport_management/sport_booking_form', type='http', auth="public", website=True)
    def chair_info(self, **post):
        salon_working_hours_obj = request.env['salon.working.hours'].search([])
        salon_holiday_obj = request.env['salon.holiday'].search([('holiday', '=', True)])
        date_check = date.today()
        chair_obj = request.env['salon.chair'].search([('active_booking_chairs', '=', True)])
        duration_obj = request.env['salon.duration'].search([('time_available','=',True)])
        order_obj = request.env['salon.order'].search([('chair_id.active_booking_chairs', '=', True),
                                                       ('stage_id', 'in', [1, 2, 3])])
        salon_service_obj = request.env['salon.service'].search([])
        order_obj = order_obj.search([('start_date_only', '=', date_check)])
        
        return request.render('salon_management.salon_booking_form',
                              {'chair_details': chair_obj, 'order_details': order_obj,
                                'duration_details': duration_obj, 
                                'date_search': date_check,
                                'holiday': salon_holiday_obj,
                                'working_time': salon_working_hours_obj,
                                'salon_service' : salon_service_obj 
                               })
