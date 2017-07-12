# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailBlackList(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _name = 'mail.blacklist'
    _description = 'Mail Blacklist'
    _order = 'email'
    _rec_name = 'email'

    email = fields.Char(string='Email Address', required=True)

    _sql_constraints = [
        ('unique_email', 'unique (email)', 'Email address already exists!')
    ]
