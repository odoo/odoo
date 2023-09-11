# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailingCustomer(models.Model):
    """ A model inheriting from mail.thread with a partner field, to test
    mass mailing flows involving checking partner email. """
    _description = 'Mailing with partner'
    _name = 'mailing.test.customer'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char(compute='_compute_email_from', readonly=False, store=True)
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=True)

    @api.depends('customer_id')
    def _compute_email_from(self):
        for mailing in self.filtered(lambda rec: not rec.email_from and rec.customer_id):
            mailing.email_from = mailing.customer_id.email

    def _message_get_default_recipients(self):
        """ Default recipient checks for 'partner_id', here the field is named
        'customer_id'. """
        default_recipients = super()._message_get_default_recipients()
        for record in self:
            if record.customer_id:
                default_recipients[record.id] = {
                    'email_cc': False,
                    'email_to': False,
                    'partner_ids': record.customer_id.ids,
                }
        return default_recipients


class MailingSimple(models.Model):
    """ Model only inheriting from mail.thread to test base mailing features and
    performances. """
    _description = 'Simple Mailing'
    _name = 'mailing.test.simple'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()


class MailingUTM(models.Model):
    """ Model inheriting from mail.thread and utm.mixin for checking utm of mailing
    is caught and set on reply """
    _description = 'Mailing: UTM enabled to test UTM sync with mailing'
    _name = 'mailing.test.utm'
    _inherit = ['mail.thread', 'utm.mixin']

    name = fields.Char()


class MailingBLacklist(models.Model):
    """ Model using blacklist mechanism for mass mailing features. """
    _description = 'Mailing Blacklist Enabled'
    _name = 'mailing.test.blacklist'
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=True)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)

    def _message_get_default_recipients(self):
        """ Default recipient checks for 'partner_id', here the field is named
        'customer_id'. """
        default_recipients = super()._message_get_default_recipients()
        for record in self:
            if record.customer_id:
                default_recipients[record.id] = {
                    'email_cc': False,
                    'email_to': False,
                    'partner_ids': record.customer_id.ids,
                }
        return default_recipients


class MailingOptOut(models.Model):
    """ Model using blacklist mechanism and a hijacked opt-out mechanism for
    mass mailing features. """
    _description = 'Mailing Blacklist / Optout Enabled'
    _name = 'mailing.test.optout'
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    opt_out = fields.Boolean()
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=True)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)

    def _mailing_get_opt_out_list(self, mailing):
        res_ids = mailing._get_recipients()
        opt_out_contacts = set(self.search([
            ('id', 'in', res_ids),
            ('opt_out', '=', True)
        ]).mapped('email_normalized'))
        return opt_out_contacts

    def _message_get_default_recipients(self):
        """ Default recipient checks for 'partner_id', here the field is named
        'customer_id'. """
        default_recipients = super()._message_get_default_recipients()
        for record in self:
            if record.customer_id:
                default_recipients[record.id] = {
                    'email_cc': False,
                    'email_to': False,
                    'partner_ids': record.customer_id.ids,
                }
        return default_recipients

class MailingTestPartner(models.Model):
    _description = 'Mailing Model with partner_id'
    _name = 'mailing.test.partner'
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    partner_id = fields.Many2one('res.partner', 'Customer')


class MailingPerformance(models.Model):
    """ A very simple model only inheriting from mail.thread to test pure mass
    mailing performances. """
    _name = 'mailing.performance'
    _description = 'Mailing: base performance'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char()


class MailingPerformanceBL(models.Model):
    """ Model using blacklist mechanism for mass mailing performance. """
    _name = 'mailing.performance.blacklist'
    _description = 'Mailing: blacklist performance'
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'  # blacklist field to check

    name = fields.Char()
    email_from = fields.Char()
    user_id = fields.Many2one(
        'res.users', 'Responsible',
        tracking=True)
    container_id = fields.Many2one(
        'mail.test.container', 'Meta Container Record',
        tracking=True)
