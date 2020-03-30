# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MassMailTest(models.Model):
    """ A very simple model only inheriting from mail.thread to test pure mass
    mailing features and base performances. """
    _description = 'Simple Mass Mailing Model'
    _name = 'mass.mail.test'
    _inherit = ['mail.thread', 'mail.address.mixin']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()


class MassMailTestBlacklist(models.Model):
    """ Model using blacklist mechanism for mass mailing. """
    _description = 'Mass Mailing Model w Blacklist'
    _name = 'mass.mail.test.bl'
    _inherit = ['mail.thread.blacklist']

    _primary_email = 'email_from'  # blacklist field to check

    name = fields.Char()
    email_from = fields.Char()
    user_id = fields.Many2one(
        'res.users', 'Responsible',
        tracking=True)
    umbrella_id = fields.Many2one(
        'mail.test', 'Meta Umbrella Record',
        tracking=True)

class MailingUTM(models.Model):
    """ Model inheriting from mail.thread and utm.mixin for checking utm of mailing is caught and set on reply """
    _description = 'Mailing: UTM enabled to test UTM sync with mailing'
    _name = 'mailing.test.utm'
    _inherit = ['mail.thread', 'utm.mixin']

    name = fields.Char()
