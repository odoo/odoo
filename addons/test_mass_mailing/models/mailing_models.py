# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailingTestCustomer(models.Model):
    """ A model inheriting from mail.thread with a partner field, to test
    mass mailing flows involving checking partner email. """
    _name = 'mailing.test.customer'
    _description = 'Mailing with partner'
    _inherit = ['mail.thread']

    name = fields.Char()
    email_from = fields.Char(compute='_compute_email_from', readonly=False, store=True)
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=True)

    @api.depends('customer_id')
    def _compute_email_from(self):
        for mailing in self.filtered(lambda rec: not rec.email_from and rec.customer_id):
            mailing.email_from = mailing.customer_id.email

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']


class MailingTestSimple(models.Model):
    """ Model only inheriting from mail.thread to test base mailing features and
    performances. """
    _name = 'mailing.test.simple'
    _description = 'Simple Mailing'
    _inherit = ['mail.thread']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()


class MailingTestUtm(models.Model):
    """ Model inheriting from mail.thread and utm.mixin for checking utm of mailing
    is caught and set on reply """
    _name = 'mailing.test.utm'
    _description = 'Mailing: UTM enabled to test UTM sync with mailing'
    _inherit = ['mail.thread', 'utm.mixin']

    name = fields.Char()


class MailingTestBlacklist(models.Model):
    """ Model using blacklist mechanism for mass mailing features. """
    _name = 'mailing.test.blacklist'
    _description = 'Mailing Blacklist Enabled'
    _inherit = ['mail.thread.blacklist']
    _order = 'name ASC, id DESC'
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=True)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']


class MailingTestOptout(models.Model):
    """ Model using blacklist mechanism and a hijacked opt-out mechanism for
    mass mailing features. """
    _name = 'mailing.test.optout'
    _description = 'Mailing Blacklist / Optout Enabled'
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    opt_out = fields.Boolean()
    customer_id = fields.Many2one('res.partner', 'Customer', tracking=True)
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True)

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id']

    def _mailing_get_opt_out_list(self, mailing):
        res_ids = mailing._get_recipients()
        opt_out_contacts = set(self.search([
            ('id', 'in', res_ids),
            ('opt_out', '=', True)
        ]).mapped('email_normalized'))
        return opt_out_contacts


class MailingTestPartner(models.Model):
    _name = 'mailing.test.partner'
    _description = 'Mailing Model with partner_id'
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


class MailingPerformanceBlacklist(models.Model):
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
