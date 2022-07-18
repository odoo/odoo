# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
    _mailing_enabled = True
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
    _mailing_enabled = True
    _order = 'name asc, id asc'

    name = fields.Char()
    subject = fields.Char()
    email_from = fields.Char()
    phone_nbr = fields.Char()
    mobile_nbr = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')

    def _sms_get_partner_fields(self):
        return ['customer_id']

    def _phone_get_number_fields(self):
        return ['phone_nbr', 'mobile_nbr']


class MailTestSMSOptout(models.Model):
    """ Model using blacklist mechanism and a hijacked opt-out mechanism for
    mass mailing features. """
    _description = 'SMS Mailing Blacklist / Optout Enabled'
    _name = 'mail.test.sms.bl.optout'
    _inherit = ['mail.thread.phone']
    _mailing_enabled = True
    _order = 'name asc, id asc'

    name = fields.Char()
    subject = fields.Char()
    email_from = fields.Char()
    phone_nbr = fields.Char()
    mobile_nbr = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    opt_out = fields.Boolean()

    def _mailing_get_opt_out_list_sms(self, mailing):
        res_ids = mailing._get_recipients()
        return self.search([
            ('id', 'in', res_ids),
            ('opt_out', '=', True)
        ]).ids

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
    _mailing_enabled = True

    name = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    opt_out = fields.Boolean()

    def _mailing_get_opt_out_list_sms(self, mailing):
        res_ids = mailing._get_recipients()
        return self.search([
            ('id', 'in', res_ids),
            ('opt_out', '=', True)
        ]).ids

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
    _mailing_enabled = True

    name = fields.Char()
    customer_ids = fields.Many2many('res.partner', string='Customers')
    opt_out = fields.Boolean()

    def _mailing_get_opt_out_list_sms(self, mailing):
        res_ids = mailing._get_recipients()
        return self.search([
            ('id', 'in', res_ids),
            ('opt_out', '=', True)
        ]).ids

    def _sms_get_partner_fields(self):
        return ['customer_ids']

    def _sms_get_number_fields(self):
        return []
