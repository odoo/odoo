# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.base.models.ir_qweb import keep_query

class MailingLegacy(http.Controller):
    """ Retro compatibility layer for legacy endpoint"""

    @http.route(['/mail/mailing/<int:mailing_id>/unsubscribe'], type='http', website=True, auth='public')
    def mailing_unsubscribe(self, mailing_id, **post):
        return request.redirect(
            f'/mailing/{mailing_id}/unsubscribe?{keep_query("*")}'
        )
