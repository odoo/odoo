# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.portal.controllers.mail import MailController
from odoo.addons.knowledge.controllers.main import KnowledgeController
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import Store
from werkzeug.exceptions import Forbidden


class ArticleThreadController(KnowledgeController):

    @http.route('/knowledge/thread/create', type='json', auth='user')
    def create_thread(self, article_id, article_anchor_text="", fields=["id", "article_anchor_text"]):
        article_thread = request.env['knowledge.article.thread'].create({
            'article_id': article_id,
            'article_anchor_text': article_anchor_text,
        })
        return {field: article_thread[field] for field in fields}

    @http.route('/knowledge/thread/resolve', type='http', auth='user')
    def resolve_thread(self, res_id, token):
        _, thread, redirect = MailController._check_token_and_record_or_redirect('knowledge.article.thread', int(res_id), token)
        if not thread or not thread.article_id.user_can_write:
            return redirect
        if not thread.is_resolved:
            thread.is_resolved = True
        return self.redirect_to_article(thread.article_id.id, show_resolved_threads=True)


class KnowledgeThreadController(ThreadController):

    @http.route("/knowledge/threads/messages", methods=["POST"], type="json", auth="user")
    def mail_threads_messages(self, thread_model, thread_ids, limit=30):
        thread_ids = [int(thread_id) for thread_id in thread_ids]
        output = {}
        for thread_id in thread_ids:
            domain = self._prepare_thread_messages_domain(thread_model, thread_id)
            # TODO ABD optimize duration. Currently very slow because of mail.message._to_store
            res = request.env["mail.message"]._message_fetch(domain, limit=limit)
            messages = res.pop("messages")
            output[thread_id] = {
                **res,
                "data": Store(messages, for_current_user=True).get_result(),
                "messages": Store.many_ids(messages),
            }
        return output

    def _prepare_thread_messages_domain(self, thread_model, thread_id):
        return [
            ("res_id", "=", int(thread_id)),
            ("model", "=", thread_model),
            ("message_type", "=", "comment"),  # only user input
            ("subtype_id", "=", request.env.ref('mail.mt_comment').id),  # comments in threads are sent as notes
            ("is_internal", "=", False)  # respect internal users only flag
        ]
