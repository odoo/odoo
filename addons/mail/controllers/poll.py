from datetime import timedelta

from odoo import fields
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store
from odoo.fields import Command, Domain
from odoo.http import route


class PollController(ThreadController):
    @route("/mail/poll/create", type="jsonrpc", auth="user", methods=["POST"])
    def poll_create(
        self,
        duration,
        option_labels,
        question,
        thread_id,
        thread_model,
        allow_multiple_options=False,
    ):
        if not self.env.user._is_internal():
            return
        thread = self._get_thread_with_access_for_post(thread_model, thread_id)
        if not thread:
            return
        message = thread.message_post(
            body="", message_type="comment", subtype_xmlid="mail.mt_comment",
        )
        end_dt = fields.Datetime.now() + timedelta(minutes=duration)
        poll_values = {
            "allow_multiple_options": allow_multiple_options,
            "option_ids": [Command.create({"option_label": label}) for label in option_labels],
            "poll_end_dt": end_dt,
            "poll_question": question,
            "start_message_id": message.id,
        }
        # sudo - mail.poll: internal user can create poll on an accessible thread.
        poll = self.env["mail.poll"].sudo().create(poll_values)
        self.env.ref("mail.ir_cron_mail_end_polls")._trigger(end_dt)
        Store(**thread._get_store_target()).add(poll).bus_send()
        return poll.id

    @route("/mail/poll/end", type="jsonrpc", auth="user", methods=["POST"])
    def poll_end(self, poll_id):
        poll_domain = Domain("id", "=", poll_id) & Domain("end_message_id", "=", False)
        if not self.env.user._is_admin():
            poll_domain &= Domain("create_uid", "=", self.env.user.id)
        # sudo - mail.poll: creator of the poll or admins can end a poll prematurely.
        self.env["mail.poll"].sudo().search_fetch(poll_domain)._end_and_notify()

    @route("/mail/poll/delete", type="jsonrpc", auth="user", methods=["POST"])
    def poll_delete(self, poll_id):
        poll_domain = Domain("id", "=", poll_id)
        if not self.env.user._is_admin():
            poll_domain &= Domain("create_uid", "=", self.env.user.id)
        # sudo - mail.poll: creator of the poll or admins can delete a poll.
        self.env["mail.poll"].sudo().search_fetch(poll_domain).unlink()

    @route("/mail/poll/vote", type="jsonrpc", auth="public", methods=["POST"])
    @add_guest_to_context
    def poll_vote(self, poll_id, option_ids):
        options_domain = [("poll_id", "=", poll_id), ("id", "in", option_ids)]
        # sudo - mail.poll.option: can access poll options, vote access is validated
        # by "_get_thread_with_access_for_post" afterwards.
        options_sudo = self.env["mail.poll.option"].sudo().search_fetch(options_domain)
        start_message = options_sudo.poll_id.start_message_id
        thread = self._get_thread_with_access_for_post(start_message.model, start_message.res_id)
        if not thread:
            return
        user, guest = self.env["res.users"]._get_current_persona()
        # sudo - mail.poll.vote: user can create vote on poll of accessible thread.
        self.env["mail.poll.vote"].sudo().create(
            [
                {
                    "option_id": option.id,
                    "guest_id": guest.id,
                    "user_id": user.id,
                }
                for option in options_sudo
            ]
        )
        self_bus_channel = guest if self.env.user._is_public() else self.env.user
        Store(bus_channel=self_bus_channel).add(options_sudo, ["selected_by_self"]).bus_send()
        Store(**thread._get_store_target()).add(
            options_sudo.poll_id.option_ids, ["number_of_votes", "vote_percentage"]
        ).bus_send()

    @route("/mail/poll/remove_vote", type="jsonrpc", auth="public", methods=["POST"])
    @add_guest_to_context
    def poll_remove_vote(self, poll_id):
        votes_domain = [("option_id.poll_id", "=", poll_id), ("is_self_vote", "=", True)]
        # sudo - mail.poll.vote: removing/accessing self vote is allowed.
        votes_sudo = self.env["mail.poll.vote"].sudo().search_fetch(votes_domain)
        user, guest = self.env["res.users"]._get_current_persona()
        if not votes_sudo:
            # sudo - mail.poll: accessing poll to re-send "selected_by_self" to the current
            # user is allowed.
            poll_sudo = self.env["mail.poll"].sudo().search_fetch([("id", "=", poll_id)])
            Store(bus_channel=user or guest).add(
                poll_sudo.option_ids, ["selected_by_self"]
            ).bus_send()
            return
        options_sudo = votes_sudo.option_id
        poll_sudo = votes_sudo.option_id.poll_id
        votes_sudo.unlink()
        Store(bus_channel=user or guest).add(options_sudo, ["selected_by_self"]).bus_send()
        thread = self.env[options_sudo.poll_id.start_message_id.model].browse(
            options_sudo.poll_id.start_message_id.res_id
        )
        Store(**thread._get_store_target()).add(
            poll_sudo.option_ids, ["number_of_votes", "vote_percentage"]
        ).bus_send()
