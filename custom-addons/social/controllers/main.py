# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.tools import plaintext2html
from werkzeug.exceptions import Forbidden


class SocialValidationException(Exception):
    def __init__(self, message, documentation_link=False, documentation_link_label=False, documentation_link_icon_class=False):
        """This custom exception allow us to show either a plain text error message or a error message with a redirect link
        to the documentation.
        : param str message: error message to be shown to the end-user.
        : param str documentation_link: allows us to put a link to the documentation of respective social media.
        : param str documentation_link_label: a label to be shown to the end-user of the documentation_link.
        : param str documentation_link_icon_class: font-awsome icon class of the respective social media.
        """
        self.message = message
        self.documentation_link = documentation_link
        self.documentation_link_label = documentation_link_label
        self.documentation_link_icon_class = documentation_link_icon_class
        super().__init__(message)

    def get_message(self):
        return plaintext2html(self.message)

    def get_documentation_data(self):
        return {
            'documentation_link': self.documentation_link,
            'documentation_link_label': self.documentation_link_label,
            'documentation_link_icon_class': self.documentation_link_icon_class,
        }

class SocialController(http.Controller):

    def _get_social_stream_post(self, stream_post_id, media_type):
        """ Small utility method that fetches the post and checks it belongs
        to the correct media_type """
        stream_post = request.env['social.stream.post'].search([
            ('id', '=', stream_post_id),
            ('stream_id.account_id.media_id.media_type', '=', media_type),
        ])
        if not stream_post:
            raise Forbidden()

        return stream_post
