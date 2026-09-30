# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingSubscriptionOptout(models.Model):
    """ Reason for opting out of mailing lists or for blacklisting. """
    _name = 'mailing.subscription.optout'
    _description = 'Mailing Subscription Reason'
    _order = 'sequence ASC, create_date DESC, id DESC'

    name = fields.Char(string='Reason', translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    is_feedback = fields.Boolean(string='Ask For Feedback')
