# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser
from odoo import api, fields, models


class HotelRestaurantReport(models.AbstractModel):
    _name = 'report.hotel_restaurant.report_res_table'

    def get_res_data(self, date_start, date_end):
        data = []
        rest_reservation_obj = self.env['hotel.restaurant.reservation']
        act_domain = [('start_date', '>=', date_start),
                      ('end_date', '<=', date_end)]
        tids = rest_reservation_obj.search(act_domain)
        for record in tids:
            data.append({'reservation': record.reservation_id,
                         'name': record.cname.name,
                         'start_date': parser.parse(record.start_date).
                         strftime('%m/%d/%Y'),
                         'end_date': parser.parse(record.end_date).
                         strftime('%m/%d/%Y')})
        return data

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids',
                                                                []))
        date_start = data.get('date_start', fields.Date.today())
        date_end = data['form'].get('date_end', str(datetime.now() +
                                    relativedelta(months=1,
                                                  day=1, days=1))[:10])
        rm_act = self.with_context(data['form'].get('used_context', {}))
        reservation_res = rm_act.get_res_data(date_start, date_end)
        docargs = {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'Bookings': reservation_res,
        }
        docargs['data'].update({'date_end':
                                parser.parse(docargs.get('data').
                                             get('date_end')).strftime('%m/%d/\
                                                                        %Y')})
        docargs['data'].update({'date_start':
                                parser.parse(docargs.get('data').
                                             get('date_start')).strftime('%m/\
                                                                          %d/\
                                                                         %Y')})
        render_model = 'hotel_restaurant.report_res_table'
        return self.env['report'].render(render_model, docargs)


class ReportKot(models.AbstractModel):
    _name = 'report.hotel_restaurant.report_hotel_order_kot'
    _inherit = 'report.abstract_report'
    _template = 'hotel_restaurant.report_hotel_order_kot'
    _wrapped_report_class = HotelRestaurantReport


class ReportBill(models.AbstractModel):
    _name = 'report.hotel_restaurant.report_hotel_order_kot'
    _inherit = 'report.abstract_report'
    _template = 'hotel_restaurant.report_hotel_order_kot'
    _wrapped_report_class = HotelRestaurantReport


class FolioRestReport(models.AbstractModel):
    _name = 'report.hotel_restaurant.report_rest_order'

    def get_data(self, date_start, date_end):
        data = []
        act_domain = [('checkin_date', '>=', date_start),
                      ('checkout_date', '<=', date_end)]
        tids = self.env['hotel.folio'].search(act_domain)
        total = 0.0
        for record in tids:
            if record.hotel_reservation_order_ids:
                total_amount = 0.0
                total_order = 0
                for order in record.hotel_reservation_order_ids:
                    total_amount = total_amount + order.amount_total
                    total_order += 1
                total += total_amount
                data.append({'folio_name': record.name,
                             'customer_name': record.partner_id.name,
                             'checkin_date': parser.parse(record.checkin_date).
                            strftime('%m/%d/%Y %H:%M:%S'),
                             'checkout_date': parser.parse(record.
                                                           checkout_date).
                             strftime('%m/%d/%Y %H:%M:%S'),
                             'total_amount': total_amount,
                             'total_order': total_order})
        data.append({'total': total})
        return data

    def get_rest(self, date_start, date_end):
        data = []
        rest_domain = [('checkin_date', '>=', date_start),
                       ('checkout_date', '<=', date_end)]
        tids = self.env['hotel.folio'].search(rest_domain)
        for record in tids:
            if record.hotel_reservation_order_ids:
                order_data = []
                for order in record.hotel_reservation_order_ids:
                    order_data.append({'order_no': order.order_number,
                                       'order_date': parser.parse(order.date1).
                                       strftime('%m/%d/%Y %H:%M:%S'),
                                       'state': order.state,
                                       'table_no': len(order.table_no),
                                       'order_len': len(order.order_list),
                                       'amount_total': order.amount_total})
                data.append({'folio_name': record.name,
                             'customer_name': record.partner_id.name,
                             'order_data': order_data})
        return data

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')

        docs = self.env[self.model].browse(self.env.context.get('active_ids',
                                                                []))
        date_start = data['form'].get('date_start', fields.Date.today())
        date_end = data['form'].get('date_end', str(datetime.now() +
                                    relativedelta(months=1,
                                                  day=1, days=1))[:10])
        rm_act = self.with_context(data['form'].get('used_context', {}))
        get_data_res = rm_act.get_data(date_start, date_end)
        get_rest_res = rm_act.get_rest(date_start, date_end)
        docargs = {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'GetData': get_data_res,
            'GetRest': get_rest_res,
        }
        docargs['data'].update({'date_end':
                                parser.parse(docargs.get('data').
                                             get('date_end')).strftime('%m/%d/\
                                                                        %Y')})
        docargs['data'].update({'date_start':
                                parser.parse(docargs.get('data').
                                             get('date_start')).strftime('%m/\
                                                                          %d/\
                                                                         %Y')})
        render_model = 'hotel_restaurant.report_rest_order'
        return self.env['report'].render(render_model, docargs)


class FolioReservReport(models.AbstractModel):
    _name = 'report.hotel_restaurant.report_reserv_order'

    def get_data(self, date_start, date_end):
        data = []
        folio_obj = self.env['hotel.folio']
        reserve_domain = [('checkin_date', '>=', date_start),
                          ('checkout_date', '<=', date_end)]
        tids = folio_obj.search(reserve_domain)
        total = 0.0
        for record in tids:
            if record.hotel_restaurant_order_ids:
                total_amount = 0.0
                total_order = 0
                for order in record.hotel_restaurant_order_ids:
                    total_amount = total_amount + order.amount_total
                    total_order += 1
                total += total_amount
                data.append({'folio_name': record.name,
                             'customer_name': record.partner_id.name,
                             'checkin_date': parser.parse(record.checkin_date).
                             strftime('%m/%d/%Y %H:%M:%S'),
                             'checkout_date': parser.parse(record.
                                                           checkout_date).
                             strftime('%m/%d/%Y %H:%M:%S'),
                             'total_amount': total_amount,
                             'total_order': total_order})
        data.append({'total': total})
        return data

    def get_reserv(self, date_start, date_end):
        data = []
        folio_obj = self.env['hotel.folio']
        res_domain = [('checkin_date', '>=', date_start),
                      ('checkout_date', '<=', date_end)]
        tids = folio_obj.search(res_domain)
        for record in tids:
            if record.hotel_restaurant_order_ids:
                order_data = []
                for order in record.hotel_restaurant_order_ids:
                    order_date = parser.parse(order.o_date)
                    order_date = order_date.strftime('%m/%d/%Y %H:%M:%S')
                    order_data.append({'order_no': order.order_no,
                                       'order_date': order_date,
                                       'state': order.state,
                                       'room_no': order.room_no.name,
                                       'table_no': len(order.table_no),
                                       'amount_total': order.amount_total})
                data.append({'folio_name': record.name,
                             'customer_name': record.partner_id.name,
                             'order_data': order_data})
        return data

    @api.model
    def render_html(self, docids, data=None):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_ids',
                                                                []))
        date_start = data.get('date_start', fields.Date.today())
        date_end = data['form'].get('date_end', str(datetime.now() +
                                    relativedelta(months=1,
                                                  day=1, days=1))[:10])
        rm_act = self.with_context(data['form'].get('used_context', {}))
        get_data_res = rm_act.get_data(date_start, date_end)
        get_reserv_res = rm_act.get_reserv(date_start, date_end)
        docargs = {
            'doc_ids': docids,
            'doc_model': self.model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'GetData': get_data_res,
            'GetReserv': get_reserv_res,
        }
        dt_end = parser.parse(docargs.get('data').get('date_end'))
        date_end = dt_end.strftime('%m/%d/%Y')
        docargs['data'].update({'date_end': date_end})
        dt_start = parser.parse(docargs.get('data').get('date_start'))
        date_start = dt_start.strftime('%m/%d/%Y')
        docargs['data'].update({'date_start': date_start})
        render_model = 'hotel_restaurant.report_reserv_order'
        return self.env['report'].render(render_model, docargs)
