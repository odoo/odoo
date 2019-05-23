# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailMessage(models.Model):
    """ Override MailMessage class in order to add a new type: SMS messages.
    Those messages comes with their own notification method, using SMS
    gateway. """
    _inherit = 'mail.message'

    message_type = fields.Selection(selection_add=[('sms', 'SMS')])
