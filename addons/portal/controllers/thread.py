# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers import thread
from odoo.addons.portal.models.mail_thread import add_portal_partner_to_context
from odoo.addons.mail.tools.discuss import Store


class ThreadController(thread.ThreadController):

    @http.route()
    @add_portal_partner_to_context
    def mail_thread_data(self, thread_model, thread_id, request_list, **kwargs):
        if request.env["res.partner"]._get_portal_partner_from_context():
            thread = request.env[thread_model].sudo().search([("id", "=", thread_id)])
            return Store(thread, request_list=request_list).get_result()
        return super().mail_thread_data(thread_model, thread_id, request_list, **kwargs)

    @http.route()
    @add_portal_partner_to_context
    def mail_message_post(
        self, thread_model, thread_id, post_data, context=None, **kwargs
    ):
        if request.env["res.partner"]._get_portal_partner_from_context():
            return super().mail_message_post(
                thread_model,
                thread_id,
                post_data,
                {"mail_create_nosubscribe": True},
                **kwargs
            )
        return super().mail_message_post(
            thread_model, thread_id, post_data, context, **kwargs
        )

    def _get_thread(self, thread_model, thread_id, sudo=False):
        if request.env["res.partner"]._get_portal_partner_from_context():
            sudo = True
        return super()._get_thread(thread_model, thread_id, sudo)

    def _get_allowed_message_post_params(self):
        post_params = super()._get_allowed_message_post_params()
        post_params.add("author_id")
        return post_params

    def _prepare_post_data(self, post_data, thread, special_mentions, **kwargs):
        post_data = super()._prepare_post_data(post_data, thread, special_mentions, **kwargs)
        if portal_partner := request.env["res.partner"]._get_portal_partner_from_context():
            post_data["author_id"] = portal_partner.id
        return post_data
