# -*- coding: utf-8 -*-
import cgi
import re

from openerp import api, fields, models


class ImChatShortcode(models.Model):
    """ Shortcode
        Canned Responses, allowing the user to defined shortcuts in its chat message.
        These shortcode are globals and are available for every user. Smiley use this mecanism.
    """

    _name = 'im_chat.shortcode'
    _description = 'Canned Response / Shortcode'

    source = fields.Char('Shortcut', required=True, index=True, help="The shortcut which must be replace in the Chat Messages")
    substitution = fields.Char('Substitution', required=True, index=True, help="The excaped html code replacing the shortcut")
    description = fields.Char('Description')

    @api.model
    def create(self, values):
        if values.get('substitution'):
            values['substitution'] = self._sanitize_shorcode(values['substitution'])
        return super(ImChatShortcode, self).create(values)

    @api.multi
    def write(self, values):
        if values.get('substitution'):
            values['substitution'] = self._sanitize_shorcode(values['substitution'])
        return super(ImChatShortcode, self).write(values)

    def _sanitize_shorcode(self, substitution):
        """ Sanitize the shortcode substitution :
                 - HTML substitution : only allow the img tag (smiley)
                 - escape other substitutions to avoid XSS
        """
        is_img_tag = re.match(r'''^<img\s+src=('|")([^'"]*)\1\s*/?>$''', substitution, re.M|re.I)
        if is_img_tag:
            return substitution
        return cgi.escape(substitution)

    @api.model
    def replace_shortcode(self, message):
        for shortcode in self.search([]):
            regex = '(?:^|\s)(%s)(?:\s|$)' % re.escape(shortcode.source)
            message = re.sub(regex, " " + shortcode.substitution + " ", message)
        return message
