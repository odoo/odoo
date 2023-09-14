# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers import thread
from odoo.addons.portal.models.mail_thread import check_portal_access_token


class ThreadController(thread.ThreadController):

    @http.route()
    @check_portal_access_token
    def mail_thread_data(self, thread_model, thread_id, request_list):
        portal_token = request.env["mail.thread"]._get_access_token_from_context()
        if portal_token:
            thread = request.env[thread_model].with_context(active_test=False).sudo().search([("id", "=", thread_id)])
            return thread._get_mail_thread_data(request_list)
        return super().mail_thread_data(thread_model, thread_id, request_list)

    @http.route()
    @check_portal_access_token
    def mail_message_post(self, thread_model, thread_id, post_data, context=None):
        return super().mail_message_post(thread_model, thread_id, post_data, context)
