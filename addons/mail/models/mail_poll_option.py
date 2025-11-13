# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import format_list


class MailPollOption(models.Model):
    _description = "Poll option"
    _name = "mail.poll.option"

    number_of_votes = fields.Integer(compute="_compute_number_of_votes")
    option_label = fields.Char(required=True)
    poll_id = fields.Many2one("mail.poll", ondelete="cascade", required=True, index=True)
    selected_by_self = fields.Boolean(compute="_compute_selected_by_self")
    vote_ids = fields.One2many("mail.poll.vote", "option_id")
    vote_percentage = fields.Integer(compute="_compute_vote_percentage")

    _check_option_label = models.Constraint(
        "CHECK (TRIM(option_label) <> '')", "Options must have a non-empty option label."
    )

    def write(self, vals):
        if "poll_id" in vals:
            raise UserError(
                self.env._(
                    'Cannot change the poll linked to the following options: %(options)s.',
                    options=format_list(self.env, self.mapped("option_label")),
                )
            )
        return super().write(vals)

    @api.depends_context("guest", "uid")
    @api.depends("vote_ids")
    def _compute_selected_by_self(self):
        user, guest = self.env["res.users"]._get_current_persona()
        if not guest and not user:
            self.selected_by_self = False
            return
        domain = Domain("option_id", "in", self.ids)
        if user:
            domain &= Domain("user_id", "=", self.env.user.id)
        else:
            domain &= Domain("guest_id", "=", guest.id)
        selected_options = self.env["mail.poll.vote"].search_fetch(domain).option_id
        for option in self:
            option.selected_by_self = option in selected_options

    @api.depends("vote_ids")
    def _compute_number_of_votes(self):
        count_by_option = dict(
            self.env["mail.poll.vote"]._read_group(
                [("option_id", "in", self.ids)], ["option_id"], ["__count"]
            )
        )
        for option in self:
            option.number_of_votes = count_by_option.get(option, 0)

    @api.depends("poll_id.option_ids.number_of_votes")
    def _compute_vote_percentage(self):
        """Use the largest remainder method to compute whole number vote percentages.
        Do not force 100% when options are tied to avoid skewing results.
        """
        percentage_by_option = {}
        for poll in self.poll_id:
            vote_data = []
            total_votes = sum(option.number_of_votes for option in poll.option_ids)
            for option in poll.option_ids:
                exact_percentage = (
                    (100 * option.number_of_votes / total_votes) if total_votes else 0
                )
                rounded_percentage = int(exact_percentage)
                fractional_remainder = exact_percentage - rounded_percentage
                vote_data.append(
                    {
                        "option": option,
                        "rounded_percentage": rounded_percentage,
                        "fractional_remainder": fractional_remainder,
                        "votes_count": option.number_of_votes,
                    }
                )
            vote_data.sort(key=lambda d: (-d["fractional_remainder"], d["option"].id))
            total_rounded = sum(d["rounded_percentage"] for d in vote_data)
            for i in range(100 - total_rounded):
                if (
                    i + 1 == len(vote_data)
                    or vote_data[i]["votes_count"] == vote_data[i + 1]["votes_count"]
                ):
                    break  # Do not skew the results when two options are tied
                vote_data[i]["rounded_percentage"] += 1
            for data in vote_data:
                percentage_by_option[data["option"]] = data["rounded_percentage"]
        for option in self:
            option.vote_percentage = percentage_by_option[option]

    def _to_store_defaults(self, target):
        fields = [
            "number_of_votes",
            "poll_id",
            "option_label",
            "vote_percentage",
        ]
        if target.is_current_user(self.env):
            fields.append("selected_by_self")
        return fields
