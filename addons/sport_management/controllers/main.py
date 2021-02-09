# -*- coding: utf-8 -*-
###################################################################################
#
#    A2A Digtial 
#    Copyright (C) 2021-TODAY A2A Digital (<https://www.a2adigital.com>).
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
        bank_trx_id = kwargs ['bank_trx_id']
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
            'duration_id':duration,
            'bank_trx_id':bank_trx_id
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
                'duration':duration_name,
                'bank_trx_id':bank_trx_id
            }
            send_receive_booking_email(email_booking_data)
        
        salon_booking.create(booking_data)
        
        return json.dumps({'result': True})

    @http.route('/page/salon_check_date_booked_court', type='json', auth="public", website=True)
    def salon_check_booked_court(self, **kwargs):
        date_check = str(kwargs.get('check_date'))
        
        # < FIXED THE TIMING DIFFERENT +7 HOURS BASE
        date_check_str = datetime.strptime(date_check, '%m/%d/%Y').strftime('%Y-%m-%d')
        date_check_obj = datetime.strptime(date_check_str,'%Y-%m-%d')
        date_check_obj_add_17 = datetime.strptime(date_check_str,'%Y-%m-%d') + timedelta(hours=17,minutes=0,seconds=0)    
        date_check_obj_minus_7 = date_check_obj - timedelta (hours=7,minutes=0,seconds=0)
        # FIXED THE TIMING DIFFERENT +7 HOURS BASE >
        
        # """ ORIGINAL FUNCTION """
        # order_obj = request.env['salon.order'].search([('chair_id.active_booking_chairs', '=', True),
        #                                                ('stage_id', 'in', [1, 2, 3]),
        #                                                ('start_date_only', '=', datetime.strptime(date_check, '%m/%d/%Y').strftime('%Y-%m-%d'))])
        # """ ORIGIN FUNCTION """

        order_obj_17 = request.env['salon.order'].search([('chair_id.active_booking_chairs', '=', True),
                                                       ('stage_id', 'in', [1, 2, 3]), 
                                                       ('start_time', '>=',date_check_obj_minus_7),
                                                       ('start_time','<',date_check_obj_add_17) 
                                                       ]).sorted('start_time')
        order_details = {}
        for orders in order_obj_17:
            # This block of function might not included if timzone configuration is right when deployed 
            time_start_local_pp = ((datetime.strptime(orders.start_time_only,"%H:%M") + timedelta(hours=7)).time()).strftime("%H:%M")
            time_end_local_pp = ((datetime.strptime(orders.end_time_only,"%H:%M") + timedelta(hours=7)).time()).strftime("%H:%M")
            # This block of function might not included if timzone configuration is right when deployed 
            data = {
                'number': orders.id,
                'start_time_only': time_start_local_pp,
                'end_time_only': time_end_local_pp
            }
            print("DDDDDDDDDDDDDDD DATA ",data,type(data))
            if orders.chair_id.id not in order_details:
                order_details[orders.chair_id.id] = {'name': orders.chair_id.name, 'orders': [data]}
            else:
                order_details[orders.chair_id.id]['orders'].append(data)
        return order_details
    
    @http.route('/page/salon_check_date_available_court', type='json', auth="public", website=True)
    def salon_check_available_court(self, **kwargs):
        date_check = str(kwargs.get('check_date'))
        # < FIXED THE TIMING DIFFERENT +7 HOURS BASE
        date_check_str = datetime.strptime(date_check, '%m/%d/%Y').strftime('%Y-%m-%d')
        date_check_obj = datetime.strptime(date_check_str,'%Y-%m-%d')
        date_check_obj_add_17 = datetime.strptime(date_check_str,'%Y-%m-%d') + timedelta(hours=17,minutes=0,seconds=0)    
        date_check_obj_minus_7 = date_check_obj - timedelta (hours=7,minutes=0,seconds=0)
        # FIXED THE TIMING DIFFERENT +7 HOURS BASE >
        order_obj_17 = request.env['salon.order'].search([('chair_id.active_booking_chairs', '=', True),
                                                       ('stage_id', 'in', [1, 2, 3]), 
                                                       ('start_time', '>=',date_check_obj_minus_7),
                                                       ('start_time','<',date_check_obj_add_17) 
                                                       ]).sorted('start_time')
        chair_obj = request.env['salon.chair'].search([('active_booking_chairs', '=', True)])
        working_hour_obj = request.env['salon.working.hours'].search([('name','=',date_check_obj.strftime("%A"))])
        order_details = {}
        oc_list = []
        for orders in order_obj_17:
            if orders.chair_id.id not in oc_list:
                oc_list.append(orders.chair_id.id)
        # AVAILABLE TIME OF BOOKED COURT
        for orders in order_obj_17:
            if orders.chair_id.id not in oc_list:
                oc_list.append(orders.chair_id.id)

            time_start_local_pp = ((datetime.strptime(orders.end_time_only,"%H:%M") + timedelta(hours=7)).time()).strftime("%H:%M")
            data = {
                    'number': orders.id,
                    'start_time_only': time_start_local_pp,
                    'end_time_only': 'NONE'
            }
            if orders.chair_id.id not in order_details: 
                order_details[orders.chair_id.id] = {'name': orders.chair_id.name, 'orders': [data]}
            else:
                order_details[orders.chair_id.id]['orders'].append(data)
        # AVAILABLE TIME OF BOOKED COURT
        # AVAILABLE TIME OF NO-BOOKED COURT
        for chair in chair_obj :
            if chair.id not in oc_list: 
                # This block of function might not included if timzone configuration is right when deployed 
                time_start_local_pp = '{0:02.0f}:{1:02.0f}'.format(*divmod(working_hour_obj.from_time * 60, 60))
                time_end_local_pp = '{0:02.0f}:{1:02.0f}'.format(*divmod(working_hour_obj.to_time * 60, 60))
                # This block of function might not included if timzone configuration is right when deployed 
                data={
                    'number' : chair.id,
                    'start_time_only' : time_start_local_pp,
                    'end_time_only' : time_end_local_pp 
                }
                order_details [chair.id] = {'name': chair.name, 'orders': [data]}
        # AVAILABLE TIME OF NO-BOOKED COURT
        return order_details

    @http.route('/page/sport_management.sport_booking_thank_you', type='http', auth="public", website=True)
    def thank_you(self, **post):
        return request.render('sport_management.salon_booking_thank_you', {})

    @http.route('/page/sport_management/sport_booking_form', type='http', auth="public", website=True)
    def chair_info(self, **post):
        salon_working_hours_obj = request.env['salon.working.hours'].search([])
        salon_holiday_obj = request.env['salon.holiday'].search([('holiday', '=', True)])
        chair_obj = request.env['salon.chair'].search([('active_booking_chairs', '=', True)])
        duration_obj = request.env['salon.duration'].search([('time_available','=',True)])
        # < FIXED THE TIMING DIFFERENT +7 HOURS BASE
        date_check = datetime.strptime(datetime.strftime(date.today(),'%Y-%m-%d'),'%Y-%m-%d')
        date_check_obj_add_17 = date_check + timedelta(hours=17,minutes=0,seconds=0) 
        date_check_obj_minus_7 = date_check - timedelta (hours=7,minutes=0,seconds=0)
        # FIXED THE TIMING DIFFERENT +7 HOURS BASE >
        order_obj = request.env['salon.order'].search([('chair_id.active_booking_chairs', '=', True),
                                                       ('stage_id', 'in', [1, 2, 3]), 
                                                       ('start_time', '>=',date_check_obj_minus_7),
                                                       ('start_time','<',date_check_obj_add_17) 
                                                       ]).sorted('start_time')
        start_time_only_local_pp = {}
        end_time_only_local_pp = {}
        for orders in order_obj:
            # This block of function might not included if timzone configuration is right when deployed 
            # ( WE DON'T CHANGE ANY UTC TIME OR DATE WE IMPORT THEIR DATA & CONVERT TO LOCAL PHNOM PENH TIME ONLY)
            start_time_only_local_pp [orders.id]= ((datetime.strptime(orders.start_time_only,"%H:%M") + timedelta(hours=7)).time()).strftime("%H:%M")
            end_time_only_local_pp [orders.id] = ((datetime.strptime(orders.end_time_only,"%H:%M") + timedelta(hours=7)).time()).strftime("%H:%M")
            # ( WE DON'T CHANGE ANY UTC TIME OR DATE WE IMPORT THEIR DATA & CONVERT TO LOCAL PHNOM PENH TIME ONLY)
            # This block of function might not included if timzone configuration is right when deployed 
        
        salon_service_obj = request.env['salon.service'].search([])
        booking_payment_obj = request.env['salon.booking.payment'].search([('activate_payment','=',True)])
        court_option = ["Booked Court","Available Court"]
        return request.render('sport_management.salon_booking_form',
                              {'chair_details': chair_obj, 'order_details': order_obj,
                                'duration_details': duration_obj, 
                                'date_search': date_check,
                                'holiday': salon_holiday_obj,
                                'working_time': salon_working_hours_obj,
                                'salon_service' : salon_service_obj, 
                                'booking_payment': booking_payment_obj,
                                'court_option': court_option,
                                'start_time_only_local_pp': start_time_only_local_pp,
                                'end_time_only_local_pp':end_time_only_local_pp
                               })
