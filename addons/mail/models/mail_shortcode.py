# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailShortcode(models.Model):
    """ Shortcode
        Canned Responses, allowing the user to defined shortcuts in its message. Should be applied before storing message in database.
        Emoji allowing replacing text with image for visual effect. Should be applied when the message is displayed (only for final rendering).
        These shortcodes are global and are available for every user.
    """

    _name = 'mail.shortcode'
    _description = 'Canned Response / Shortcode'
    source = fields.Char('Shortcut', required=True, index=True, help="The shortcut which must be replaced in the Chat Messages")
    substitution = fields.Text('Substitution', required=True, index=True, help="The escaped html code replacing the shortcut")
    description = fields.Char('Description')
