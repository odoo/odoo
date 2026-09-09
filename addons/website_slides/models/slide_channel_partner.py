import math

from odoo import _, api, fields, models, tools
from odoo.fields import Domain


class SlideChannelPartner(models.Model):
    _name = "slide.channel.partner"
    _description = "Channel / Partners (Members)"
    _table = "slide_channel_partner"
    _rec_name = "partner_id"

    active = fields.Boolean(default=True)
    channel_id = fields.Many2one(
        comodel_name="slide.channel",
        string="Course",
        index=True,
        required=True,
        ondelete="cascade",
    )
    member_status = fields.Selection(
        selection=[
            ("invited", "Invite Sent"),
            ("joined", "Joined"),
            ("ongoing", "Ongoing"),
            ("completed", "Finished"),
        ],
        string="Attendee Status",
        default="joined",
        readonly=True,
        required=True,
    )
    completion = fields.Integer(
        string="% Completed Contents",
        default=0,
        aggregator="avg",
    )
    completed_slides_count = fields.Integer(
        string="# Completed Contents",
        default=0,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        index=True,
        required=True,
        ondelete="cascade",
    )
    partner_email = fields.Char(
        related="partner_id.email",
        readonly=True,
    )
    channel_user_id = fields.Many2one(
        comodel_name="res.users",
        related="channel_id.user_id",
        string="Responsible",
    )
    channel_type = fields.Selection(related="channel_id.channel_type")
    channel_visibility = fields.Selection(related="channel_id.visibility")
    channel_enroll = fields.Selection(related="channel_id.enroll")
    channel_website_id = fields.Many2one(
        comodel_name="website",
        related="channel_id.website_id",
        string="Website",
    )
    next_slide_id = fields.Many2one(
        comodel_name="slide.slide",
        string="Next Lesson",
        compute="_compute_next_slide_id",
    )

    invitation_link = fields.Char(compute="_compute_invitation_link")
    last_invitation_date = fields.Datetime()

    _channel_partner_uniq = models.Constraint(
        "unique(channel_id, partner_id)",
        "A partner membership to a channel must be unique!",
    )
    _check_completion = models.Constraint(
        "check(completion >= 0 and completion <= 100)",
        "The completion of a channel is a percentage and should be between 0% and 100.",
    )

    @api.depends("channel_id", "partner_id")
    def _compute_invitation_link(self):
        for record in self:
            invitation_hash = record._get_invitation_hash()
            record.invitation_link = f"{record.channel_id.get_base_url()}/slides/{record.channel_id.id}/invite?invite_partner_id={record.partner_id.id}&invite_hash={invitation_hash}"

    def _compute_next_slide_id(self):
        if not self.ids:
            self.next_slide_id = False
            return
        self.env["slide.channel.partner"].flush_model()
        self.env["slide.slide"].flush_model()
        self.env["slide.slide.partner"].flush_model()
        query = """
            SELECT DISTINCT ON (SCP.id)
                SCP.id AS id,
                SS.id AS slide_id
            FROM slide_channel_partner SCP
            JOIN slide_slide SS
                ON SS.channel_id = SCP.channel_id
                AND SS.is_published = TRUE
                AND SS.active = TRUE
                AND SS.is_category = FALSE
                AND NOT EXISTS (
                    SELECT 1
                      FROM slide_slide_partner
                     WHERE slide_id = SS.id
                       AND partner_id = SCP.partner_id
                       AND completed = TRUE
                )
            WHERE SCP.id = ANY(%s)
            ORDER BY SCP.id, SS.sequence, SS.id
        """
        self.env.cr.execute(query, [list(self.ids)])
        next_slide_per_membership = {
            line["id"]: line["slide_id"] for line in self.env.cr.dictfetchall()
        }

        for membership in self:
            membership.next_slide_id = next_slide_per_membership.get(
                membership.id, False
            )

    def _is_finished(self):
        self.check_singleton()
        total_slides = self.channel_id.total_slides
        return bool(total_slides) and self.completed_slides_count >= total_slides

    def _recompute_completion(self):
        read_group_res = (
            self.env["slide.slide.partner"]
            .sudo()
            ._read_group(
                [
                    "&",
                    "&",
                    ("channel_id", "in", self.mapped("channel_id").ids),
                    ("partner_id", "in", self.mapped("partner_id").ids),
                    ("completed", "=", True),
                    ("slide_id.is_published", "=", True),
                    ("slide_id.active", "=", True),
                ],
                ["channel_id", "partner_id"],
                aggregates=["__count"],
            )
        )
        mapped_data = {
            (channel.id, partner.id): count
            for channel, partner, count in read_group_res
        }

        completed_records = self.env["slide.channel.partner"]
        uncompleted_records = self.env["slide.channel.partner"]
        for record in self:
            if record.member_status in ("completed", "invited"):
                continue
            total_slides = record.channel_id.total_slides
            was_finished = record._is_finished()
            record.completed_slides_count = mapped_data.get(
                (record.channel_id.id, record.partner_id.id), 0
            )
            record.completion = (
                math.floor(100.0 * record.completed_slides_count / total_slides)
                if total_slides
                else 0
            )
            is_finished = record._is_finished()

            if not record.channel_id.active:
                continue
            if not was_finished and is_finished:
                completed_records += record
            elif was_finished and not is_finished:
                uncompleted_records += record

            if is_finished:
                record.member_status = "completed"
            elif not record.completed_slides_count:
                record.member_status = "joined"
            else:
                record.member_status = "ongoing"

        if completed_records:
            completed_records._post_completion_update_hook(completed=True)
            completed_records._send_completed_mail()

        if uncompleted_records:
            uncompleted_records._post_completion_update_hook(completed=False)

    def unlink(self):
        if self:
            self.filtered(
                lambda membership: membership.member_status == "completed"
            )._post_completion_update_hook(completed=False)
            # One clause per (channel, partners) pair rather than per record,
            # and the channel side expressed as a relation instead of an
            # inlined list of slide ids: unlinking 1000 members of a 500-slide
            # course used to build a domain with half a million terms in it.
            removed_slide_partner_domain = Domain.OR(
                Domain("channel_id", "=", channel.id)
                & Domain("partner_id", "in", channel_partners.partner_id.ids)
                for channel, channel_partners in self.grouped("channel_id").items()
            )
            self.env["slide.slide.partner"].search(
                removed_slide_partner_domain
            ).unlink()
        return super().unlink()

    def _get_invitation_hash(self):
        self.check_singleton()
        token = (self.partner_id.id, self.channel_id.id)
        return tools.hmac(self.env(su=True), "website_slides-channel-invite", token)

    def _post_completion_update_hook(self, completed=True):
        for channel, memberships in self.grouped("channel_id").items():
            karma = channel.karma_gen_channel_finish
            if karma <= 0:
                continue

            karma_per_users = {}
            for user in memberships.sudo().partner_id.user_ids:
                karma_per_users[user] = {
                    "gain": karma if completed else karma * -1,
                    "source": channel,
                    "reason": _("Course Finished")
                    if completed
                    else _("Course Set Uncompleted"),
                }

            self.env["res.users"]._add_karma_batch(karma_per_users)

    def _send_completed_mail(self):
        template_to_records = {}
        for record in self:
            template = record.channel_id.completed_template_id
            if template:
                template_to_records.setdefault(
                    template, self.env["slide.channel.partner"]
                )
                template_to_records[template] += record

        record_email_values = {}
        for template, records in template_to_records.items():
            record_values = template._prepare_mail_vals(
                records.ids,
                [
                    "attachment_ids",
                    "body_html",
                    "email_cc",
                    "email_from",
                    "email_to",
                    "mail_server_id",
                    "model",
                    "partner_to",
                    "reply_to",
                    "report_template_ids",
                    "res_id",
                    "scheduled_date",
                    "subject",
                ],
            )
            for res_id, values in record_values.items():
                values.pop("attachments", False)
                values["body"] = values.get("body_html")
                record_email_values[res_id] = (template, values)

        mail_mail_values = []
        for record in self:
            template, email_values = record_email_values.get(record.id, (None, None))

            if not email_values or not email_values.get("partner_ids"):
                continue

            email_values.update(
                author_id=record.channel_id.user_id.partner_id.id
                or self.env.company.partner_id.id,
                auto_delete=True,
                recipient_ids=[(4, pid) for pid in email_values["partner_ids"]],
            )
            email_values["body_html"] = template._render_encapsulate(
                "mail.mail_notification_light",
                email_values["body_html"],
                add_context={"model_description": _("Completed Course")},
                context_record=record.channel_id,
            )
            mail_mail_values.append(email_values)

        if mail_mail_values:
            self.env["mail.mail"].sudo().create(mail_mail_values)

    @api.autovacuum
    def _gc_slide_channel_partner(self):
        limit_dt = fields.Datetime.subtract(fields.Datetime.now(), months=3)
        expired_invitations = (
            self.env["slide.channel.partner"]
            .with_context(active_test=False)
            .search(
                [
                    ("member_status", "=", "invited"),
                    ("completion", "=", 0),
                    "|",
                    ("last_invitation_date", "=", False),
                    ("last_invitation_date", "<", limit_dt),
                ]
            )
        )
        expired_invitations.unlink()
