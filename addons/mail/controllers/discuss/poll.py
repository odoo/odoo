from markupsafe import Markup
from werkzeug.exceptions import NotFound

from odoo.http import Controller, request, route
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class PollController(Controller):
    @route("/discuss/poll/create", type="jsonrpc", auth="user", methods=["POST"])
    def poll_create(self, channel_id, question, answers, duration):
        channel = request.env["discuss.channel"].browse(channel_id).exists()
        if not channel:
            raise NotFound()
        notification = (
            Markup("<div class='o_mail_notification'>%s</div>") % self.env._("created a poll %s", question)
        )
        message = channel.message_post(
            body=notification,
            message_type="notification",
            subtype_xmlid="mail.mt_comment",
        )
        poll = request.env["discuss.poll"].create(
            {"duration": duration, "start_message_id": message.id, "question": question}
        )
        for answer in answers:
            request.env["discuss.poll.answer"].create({"poll_id": poll.id, "text": answer})
        poll._bus_send_store(poll)

    @route("/discuss/poll/vote", type="jsonrpc", auth="public", methods=["POST"])
    @add_guest_to_context
    def poll_vote(self, poll_id, answer_ids):
        selected_answers = request.env["discuss.poll.answer"].search(
            [("poll_id", "=", poll_id), ("id", "in", answer_ids)]
        )
        if len(selected_answers) != len(answer_ids):
            raise NotFound()
        selected_answers.voting_partner_ids += request.env.user.partner_id
        selected_answers.poll_id._bus_send_store(selected_answers)
        selected_answers.poll_id._bus_send_store(selected_answers.poll_id, fields=["number_of_votes"])

    @route("/discuss/poll/remove_vote", type="jsonrpc", auth="public", methods=["POST"])
    @add_guest_to_context
    def poll_remove_vote(self, poll_id):
        selected_answers = request.env["discuss.poll.answer"].search(
            [
                ("poll_id", "=", poll_id),
                ("voting_partner_ids", "in", request.env.user.partner_id.ids),
            ]
        )
        if not selected_answers:
            return
        selected_answers.voting_partner_ids -= request.env.user.partner_id
        selected_answers.poll_id._bus_send_store(selected_answers)
        selected_answers.poll_id._bus_send_store(selected_answers.poll_id, fields=["number_of_votes"])
