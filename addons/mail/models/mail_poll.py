# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store


class MailPoll(models.Model):
    _description = "Poll"
    _name = "mail.poll"

    allow_multiple_options = fields.Boolean()
    end_message_id = fields.Many2one("mail.message", ondelete="cascade", index=True)
    option_ids = fields.One2many("mail.poll.option", "poll_id", required=True)
    poll_end_dt = fields.Datetime(index=True)
    poll_question = fields.Char(required=True)
    start_message_id = fields.Many2one(
        "mail.message", ondelete="cascade", required=True, index=True
    )
    winning_option_id = fields.Many2one("mail.poll.option", compute="_compute_winning_option_ids")

    _unique_start_message_id = models.Constraint(
        "UNIQUE(start_message_id)", "A start message can only be linked to one poll."
    )
    _unique_end_message_id = models.Constraint(
        "UNIQUE(end_message_id)", "An end message can only be linked to one poll."
    )

    @api.depends("end_message_id", "option_ids.vote_percentage")
    def _compute_winning_option_ids(self):
        ongoing_polls = self.filtered(lambda poll: not poll.end_message_id)
        ongoing_polls.winning_option_id = None
        for poll in self - ongoing_polls:
            max_vote = max(option.vote_percentage for option in poll.option_ids)
            winners = [
                option
                for option in poll.option_ids
                if option.vote_percentage == max_vote and option.vote_percentage > 0
            ]
            poll.winning_option_id = winners[0] if len(winners) == 1 else None

    def _to_store_defaults(self, target):
        return [
            "allow_multiple_options",
            "create_date",
            "create_uid",
            "end_message_id",
            Store.Many("option_ids"),
            "poll_end_dt",
            "poll_question",
            "start_message_id",
            "winning_option_id",
        ]

    def _end_and_notify(self):
        thread_by_message = self.start_message_id._record_by_message()
        for poll in self:
            thread = thread_by_message[poll.start_message_id]
            poll.end_message_id = thread.message_post(
                body="", message_type="mail_poll", subtype_xmlid="mail.mt_comment"
            )
            Store(**thread._get_store_target()).add(poll).bus_send()

    @api.model
    def _end_expired_polls(self):
        self.env["mail.poll"].search_fetch([("poll_end_dt", "<=", "now")])._end_and_notify()

    @api.ondelete(at_uninstall=False)
    def _poll_on_delete(self):
        thread_by_message = (self.start_message_id | self.end_message_id)._record_by_message()
        for message in self.start_message_id | self.end_message_id:
            Store(**thread_by_message[message]._get_store_target()).add(
                message,
                [
                    Store.Many("started_poll_ids", [], mode="DELETE"),
                    Store.Many("ended_poll_ids", [], mode="DELETE"),
                ],
            ).bus_send()
