# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class CustomMessageConfiguration(models.Model):
    _name = 'custom.message.configuration'
    _description = 'Custom Message Configuration'
    _rec_name = 'message_code'

    message_code = fields.Integer(
        string='Message Code',
        required=True,
        help='Unique integer code for the message'
    )

    description = fields.Char(
        string='Message Description',
        required=True,
        help='Short description or message text'
    )

    _sql_constraints = [
        ('unique_message_code', 'unique(message_code)', 'Message Code must be unique.')
    ]
