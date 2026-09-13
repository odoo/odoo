import logging
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

emails_split = re.compile(r"[;,\n\r]+")


class SlideChannelInvite(models.TransientModel):
    _name = "slide.channel.invite"
    _inherit = ["mixin.mail.composer"]
    _description = "Channel Invitation Wizard"

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attachments",
        bypass_search_access=True,
    )
    send_email = fields.Boolean(
        compute="_compute_send_email",
        store=True,
        readonly=False,
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Recipients",
    )
    channel_id = fields.Many2one(
        comodel_name="slide.channel",
        string="Course",
        required=True,
    )
    channel_invite_url = fields.Char(
        string="Course Link",
        compute="_compute_channel_invite_url",
    )
    channel_visibility = fields.Selection(related="channel_id.visibility")
    channel_published = fields.Boolean(related="channel_id.is_published")
    enroll_mode = fields.Boolean(
        string="Enroll partners",
        readonly=True,
        help="Whether invited partners will be added as enrolled. Otherwise, they will be added as invited.",
    )

    @api.depends("channel_id")
    def _compute_channel_invite_url(self):
        for invite in self:
            channel = invite.channel_id
            invite.channel_invite_url = f"{channel.get_base_url()}/slides/{channel.id}"

    @api.depends("channel_id")
    def _compute_render_model(self):
        self.render_model = "slide.channel.partner"

    @api.depends("channel_id", "enroll_mode")
    def _compute_send_email(self):
        self.send_email = self.channel_visibility != "public" or self.enroll_mode

    def action_invite(self):
        self.check_singleton()

        if not self.partner_ids:
            raise UserError(_("Please select at least one recipient."))
        if self.send_email and not self.env.user.email:
            raise UserError(
                _(
                    "Unable to post message, please configure the sender's email address."
                )
            )

        attendees_to_reinvite = (
            self.env["slide.channel.partner"].search(
                [
                    ("member_status", "=", "invited"),
                    ("channel_id", "=", self.channel_id.id),
                    ("partner_id", "in", self.partner_ids.ids),
                ]
            )
            if not self.enroll_mode
            else self.env["slide.channel.partner"]
        )

        channel_partners = self.channel_id._action_add_members(
            self.partner_ids - attendees_to_reinvite.partner_id,
            member_status="joined" if self.enroll_mode else "invited",
            raise_on_access=True,
        )
        if not self.enroll_mode:
            (
                attendees_to_reinvite | channel_partners
            ).last_invitation_date = fields.Datetime.now()

        if self.send_email:
            mail_values = [
                self._prepare_mail_values(channel_partner)
                for channel_partner in attendees_to_reinvite | channel_partners
            ]
            self.env["mail.mail"].sudo().create(mail_values)

        return {"type": "ir.actions.act_window_close"}

    def _prepare_mail_values(self, slide_channel_partner):
        lang = self._render_lang(slide_channel_partner.ids)[slide_channel_partner.id]
        subject = self._render_field(
            "subject", slide_channel_partner.ids, set_lang=lang
        )[slide_channel_partner.id]
        body = self._render_field("body", slide_channel_partner.ids, set_lang=lang)[
            slide_channel_partner.id
        ]
        mail_values = {
            "attachment_ids": [(4, att.id) for att in self.attachment_ids],
            "author_id": self.env.user.partner_id.id,
            "auto_delete": self.template_id.auto_delete if self.template_id else True,
            "body_html": body,
            "email_from": self.env.user.email_formatted,
            "model": None,
            "recipient_ids": [(4, slide_channel_partner.partner_id.id)],
            "res_id": None,
            "subject": subject,
        }

        email_layout_xmlid = self.env.context.get(
            "default_email_layout_xmlid", self.env.context.get("notif_layout")
        )
        if email_layout_xmlid:
            mail_values["body_html"] = self._render_encapsulate(
                email_layout_xmlid,
                mail_values["body_html"],
                context_record=slide_channel_partner,
                add_context={
                    "record_name": self.channel_id.name,
                    "signature": self.channel_id.user_id.signature,
                },
            )

        return mail_values
