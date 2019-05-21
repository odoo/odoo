# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTestSMS(models.Model):
    """ A model inheriting from mail.thread with some fields used for SMS
    gateway, like a partner, a specific mobile phone, ... """
    _description = 'Chatter Model for SMS Gateway'
    _name = 'mail.test.sms'
    _inherit = ['mail.thread']

    name = fields.Char()
    subject = fields.Char()
    email_from = fields.Char()
    phone_nbr = fields.Char()
    mobile_nbr = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')

    @api.multi
    def _get_default_sms_recipients(self):
        return self.mapped('customer_id')
