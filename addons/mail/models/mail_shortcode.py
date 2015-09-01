# -*- coding: utf-8 -*-
import cgi
import re

from openerp import api, fields, models


class MailShortcode(models.Model):
    """ Shortcode
        Canned Responses, allowing the user to defined shortcuts in its message. Should be applied before storing message in database.
        Emoji allowing replacing text with image for visual effect. Should be applied when the message is displayed (only for final rendering).
        These shortcodes are global and are available for every user.
    """

    _name = 'mail.shortcode'
    _description = 'Canned Response / Shortcode'

    source = fields.Char('Shortcut', required=True, index=True, help="The shortcut which must be replace in the Chat Messages")
    substitution = fields.Char('Substitution', required=True, index=True, help="The excaped html code replacing the shortcut")
    description = fields.Char('Description')
    shortcode_type = fields.Selection([('image', 'Smiley'), ('text', 'Canned Response')], required=True, default='text',
        help="* Smiley are only used for HTML code to display an image "\
             "* Text (default value) is use to substitute text with another text")

    @api.model
    def create(self, values):
        if values.get('substitution'):
            values['substitution'] = self._sanitize_shorcode(values['substitution'])
        return super(MailShortcode, self).create(values)

    @api.multi
    def write(self, values):
        if values.get('substitution'):
            values['substitution'] = self._sanitize_shorcode(values['substitution'])
        return super(MailShortcode, self).write(values)

    def _sanitize_shorcode(self, substitution):
        """ Sanitize the shortcode substitution :
                - HTML substitution : only allow the img tag (emoji)
                - escape other substitutions to avoid XSS
        """
        is_img_tag = re.match(r'''^<img\s+src=('|")([^'"]*)\1\s*/?>$''', substitution, re.M | re.I)
        if is_img_tag:
            return substitution
        return cgi.escape(substitution)

    @api.model
    def apply_shortcode(self, message, shortcode_type=None):
        """ Apply the substitution on the given text
            :param message : the text where the shortcode will be applied
            :param shortcode_type : shortcode type that should be applied during the substitution
        """
        domain = []
        if shortcode_type:
            domain.append(('shortcode_type', '=', shortcode_type))
        for shortcode in self.search(domain):
            regex = '(?:^|\s)(%s)(?:\s|$)' % re.escape(shortcode.source)
            message = re.sub(regex, " " + shortcode.substitution + " ", message)
        return message
