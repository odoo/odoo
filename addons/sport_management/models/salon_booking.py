# -*- coding: utf-8 -*-
###################################################################################
#
#    A2A Digtial 
#    Copyright (C) 2021-TODAY A2A Digital (<https://www.a2adigital.com>).
#
###################################################################################

from datetime import date
from odoo import models, fields, api


class SalonBookingBackend(models.Model):
    _name = 'salon.booking'

    name = fields.Char(string="Name")
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')], default="draft")
    time = fields.Datetime(string="Booking Date")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="E-Mail")
    services = fields.Many2many('salon.service', string="Services")
    chair_id = fields.Many2one('salon.chair', string="Court")
    duration_id = fields.Many2one('salon.duration', string="Duration")
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company'].browse(1))
    bank_trx_id = fields.Char(string="Trx. ID",help="Trx ID of completed transaction")
    lang = fields.Many2one('res.lang', 'Language',
                           default=lambda self: self.env['res.lang'].browse(1))

    def all_salon_orders(self):
        if self.time:
            date_only = str(self.time)[0:10]
        else:
            date_only = date.today()
        all_salon_service_obj = self.env['salon.order'].search([('chair_id', '=', self.chair_id.id),
                                                                ('start_date_only', '=', date_only)])
        self.filtered_orders = [(6, 0, [x.id for x in all_salon_service_obj])]

    filtered_orders = fields.Many2many('salon.order', string="Sport Orders", compute="all_salon_orders")

    def booking_approve(self):
        salon_order_obj = self.env['salon.order']
        salon_service_obj = self.env['salon.order.lines']
        order_data = {
            'customer_name': self.name,
            'chair_id': self.chair_id.id,
            'start_time': self.time,
            'date': date.today(),
            'stage_id': 1,
            'booking_identifier': True,
        }
        order = salon_order_obj.create(order_data)
        for records in self.services:
            service_data = {
                'service_id': records.id,
                'time_taken': records.time_taken,
                'price': records.price,
                'price_subtotal': records.price,
                'salon_order': order.id,
            }
            salon_service_obj.create(service_data)
        template = self.env.ref('sport_management.salon_email_template_approved')
        self.env['mail.template'].browse(template.id).send_mail(self.id)
        self.state = "approved"

    def booking_reject(self):
        template = self.env.ref('sport_management.salon_email_template_rejected')
        self.env['mail.template'].browse(template.id).send_mail(self.id)
        self.state = "rejected"

