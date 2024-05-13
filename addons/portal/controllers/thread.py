# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers import thread
from odoo.addons.portal.models.mail_thread import check_portal_access
from odoo.addons.portal.controllers.mail import _check_special_access


class ThreadController(thread.ThreadController):

    @http.route()
    @check_portal_access
    def mail_thread_data(self, thread_model, thread_id, request_list):
        thread = request.env[thread_model].sudo().search([("id", "=", thread_id)])
        if thread._get_portal_access():
            return thread._get_mail_thread_data(request_list)
        return super().mail_thread_data(thread_model, thread_id, request_list)

    @http.route()
    @check_portal_access
    def mail_message_post(
        self, thread_model, thread_id, post_data, context=None, **kwargs
    ):
        token = kwargs.get("token")
        _hash = kwargs.get("hash")
        pid = kwargs.get("pid")
        if token or (_hash and pid):
            has_access = _check_special_access(
                thread_model, thread_id, token, _hash, pid
            )
            if has_access:
                request.update_context(
                    portal_token=token,
                    portal_hash=_hash,
                    portal_pid=pid,
                )
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

    def _get_thread(self, thread_model, thread_id):
        thread = (
            request.env[thread_model]
            .with_context(active_test=False)
            .sudo()
            .search([("id", "=", thread_id)])
        )
        if thread._get_portal_access():
            return thread.with_context(active_test=True)
        return super()._get_thread(thread_model, thread_id)
