# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailTestCC(models.Model):
    _name = 'mail.test.cc'
    _description = "Test Email CC Thread"
    _inherit = ['mail.thread.cc']

    name = fields.Char()


class MailTestCustomer(models.Model):
    _name = 'mail.test.customer'
    _description = "Test Email Customer Thread"
    _inherit = ['mail.thread.customer']

    _mail_field_email = 'email_from'
    _mail_field_customer = 'customer_id'

    name = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    email_from = fields.Char('Email')
    user_id = fields.Many2one('res.users', 'Responsible', tracking=1)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company.id)
