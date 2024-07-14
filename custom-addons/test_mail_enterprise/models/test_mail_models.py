# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailTestActivitySMSVoip(models.Model):
    """ A model inheriting from most phone- and mail- related mixin in order
    to test activities with a full setup. """
    _description = 'VOIP SMS Mailing Blacklist Enabled with activities'
    _name = 'mail.test.activity.bl.sms.voip'
    _inherit = [
        'mail.thread.blacklist',
        'mail.thread.phone',
        'mail.activity.mixin',
        'voip.queue.mixin',
    ]
    _mailing_enabled = True
    _order = 'name asc, id asc'
    _primary_email = 'email_from'

    name = fields.Char()
    subject = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer')
    email_from = fields.Char()
    mobile_nbr = fields.Char()
    opt_out = fields.Boolean()
    phone_nbr = fields.Char()

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']

    def _mailing_get_opt_out_list(self, mailing):
        res_ids = mailing._get_recipients()
        opt_out_contacts = set(self.search([
            ('id', 'in', res_ids),
            ('opt_out', '=', True),
        ]).mapped('email_normalized'))
        return opt_out_contacts

    def _mailing_get_opt_out_list_sms(self, mailing):
        res_ids = mailing._get_recipients()
        return self.search([
            ('id', 'in', res_ids),
            ('opt_out', '=', True),
        ]).ids

    def _phone_get_number_fields(self):
        return ['phone_nbr', 'mobile_nbr']
