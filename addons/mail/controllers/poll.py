from werkzeug.exceptions import NotFound

from odoo.addons.mail.tools.discuss import add_guest_to_context, Store
from odoo.fields import Command
from odoo.http import Controller, route


class PollController(Controller):
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
        thread = (
            self.env[thread_model]._get_thread_with_access(thread_id, mode="read")
            if self.env.user._is_internal()
            else None
        )
        if not thread:
            raise NotFound()
        message = thread.message_post(
            body="", message_type="mail_poll", subtype_xmlid="mail.mt_comment"
        )
        # sudo - mail.poll: internal user can create poll on an accessible thread.
        poll = (
            self.env["mail.poll"]
            .sudo()
            .create(
                {
                    "allow_multiple_options": allow_multiple_options,
                    "option_ids": [
                        Command.create({"option_label": label}) for label in option_labels
                    ],
                    "poll_duration": duration,
                    "poll_question": question,
                    "start_message_id": message.id,
                }
            )
        )
        Store(bus_channel=thread).add(poll).bus_send()

    @route("/mail/poll/end", type="jsonrpc", auth="user", methods=["POST"])
    def poll_end(self, poll_id):
        # sudo - mail.poll: creator of the poll can end it prematurely.
        poll_sudo = (
            self.env["mail.poll"]
            .sudo()
            .search_fetch(
                [
                    ("id", "=", poll_id),
                    ("create_uid", "=", self.env.user.id),
                    ("end_message_id", "=", False),
                ]
            )
        )
        if not poll_sudo:
            raise NotFound()
        poll_sudo._end_and_notify()

    @route("/mail/poll/delete", type="jsonrpc", auth="user", methods=["POST"])
    def poll_delete(self, poll_id):
        # sudo - mail.poll: creator of the poll can delete it.
        if (
            poll_sudo := self.env["mail.poll"]
            .sudo()
            .search_fetch([("id", "=", poll_id), ("create_uid", "=", self.env.user.id)])
        ):
            poll_sudo.unlink()

    @route("/mail/poll/vote", type="jsonrpc", auth="public", methods=["POST"])
    @add_guest_to_context
    def poll_vote(self, poll_id, option_ids):
        options_sudo = (
            self.env["mail.poll.option"]
            .sudo()
            .search_fetch([("poll_id", "=", poll_id), ("id", "in", option_ids)])
        )
        thread = self.env[options_sudo.poll_id.start_message_id.model]._get_thread_with_access(
            options_sudo.poll_id.start_message_id.res_id, mode="read"
        )
        if not thread:
            raise NotFound()
        guest = self.env["mail.guest"]._get_guest_from_context()
        # sudo - mail.poll.vote: user can create vote on poll of accessible thread.
        self.env["mail.poll.vote"].sudo().create(
            [
                {
                    "option_id": option.id,
                    "guest_id": guest.id if self.env.user._is_public() else None,
                    "user_id": self.env.user.id if not self.env.user._is_public() else None,
                }
                for option in options_sudo
            ]
        )
        self_bus_channel = guest if self.env.user._is_public() else self.env.user
        Store(bus_channel=self_bus_channel).add(options_sudo, ["selected_by_self"]).bus_send()
        Store(bus_channel=thread).add(
            options_sudo.poll_id.option_ids, ["number_of_votes", "vote_percentage"]
        ).bus_send()

    @route("/mail/poll/remove_vote", type="jsonrpc", auth="public", methods=["POST"])
    @add_guest_to_context
    def poll_remove_vote(self, poll_id):
        # sudo - mail.poll.vote: removing/accessing self vote is allowed.
        votes_sudo = (
            self.env["mail.poll.vote"]
            .sudo()
            .search_fetch([("option_id.poll_id", "=", poll_id), ("is_self_vote", "=", True)])
        )
        if not votes_sudo:
            raise NotFound()
        options_sudo = votes_sudo.option_id
        poll_sudo = votes_sudo.option_id.poll_id
        votes_sudo.unlink()
        guest = self.env["mail.guest"]._get_guest_from_context()
        Store(bus_channel=guest if self.env.user._is_public() else self.env.user).add(
            options_sudo, ["selected_by_self"]
        ).bus_send()
        thread = self.env[options_sudo.poll_id.start_message_id.model].browse(
            options_sudo.poll_id.start_message_id.res_id
        )
        Store(bus_channel=thread).add(
            poll_sudo.option_ids, ["number_of_votes", "vote_percentage"]
        ).bus_send()
