# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.exceptions import UserError


class DiscussThreadController(ThreadController):
    def _filter_message_post_partners(self, thread, partners):
        if thread._name == "discuss.channel":
            domain = [("channel_id", "=", thread.id), ("partner_id", "in", partners.ids)]
            # sudo: discuss.channel.member - filtering partners that are members is acceptable
            return request.env["discuss.channel.member"].sudo().search(domain).partner_id
        return super()._filter_message_post_partners(thread, partners)

    def _check_message_post_access(self, thread):
        if thread._name == "discuss.channel" and thread._is_read_only():
            raise UserError(_("You cannot post inside a read only channel."))
        return super()._check_message_post_access(thread)
