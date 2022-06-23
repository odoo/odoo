# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailTestPortal(models.Model):
    """ A model intheriting from mail.thread with some fields used for portal
    sharing, like a partner, ..."""
    _description = 'Chatter Model for Portal'
    _name = 'mail.test.portal'
    _inherit = [
        'mail.thread',
        'portal.mixin',
    ]

    name = fields.Char()
    partner_id = fields.Many2one('res.partner', 'Customer')

    def _compute_access_url(self):
        self.access_url = False
        for record in self.filtered('id'):
            record.access_url = '/my/test_portal/%s' % self.id


class MailTestSMS(models.Model):
    """ A model inheriting from mail.thread with some fields used for SMS
    gateway, like a partner, a specific mobile phone, ... """
    _description = 'Chatter Model for SMS Gateway'
    _name = 'mail.test.sms'
    _inherit = ['mail.thread']
    _order = 'name asc, id asc'

    name = fields.Char()
    subject = fields.Char()
    email_from = fields.Char()
    phone_nbr = fields.Char()
    mobile_nbr = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')

    def _sms_get_partner_fields(self):
        return ['customer_id']

    def _sms_get_number_fields(self):
        return ['phone_nbr', 'mobile_nbr']


class MailTestSMSBL(models.Model):
    """ A model inheriting from mail.thread with some fields used for SMS
    gateway, like a partner, a specific mobile phone, ... """
    _description = 'Chatter Model for SMS Gateway'
    _name = 'mail.test.sms.bl'
    _inherit = ['mail.thread.phone']
    _order = 'name asc, id asc'

    name = fields.Char()
    subject = fields.Char()
    email_from = fields.Char()
    phone_nbr = fields.Char()
    mobile_nbr = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')

    def _sms_get_partner_fields(self):
        return ['customer_id']

    def _sms_get_number_fields(self):
        return ['phone_nbr', 'mobile_nbr']


class MailTestSMSSoLike(models.Model):
    """ A model like sale order having only a customer, not specific phone
    or mobile fields. """
    _description = 'Chatter Model for SMS Gateway (Partner only)'
    _name = 'mail.test.sms.partner'
    _inherit = ['mail.thread']

    name = fields.Char()
    partner_id = fields.Many2one('res.partner', 'Customer')
