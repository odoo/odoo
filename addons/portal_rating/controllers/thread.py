# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.mail.controllers import thread
from odoo.addons.portal.models.mail_thread import check_portal_access_token


class ThreadController(thread.ThreadController):

    def _get_allowed_message_post_params(self):
        post_params = super()._get_allowed_message_post_params()
        post_params.add("rating_value")
        return post_params

    @http.route()
    @check_portal_access_token
    def mail_message_post(self, thread_model, thread_id, post_data, context=None):
        if post_data.get('rating_value'):
            post_data['rating_feedback'] = post_data.pop('rating_feedback', post_data.get("body"))
        return super().mail_message_post(thread_model, thread_id, post_data, context)
