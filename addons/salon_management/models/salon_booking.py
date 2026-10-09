# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2021-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
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

import pytz
from datetime import datetime, time

from odoo import api, fields, models


class SalonBooking(models.Model):
    _name = 'salon.booking'
    _description = 'Salon Booking'

    name = fields.Char(string="Name", required=True)
    state = fields.Selection(
        string="State", default="draft",
        selection=[('draft', 'Draft'), ('approved', 'Approved'),
                   ('rejected', 'Rejected')])
    time = fields.Datetime(string="Date", required=True)
    phone = fields.Char(string="Phone")
    email = fields.Char(string="E-Mail")
    service_ids = fields.Many2many('salon.service',
                                   string="Services")
    chair_id = fields.Many2one('salon.chair', string="Chair",
                               required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company'].browse(1))
    language_id = fields.Many2one(
        'res.lang', 'Language',
        default=lambda self: self.env['res.lang'].browse(1))
    filtered_order_ids = fields.Many2many('salon.order',
                                          string="Salon Orders",
                                          compute="_compute_filtered_order_ids")

    def _compute_filtered_order_ids(self):
        """
        compute filtered_order_ids
        """
        if self.time:
            date_only = fields.Date.to_date(fields.Datetime.to_string(
                pytz.UTC.localize(self.time).astimezone(pytz.timezone(
                    self.env.user.tz)))[0:10])
        else:
            date_only = fields.Date.context_today(self)
        date_start = pytz.timezone(self.env.user.tz).localize(
            datetime.combine(date_only, time(0, 0, 0))).astimezone(
            pytz.UTC).replace(tzinfo=None)
        date_end = pytz.timezone(self.env.user.tz).localize(
            datetime.combine(date_only, time(23, 59, 59))).astimezone(
            pytz.UTC).replace(tzinfo=None)
        salon_orders = self.env['salon.order'].search(
            [('chair_id', '=', self.chair_id.id),
             ('start_time', '>=', date_start), ('start_time', '<=', date_end)])
        self.filtered_order_ids = [(6, 0, [x.id for x in salon_orders])]

    def action_approve_booking(self):
        """
        approve booking for salon services
        """
        order_data = {
            'customer_name': self.name,
            'chair_id': self.chair_id.id,
            'start_time': self.time,
            'date': fields.Datetime.now(),
            'stage_id': 1,
            'booking_identifier': True,
        }
        order = self.env['salon.order'].create(order_data)
        for records in self.service_ids:
            service_data = {
                'service_id': records.id,
                'time_taken': records.time_taken,
                'price': records.price,
                'price_subtotal': records.price,
                'salon_order_id': order.id,
            }
            self.env['salon.order.line'].create(service_data)
        template = self.env.ref(
            'salon_management.mail_template_salon_approved')
        self.env['mail.template'].browse(template.id).send_mail(self.id,
                                                                force_send=True)
        self.state = "approved"

    def action_reject_booking(self):
        """
        reject booking for salon services
        """
        template = self.env.ref(
            'salon_management.mail_template_salon_rejected')
        self.env['mail.template'].browse(template.id).send_mail(self.id,
                                                                force_send=True)
        self.state = "rejected"

    def get_booking_count(self):
        salon_bookings = self.env['salon.booking'].search_count(
            [('state', '=', 'approved')])
        recent_works = self.env['salon.order'].search_count(
            [('stage_id', 'in', [3, 4])])
        salon_orders = self.env['salon.order'].search_count([])
        salon_clients = self.env['res.partner'].search_count(
            [('partner_salon', '=', True)])

        salon_chairs = self.env['salon.chair'].search([])
        values = {
            'bookings': salon_bookings,
            'sales': recent_works,
            'orders': salon_orders,
            'clients': salon_clients,
            'chairs': salon_chairs
        }
        return values
