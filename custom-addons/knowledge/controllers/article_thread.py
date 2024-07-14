# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.portal.controllers.mail import MailController
from odoo.addons.knowledge.controllers.main import KnowledgeController
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from werkzeug.exceptions import Forbidden


class ArticleThreadController(KnowledgeController):

    @http.route('/knowledge/thread/resolve', type='http', auth='user')
    def resolve_thread(self, res_id, token):
        _, thread, redirect = MailController._check_token_and_record_or_redirect('knowledge.article.thread', int(res_id), token)
        if not thread or not thread.article_id.user_can_write:
            return redirect
        if not thread.is_resolved:
            thread.is_resolved = True
        return self.redirect_to_article(thread.article_id.id, show_resolved_threads=True)


class KnowledgeThreadController(ThreadController):

    @http.route()
    def mail_thread_messages(self, thread_model, thread_id, **kwargs):
        """Portal users doesn't have access to the mail.message model but we want them to be able to
        see the messages from a `knowledge.article.thread` on which they can access, if access rules
        applies to them.
        So for them, we check if they indeed have access to the article linked to the thread and if
        that's the case we sudo the search to return the messages.
        """
        if request.env.user._is_portal() and thread_model == 'knowledge.article.thread':
            thread = request.env['knowledge.article.thread'].browse(thread_id).exists()
            if not thread or not thread.article_id.user_has_access:
                raise Forbidden()
            domain = [
                ("res_id", "=", int(thread_id)),
                ("model", "=", thread_model),
                ("message_type", "=", "comment"), # only user input
                ("subtype_id", "=", request.env.ref('mail.mt_comment').id), # comments in threads are sent as notes
                ("is_internal", "=", False) # respect internal users only flag
            ]
            res = request.env["mail.message"].sudo()._message_fetch(domain, **kwargs)
            return {**res, "messages": res["messages"].message_format()}
        return super().mail_thread_messages(thread_model, thread_id, **kwargs)
