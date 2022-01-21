# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
    """ A model inheriting from mail.thread.phone allowing to test auto formatting
    of phone numbers, blacklist, ... """
    _description = 'SMS Mailing Blacklist Enabled'
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
        # TDE note: should override _phone_get_number_fields but ok as sms in dependencies
        return ['phone_nbr', 'mobile_nbr']


class MailTestSMSOptout(models.Model):
    """ Model using blacklist mechanism and a hijacked opt-out mechanism for
    mass mailing features. """
    _description = 'SMS Mailing Blacklist / Optout Enabled'
    _name = 'mail.test.sms.bl.optout'
    _inherit = ['mail.thread.phone']
    _order = 'name asc, id asc'

    name = fields.Char()
    subject = fields.Char()
    email_from = fields.Char()
    phone_nbr = fields.Char()
    mobile_nbr = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    opt_out = fields.Boolean()

    def _sms_get_partner_fields(self):
        return ['customer_id']

    def _sms_get_number_fields(self):
        # TDE note: should override _phone_get_number_fields but ok as sms in dependencies
        return ['phone_nbr', 'mobile_nbr']


class MailTestSMSPartner(models.Model):
    """ A model like sale order having only a customer, not specific phone
    or mobile fields. """
    _description = 'Chatter Model for SMS Gateway (Partner only)'
    _name = 'mail.test.sms.partner'
    _inherit = ['mail.thread']

    name = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    opt_out = fields.Boolean()

    def _sms_get_partner_fields(self):
        return ['customer_id']

    def _sms_get_number_fields(self):
        return []


class MailTestSMSPartner2Many(models.Model):
    """ A model like sale order having only a customer, not specific phone
    or mobile fields. """
    _description = 'Chatter Model for SMS Gateway (M2M Partners only)'
    _name = 'mail.test.sms.partner.2many'
    _inherit = ['mail.thread']

    name = fields.Char()
    customer_ids = fields.Many2many('res.partner', string='Customers')
    opt_out = fields.Boolean()

    def _sms_get_partner_fields(self):
        return ['customer_ids']

    def _sms_get_number_fields(self):
        return []
