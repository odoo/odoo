from markupsafe import Markup

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store


class DiscussPoll(models.Model):
    _name = "discuss.poll"
    _inherit = ["bus.listener.mixin"]

    start_message_id = fields.Many2one("mail.message", ondelete="cascade", required=True)
    end_message_id = fields.Many2one("mail.message", ondelete="cascade")
    question = fields.Char(required=True)
    answer_ids = fields.One2many("discuss.poll.answer", "poll_id")
    duration = fields.Integer(required=True)
    closed = fields.Boolean()
    number_of_votes = fields.Integer(compute="_compute_number_of_votes")
    winning_answer_id = fields.One2many(
        "discuss.poll.answer", "poll_id", compute="_compute_winning_answer"
    )

    @api.depends("answer_ids.voting_partner_ids")
    def _compute_number_of_votes(self):
        for poll in self:
            poll.number_of_votes = sum(len(answer.voting_partner_ids) for answer in poll.answer_ids)

    @api.depends("closed")
    def _compute_winning_answer(self):
        for poll in self:
            if not poll.answer_ids.voting_partner_ids or not poll.closed:
                poll.winning_answer_id = None
                continue
            max_vote = max(answer.percent_votes for answer in poll.answer_ids)
            winners = [answer for answer in poll.answer_ids if answer.percent_votes == max_vote]
            poll.winning_answer_id = winners[0] if len(winners) == 1 else None

    def _to_store_defaults(self):
        return [
            "closed",
            "create_date",
            "duration",
            "question",
            "number_of_votes",
            Store.Attr("start_message_id", lambda p: p.start_message_id.id),
            Store.Attr("end_message_id", lambda p: p.end_message_id.id),
            Store.Many("answer_ids"),
            Store.One("winning_answer_id"),
        ]

    def _bus_channel(self):
        return self.env["discuss.channel"].browse(self.start_message_id.res_id)._bus_channel()

    @api.model
    def _end_expired_polls(self):
        self.env.cr.execute("""
            SELECT id
              FROM discuss_poll
             WHERE closed IS NOT TRUE
        """)
        # AND (create_date + (duration * INTERVAL '1 hour')) < NOW();
        expired_polls = self.env["discuss.poll"].browse([r[0] for r in self.env.cr.fetchall()])
        expired_polls.closed = True
        for poll in expired_polls:
            poll_link = Markup('<a href="#" data-oe-type="highlight" data-oe-id="%s">%s</a>') % (
                poll.start_message_id.id,
                poll.question,
            )
            notification_text = (
                Markup("""<div class="o_mail_notification">%s</div>""")
                % self.env._(
                    "%(author_name)s's poll %(poll_link)s has closed",
                )
                % {
                    "author_name": poll.start_message_id.author_id.name,
                    "poll_link": poll_link,
                }
            )
            poll.end_message_id = (
                self.env["discuss.channel"]
                .browse(poll.start_message_id.res_id)
                .message_post(
                    author_id=poll.start_message_id.author_id.id,
                    message_type="notification",
                    subtype_xmlid="mail.mt_comment",
                    body=notification_text,
                )
            )
        expired_polls._bus_send_store(expired_polls)
