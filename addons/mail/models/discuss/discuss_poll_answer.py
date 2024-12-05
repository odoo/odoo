# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store
from math import floor


class DiscussPollAnswer(models.Model):
    _name = "discuss.poll.answer"

    poll_id = fields.Many2one("discuss.poll")
    text = fields.Char()
    voting_partner_ids = fields.Many2many("res.partner")
    percent_votes = fields.Integer(compute="_compute_percent_votes")

    @api.depends("poll_id.number_of_votes", "voting_partner_ids")
    def _compute_percent_votes(self):
        for answer in self:
            answer.percent_votes = (
                floor((answer.poll_id.number_of_votes / len(answer.voting_partner_ids)) * 100)
                if answer.voting_partner_ids
                else 0
            )

    def _to_store(self, store: Store, /, *, fields=None, **kwargs):
        if fields is None:
            fields = ["poll_id", "text", "voting_partner_ids", "percent_votes"]
        for answer in self:
            data = answer._read_format(
                [f for f in fields if f not in {"voting_partner_ids", "poll_id", "percent_votes"}],
                load=False,
            )[0]
            data["poll_id"] = answer.poll_id.id
            data["voting_partner_ids"] = Store.many(answer.voting_partner_ids, only_id=True)
            store.add("discuss.poll.answer", data)
