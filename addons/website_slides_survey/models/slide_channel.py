from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.fields import Domain


class SlideChannelPartner(models.Model):
    _inherit = "slide.channel.partner"

    nbr_certification = fields.Integer(related="channel_id.nbr_certification")
    survey_certification_success = fields.Boolean(string="Certified")


class SlideChannel(models.Model):
    _inherit = "slide.channel"

    members_certified_count = fields.Integer(
        string="# Certified Attendees",
        compute="_compute_members_certified_count",
    )

    def _remove_membership(self, partner_ids):
        if self:
            removed_channel_partner_domain = Domain.OR(
                Domain("partner_id", "in", partner_ids)
                & Domain("channel_id", "=", channel.id)
                for channel in self
            )
            slide_partners_sudo = (
                self.env["slide.slide.partner"]
                .sudo()
                .search(removed_channel_partner_domain)
            )
            slide_partners_sudo.user_input_ids.slide_partner_id = False
        return super()._remove_membership(partner_ids)

    @api.depends("channel_partner_ids")
    def _compute_members_certified_count(self):
        channels_count = (
            self.env["slide.channel.partner"]
            .sudo()
            ._read_group(
                domain=[
                    ("channel_id", "in", self.ids),
                    ("survey_certification_success", "=", True),
                ],
                groupby=["channel_id"],
                aggregates=["__count"],
            )
        )
        mapped_data = dict(channels_count)
        for channel in self:
            channel.members_certified_count = mapped_data.get(channel, 0)

    def action_redirect_to_certified_members(self):
        action = self.action_redirect_to_members("certified")
        msg = _("No Attendee passed this course certification yet!")
        action["help"] = Markup('<p class="o_view_nocontent_smiling_face">%s</p>') % msg
        return action
