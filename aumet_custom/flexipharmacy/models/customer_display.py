# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, fields, api, _


class CustomerDisplay(models.Model):
    _name = 'customer.display'
    _description = "Customer Display"

    @api.model
    def broadcast_data(self, data):
        notifications = []
        vals = {
            'user_id': self._uid,
            'orderLines': data.get('orderLines'),
            'total': data.get('total'),
            'tax': data.get('tax'),
            'customer_name': data.get('client_name'),
            'order_total': data.get('order_total'),
            'change_amount': data.get('change_amount'),
            'payment_info': data.get('payment_info'),
            'enable_customer_rating': data.get('enable_customer_rating'),
            'set_customer': data.get('set_customer'),
            'order_note': data.get('order_note'),
            'new_order': data.get('new_order') and True or False,
        }
        notifications.append([(self._cr.dbname, 'customer.display', self._uid), {'customer_display_data': vals}])
        self.env['bus.bus'].sendmany(notifications)
        return True

    @api.model
    def send_rating(self, config_id, rating_val):
        notifications = []
        session_id = self.env['pos.session'].search([('config_id', '=', config_id), ('state', '=', 'opened')], limit=1)
        if session_id:
            notifications.append(
                [(self._cr.dbname, 'customer.display', session_id.user_id.id), {'rating': rating_val}])
            self.env['bus.bus'].sendmany(notifications)
        return True

    @api.model
    def create_customer(self, vals, config_id):
        partner = self.env['res.partner'].create({
            'company_type': 'person',
            'name': vals['name'],
            'street': vals['street'],
            'city': vals['city'],
            'zip': vals['zip'],
            'email': vals['email'],
            'phone': vals['phone'],
        })
        if partner:
            notifications = []
            session_id = self.env['pos.session'].search([('config_id', '=', config_id),
                                                         ('state', '=', 'opened')], limit=1)
            if session_id:
                notifications.append(
                    [(self._cr.dbname, 'customer.display', session_id.user_id.id), {'partner_id': partner.id}])
                self.env['bus.bus'].sendmany(notifications)

    name = fields.Char("Name")
    image = fields.Binary("Image")
    config_id = fields.Many2one('pos.config', "POS config")


class AdVideo(models.Model):
    _name = 'ad.video'
    _description = "Advertise Video"

    video_id = fields.Char(string="YouTube Video ID")
    config_id = fields.Many2one('pos.config', "POS config")
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
