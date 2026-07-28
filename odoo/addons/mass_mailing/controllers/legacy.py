# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug

from odoo import http
from odoo.http import request


class MailingLegacy(http.Controller):
    """ Retro compatibility layer for legacy endpoint"""

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', website=True, auth='public')
    def mailing_unsubscribe(self, mailing_id, email=None, res_id=None, token="", **post):
        """ Old route, using mail/mailing prefix, and outdated parameter names """
        params = werkzeug.urls.url_encode(
            dict(**post, document_id=res_id, email=email, hash_token=token)
        )
        return request.redirect(
            f'/mailing/{mailing_id}/unsubscribe?{params}'
        )
