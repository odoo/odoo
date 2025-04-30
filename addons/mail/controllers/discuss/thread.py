# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.thread import ThreadController


class DiscussThreadController(ThreadController):
    def _filter_message_post_partners(self, thread, partners):
        if thread._name != "discuss.channel":
            return super()._filter_message_post_partners(thread, partners)
        if thread.channel_type == "channel":
            if group := ((thread.parent_channel_id or thread).group_public_id):
                domain = [("id", "in", partners.ids), ("user_ids.all_group_ids", "in", group.ids)]
                # sudo: res.partner - filtering partners that have the correct group is acceptable.
                partners = self.env["res.partner"].sudo().search(domain)
            # Non-internal users can only mention members of the channel which is handled below.
            if self.env.user._is_internal():
                return partners
        domain = [("channel_id", "=", thread.id), ("partner_id", "in", partners.ids)]
        # sudo: discuss.channel.member - filtering partners that are members is acceptable
        return self.env["discuss.channel.member"].sudo().search(domain).partner_id
