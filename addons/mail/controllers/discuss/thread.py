# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route
from odoo.addons.mail.controllers.thread import ThreadController


class DiscussThreadController(ThreadController):
    def _filter_message_post_partners(self, thread, partners):
        if thread._name == "discuss.channel":
            domain = [("channel_id", "=", thread.id), ("partner_id", "in", partners.ids)]
            # sudo: discuss.channel.member - filtering partners that are members is acceptable
            return request.env["discuss.channel.member"].sudo().search(domain).partner_id
        return super()._filter_message_post_partners(thread, partners)

    @route()
    def mail_message_post(self, thread_model, thread_id, post_data, context=None, **kwargs):
        if thread_model == 'discuss.channel':
            thread = request.env[thread_model].browse(int(thread_id))
            if not thread.is_member and thread.exists():
                thread._find_or_create_member_for_self()
        return super().mail_message_post(thread_model, thread_id, post_data, context, **kwargs)
