# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import NotFound

from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController


class DiscussThreadController(ThreadController):
    def _prepare_post_data(self, post_data, thread, **kwargs):
        partner, guest = request.env["res.partner"]._get_current_persona()
        if thread._name == "discuss.channel" and not partner and not guest:
            raise NotFound()
        return super()._prepare_post_data(post_data, thread, **kwargs)

    def _filter_message_post_partners(self, thread, partners):
        if thread._name == "discuss.channel":
            domain = [("channel_id", "=", thread.id), ("partner_id", "in", partners.ids)]
            # sudo: discuss.channel.member - filtering partners that are members is acceptable
            return request.env["discuss.channel.member"].sudo().search(domain).partner_id
        return super()._filter_message_post_partners(thread, partners)
