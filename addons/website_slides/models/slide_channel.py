import ast
import logging
import math
import uuid
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import is_html_empty

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class SlideChannel(models.Model):
    _name = "slide.channel"
    _description = "Course"
    _inherit = [
        "mixin.rating",
        "mixin.mail.activity",
        "mixin.image",
        "mixin.website.cover_properties",
        "mixin.website.seo.metadata",
        "mixin.website.published.multi",
        "mixin.website.searchable",
        "mixin.approval.access",
    ]
    _order = "sequence, id"
    _access_approval_category = "website_slides.approval_category_course_access"
    _mail_partner_fields = ()
    _partner_unfollow_enabled = True

    _CUSTOMER_HEADERS_LIMIT_COUNT = 0

    def _default_cover_properties(self):
        res = super()._default_cover_properties()
        res.update(
            {
                "background_color_class": "o_cc4",
                "background_color_style": (
                    "background-color: rgba(0, 0, 0, 0); "
                    "background-image: linear-gradient(120deg, #875A7B, #78516F);"
                ),
                "opacity": "0",
                "resize_class": "cover_auto",
            }
        )
        return res

    def _default_access_token(self):
        return str(uuid.uuid4())

    def _default_enroll_msg(self):
        return _("Contact Responsible")

    name = fields.Char(
        translate=True,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        tracking=100,
    )
    description = fields.Html(
        translate=True,
        sanitize_attributes=False,
        sanitize_form=False,
        help="The description that is displayed on top of the course page, just below the title",
    )
    description_short = fields.Html(
        string="Short Description",
        translate=True,
        sanitize_attributes=False,
        sanitize_form=False,
        help="The description that is displayed on the course card",
    )
    description_html = fields.Html(
        string="Detailed Description",
        translate=tools.html_translate,
        sanitize_attributes=False,
        sanitize_form=False,
    )
    channel_type = fields.Selection(
        selection=[("training", "Training"), ("documentation", "Documentation")],
        string="Course type",
        default="training",
        required=True,
        help='Defines the course type (e.g., "Training" for interactive learning, or "Documentation" for resources and guides).',
    )
    sequence = fields.Integer(default=10)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        default=lambda self: self.env.uid,
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
        help="Used to decorate kanban view",
    )
    tag_ids = fields.Many2many(
        comodel_name="slide.channel.tag",
        relation="slide_channel_tag_rel",
        column1="channel_id",
        column2="tag_id",
        string="Tags",
        help="Used to categorize and filter displayed channels/courses",
    )
    slide_ids = fields.One2many(
        comodel_name="slide.slide",
        inverse_name="channel_id",
        string="Slides and categories",
        copy=True,
    )
    slide_content_ids = fields.One2many(
        comodel_name="slide.slide",
        string="Content",
        compute="_compute_category_and_slide_ids",
    )
    slide_category_ids = fields.One2many(
        comodel_name="slide.slide",
        string="Categories",
        compute="_compute_category_and_slide_ids",
    )
    slide_last_update = fields.Date(
        string="Last Update",
        compute="_compute_slide_last_update",
        store=True,
    )
    slide_partner_ids = fields.One2many(
        comodel_name="slide.slide.partner",
        inverse_name="channel_id",
        string="Slide User Data",
        copy=False,
        groups="website_slides.group_website_slides_officer",
    )
    promote_strategy = fields.Selection(
        selection=[
            ("latest", "Latest Created"),
            ("most_voted", "Most Voted"),
            ("most_viewed", "Most Viewed"),
            ("specific", "Select Manually"),
            ("none", "None"),
        ],
        string="Featured Content",
        default="latest",
        copy=False,
        required=False,
        help="Defines the content that will be promoted on the course home page",
    )
    promoted_slide_id = fields.Many2one(
        comodel_name="slide.slide",
        copy=False,
    )
    access_token = fields.Char(
        string="Security Token",
        default=_default_access_token,
        copy=False,
    )
    nbr_document = fields.Integer(
        string="Documents",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_video = fields.Integer(
        string="Videos",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_infographic = fields.Integer(
        string="Infographics",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_article = fields.Integer(
        string="Articles",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_quiz = fields.Integer(
        string="Number of Quizs",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_certification = fields.Integer(
        string="Number of Certifications",
        compute="_compute_slides_statistics",
        store=True,
    )
    total_slides = fields.Integer(
        string="Number of Contents",
        compute="_compute_slides_statistics",
        store=True,
    )
    total_views = fields.Integer(
        string="Visits",
        compute="_compute_slides_statistics",
        store=True,
    )
    total_votes = fields.Integer(
        string="Votes",
        compute="_compute_slides_statistics",
        store=True,
    )
    total_time = fields.Float(
        string="Duration",
        digits=(10, 2),
        compute="_compute_slides_statistics",
        store=True,
    )
    rating_avg_stars = fields.Float(
        string="Rating Average (Stars)",
        digits=(16, 1),
        compute="_compute_rating_stats",
        compute_sudo=True,
    )
    allow_comment = fields.Boolean(
        string="Allow rating on Course",
        compute="_compute_allow_comment",
        precompute=True,
        store=True,
        readonly=False,
        help="Allow Attendees to like and comment your content and to submit reviews on your course.",
    )
    publish_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="New Content Notification",
        default=lambda self: self.env["ir.model.data"]._xmlid_to_res_id(
            "website_slides.slide_template_published"
        ),
        domain=[("model", "=", "slide.slide")],
        help="Defines the email your Attendees will receive each time you upload new content.",
    )
    share_channel_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Channel Share Template",
        default=lambda self: self.env["ir.model.data"]._xmlid_to_res_id(
            "website_slides.mail_template_channel_shared"
        ),
        help="Email template used when sharing a channel",
    )
    share_slide_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Share Template",
        default=lambda self: self.env["ir.model.data"]._xmlid_to_res_id(
            "website_slides.slide_template_shared"
        ),
        help="Email template used when sharing a slide",
    )
    completed_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Completion Notification",
        default=lambda self: self.env["ir.model.data"]._xmlid_to_res_id(
            "website_slides.mail_template_channel_completed"
        ),
        domain=[("model", "=", "slide.channel.partner")],
        help="Defines the email your Attendees will receive once they reach the end of your course.",
    )
    enroll = fields.Selection(
        selection=[("public", "Open"), ("invite", "On Invitation")],
        string="Enroll Policy",
        compute="_compute_enroll",
        precompute=True,
        store=True,
        copy=False,
        readonly=False,
        required=True,
        help="Defines how people can enroll to your Course.",
    )
    enroll_msg = fields.Html(
        string="Enroll Message",
        translate=tools.html_translate,
        sanitize_attributes=False,
        default=_default_enroll_msg,
        help="Message explaining the enroll process",
    )
    enroll_group_ids = fields.Many2many(
        comodel_name="res.groups",
        string="Auto Enroll Groups",
        help="Members of those groups are automatically added as members of the channel.",
    )
    visibility = fields.Selection(
        selection=[
            ("public", "Everyone"),
            ("connected", "Signed In"),
            ("members", "Course Attendees"),
            ("link", "Anyone with the link"),
        ],
        string="Show Course To",
        default="public",
        required=True,
        help="Defines who can access your courses and their content.",
    )
    upload_group_ids = fields.Many2many(
        comodel_name="res.groups",
        relation="rel_upload_groups",
        column1="channel_id",
        column2="group_id",
        string="Upload Groups",
        groups="base.group_user",
        help="Groups whose members may add contents to this course. It grants "
        "uploading, not publishing: only the responsible and eLearning managers "
        "can publish. Leave empty to restrict uploading to those two.",
    )
    website_default_background_image_url = fields.Char(
        string="Background image URL",
        compute="_compute_website_default_background_image_url",
    )
    channel_partner_ids = fields.One2many(
        comodel_name="slide.channel.partner",
        inverse_name="channel_id",
        string="Enrolled Attendees Information",
        domain=[("member_status", "!=", "invited")],
        groups="website_slides.group_website_slides_officer",
    )
    channel_partner_all_ids = fields.One2many(
        comodel_name="slide.channel.partner",
        inverse_name="channel_id",
        string="All Attendees Information",
        groups="website_slides.group_website_slides_officer",
    )
    members_count = fields.Integer(
        string="# Enrolled Attendees",
        compute="_compute_members_counts",
    )
    members_all_count = fields.Integer(
        string="# Enrolled or Invited Attendees",
        compute="_compute_members_counts",
    )
    members_engaged_count = fields.Integer(
        string="# Active Attendees",
        compute="_compute_members_counts",
        help="Active attendees include both 'joined' and 'ongoing' attendees.",
    )
    members_completed_count = fields.Integer(
        string="# Completed Attendees",
        compute="_compute_members_counts",
    )
    members_invited_count = fields.Integer(
        string="# Invited Attendees",
        compute="_compute_members_counts",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Attendees",
        compute="_compute_partners",
        search="_search_partner_ids",
        help="Enrolled partners in the course",
    )
    completed = fields.Boolean(
        string="Done",
        compute="_compute_user_statistics",
        compute_sudo=False,
    )
    completion = fields.Integer(
        compute="_compute_user_statistics",
        compute_sudo=False,
    )
    can_upload = fields.Boolean(
        compute="_compute_can_upload",
        compute_sudo=False,
    )
    has_requested_access = fields.Boolean(
        string="Access Requested",
        compute="_compute_has_requested_access",
        compute_sudo=False,
    )
    is_member = fields.Boolean(
        string="Is Enrolled Attendee",
        compute="_compute_membership_values",
        search="_search_is_member",
        help="Is the attendee actively enrolled.",
    )
    is_member_invited = fields.Boolean(
        string="Is Invited Attendee",
        compute="_compute_membership_values",
        search="_search_is_member_invited",
        help="Is the invitation for this attendee pending.",
    )
    is_visible = fields.Boolean(
        string="Is Visible On Website",
        compute="_compute_is_visible",
        search="_search_is_visible",
    )
    partner_has_new_content = fields.Boolean(
        compute="_compute_partner_has_new_content",
        compute_sudo=False,
    )
    karma_gen_channel_rank = fields.Integer(
        string="Course ranked",
        default=5,
    )
    karma_gen_channel_finish = fields.Integer(
        string="Course finished",
        default=10,
    )
    karma_review = fields.Integer(
        string="Add Review",
        default=10,
        help="Karma needed to add a review on the course",
    )
    karma_slide_comment = fields.Integer(
        string="Add Comment",
        default=3,
        help="Karma needed to add a comment on a slide of this course",
    )
    karma_slide_vote = fields.Integer(
        string="Vote",
        default=3,
        help="Karma needed to like/dislike a slide of this course.",
    )
    can_review = fields.Boolean(
        compute="_compute_action_rights",
        compute_sudo=False,
    )
    can_comment = fields.Boolean(
        compute="_compute_action_rights",
        compute_sudo=False,
    )
    can_vote = fields.Boolean(
        compute="_compute_action_rights",
        compute_sudo=False,
    )
    prerequisite_channel_ids = fields.Many2many(
        comodel_name="slide.channel",
        relation="slide_channel_prerequisite_slide_channel_rel",
        column1="channel_id",
        column2="prerequisite_channel_id",
        string="Prerequisites",
        domain="[('id', '!=', id), ('visibility', '=', visibility), ('website_published', '=', website_published)]",
        help="Prerequisite courses to complete before accessing this one.",
    )
    prerequisite_of_channel_ids = fields.Many2many(
        comodel_name="slide.channel",
        relation="slide_channel_prerequisite_slide_channel_rel",
        column1="prerequisite_channel_id",
        column2="channel_id",
        string="Prerequisite Of",
        help="Courses that have this course as prerequisite.",
    )
    prerequisite_user_has_completed = fields.Boolean(
        string="Has Completed Prerequisite",
        compute="_compute_prerequisite_user_has_completed",
    )

    _check_enroll = models.Constraint(
        "CHECK(visibility != 'members' OR enroll = 'invite')",
        "The Enroll Policy should be set to 'On Invitation' when visibility is set to 'Course Attendees'",
    )

    @api.depends("visibility")
    def _compute_enroll(self):
        for channel in self:
            if channel.visibility == "members":
                channel.enroll = "invite"
            elif not channel.enroll:
                channel.enroll = "public"

    @api.depends("visibility", "is_member")
    @api.depends_context("uid")
    def _compute_is_visible(self):
        for channel in self:
            channel.is_visible = (
                channel.visibility == "public"
                or channel.is_member
                or (
                    not self.env.user._is_public() and channel.visibility == "connected"
                )
            )

    @api.model
    def _search_is_visible(self, operator, value):
        if operator != "in":
            return NotImplemented
        return [
            "|",
            ("is_member", "=", True),
            (
                "visibility",
                "in",
                ["public"] if self.env.user._is_public() else ["public", "connected"],
            ),
        ]

    @api.depends(
        "channel_partner_all_ids",
        "channel_partner_all_ids.member_status",
        "channel_partner_all_ids.active",
    )
    def _compute_partners(self):
        data = dict(
            self.env["slide.channel.partner"]
            .sudo()
            ._read_group(
                [("channel_id", "in", self.ids), ("member_status", "!=", "invited")],
                ["channel_id"],
                aggregates=["partner_id:array_agg"],
            )
        )
        for slide_channel in self:
            slide_channel.partner_ids = data.get(slide_channel, [])

    def _search_partner_ids(self, operator, value):
        return [
            (
                "channel_partner_ids",
                "in",
                self.env["slide.channel.partner"]
                .sudo()
                ._search(
                    [
                        ("partner_id", operator, value),
                        ("active", "=", True),
                        ("member_status", "!=", "invited"),
                    ],
                ),
            )
        ]

    @api.depends("slide_ids.is_published")
    def _compute_slide_last_update(self):
        self.slide_last_update = fields.Date.today()

    @api.depends(
        "channel_partner_all_ids.channel_id", "channel_partner_all_ids.member_status"
    )
    def _compute_members_counts(self):
        read_group_res = (
            self.env["slide.channel.partner"]
            .sudo()
            ._read_group(
                domain=[("channel_id", "in", self.ids)],
                groupby=["channel_id", "member_status"],
                aggregates=["__count"],
            )
        )
        data = {
            (channel.id, member_status): count
            for channel, member_status, count in read_group_res
        }
        for channel in self:
            channel.members_invited_count = data.get((channel.id, "invited"), 0)
            channel.members_engaged_count = data.get(
                (channel.id, "joined"), 0
            ) + data.get((channel.id, "ongoing"), 0)
            channel.members_completed_count = data.get((channel.id, "completed"), 0)
            channel.members_all_count = (
                channel.members_invited_count
                + channel.members_engaged_count
                + channel.members_completed_count
            )
            channel.members_count = (
                channel.members_engaged_count + channel.members_completed_count
            )

    @api.depends("approval_request_ids.state")
    @api.depends_context("uid")
    def _compute_has_requested_access(self):
        requested_cids = (
            self.env["approval.request"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "in", self.ids),
                    (
                        "subject_key",
                        "=",
                        self._get_access_subject_key(self.env.user.partner_id),
                    ),
                    ("state", "in", ("new", "pending")),
                ]
            )
            .mapped("res_id")
        )
        for channel in self:
            channel.has_requested_access = channel.id in requested_cids

    @api.depends(
        "channel_partner_all_ids.partner_id",
        "channel_partner_all_ids.member_status",
        "channel_partner_all_ids.active",
    )
    @api.depends_context("uid")
    def _compute_membership_values(self):
        if self.env.user._is_public():
            self.is_member = False
            self.is_member_invited = False
            return
        data = dict(
            self.env["slide.channel.partner"]
            .sudo()
            ._read_group(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("channel_id", "in", self.ids),
                    ("active", "=", True),
                ],
                ["member_status"],
                ["channel_id:array_agg"],
            )
        )
        active_channels_ids = (
            data.get("joined", []) + data.get("ongoing", []) + data.get("completed", [])
        )
        invitation_pending_channels_ids = data.get("invited", [])
        for channel in self:
            channel.is_member = channel.id in active_channels_ids
            channel.is_member_invited = channel.id in invitation_pending_channels_ids

    def _search_is_member(self, operator, value):
        if operator != "in":
            return NotImplemented
        return [("id", "in", self._search_is_member_channel_ids())]

    def _search_is_member_invited(self, operator, value):
        if operator != "in":
            return NotImplemented
        return [("id", "in", self._search_is_member_channel_ids(invited=True))]

    def _search_is_member_channel_ids(self, invited=False):
        return (
            self.env["slide.channel.partner"]
            .sudo()
            ._read_group(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("member_status", "=" if invited else "!=", "invited"),
                    ("active", "=", True),
                ],
                aggregates=["channel_id:array_agg"],
            )[0][0]
        )

    @api.depends("slide_ids.is_category")
    def _compute_category_and_slide_ids(self):
        for channel in self:
            channel.slide_category_ids = channel.slide_ids.filtered(
                lambda slide: slide.is_category
            )
            channel.slide_content_ids = channel.slide_ids - channel.slide_category_ids

    @api.depends(
        "slide_ids.slide_category",
        "slide_ids.is_published",
        "slide_ids.completion_time",
        "slide_ids.likes",
        "slide_ids.dislikes",
        "slide_ids.total_views",
        "slide_ids.is_category",
        "slide_ids.active",
    )
    def _compute_slides_statistics(self):
        default_vals = {
            "total_views": 0,
            "total_votes": 0,
            "total_time": 0,
            "total_slides": 0,
        }
        keys = [
            "nbr_%s" % slide_category
            for slide_category in self.env["slide.slide"]
            ._fields["slide_category"]
            .get_values(self.env)
        ]
        default_vals.update(dict.fromkeys(keys, 0))

        result = {cid: dict(default_vals) for cid in self.ids}
        read_group_res = self.env["slide.slide"]._read_group(
            [
                ("active", "=", True),
                ("is_published", "=", True),
                ("channel_id", "in", self.ids),
                ("is_category", "=", False),
            ],
            ["channel_id", "slide_category"],
            aggregates=[
                "__count",
                "likes:sum",
                "dislikes:sum",
                "total_views:sum",
                "completion_time:sum",
            ],
        )
        for (
            channel,
            slide_category,
            count,
            likes_sum,
            dislikes_sum,
            total_views_sum,
            completion_time_sum,
        ) in read_group_res:
            channel_dict = result[channel.id]
            channel_dict["total_votes"] += likes_sum
            channel_dict["total_votes"] -= dislikes_sum
            channel_dict["total_views"] += total_views_sum
            channel_dict["total_time"] += completion_time_sum
            if slide_category:
                channel_dict[f"nbr_{slide_category}"] = count
                channel_dict["total_slides"] += count

        for record in self:
            record.update(result.get(record.id, default_vals))

    def _compute_rating_stats(self):
        super()._compute_rating_stats()
        for record in self:
            record.rating_avg_stars = record.rating_avg

    @api.depends("channel_type")
    def _compute_allow_comment(self):
        for record in self:
            record.allow_comment = record.channel_type != "documentation"

    @api.depends("slide_partner_ids", "slide_partner_ids.completed", "total_slides")
    @api.depends_context("uid")
    def _compute_user_statistics(self):
        current_user_info = (
            self.env["slide.channel.partner"]
            .sudo()
            .search(
                [
                    ("channel_id", "in", self.ids),
                    ("partner_id", "=", self.env.user.partner_id.id),
                ]
            )
        )
        mapped_data = {
            info.channel_id.id: (
                info.member_status == "completed",
                info.completed_slides_count,
            )
            for info in current_user_info
        }
        for record in self:
            completed, completed_slides_count = mapped_data.get(record.id, (False, 0))
            record.completed = completed
            record.completion = (
                100
                if completed
                else math.floor(
                    100.0 * completed_slides_count / (record.total_slides or 1)
                )
            )

    @api.depends("upload_group_ids", "user_id")
    @api.depends_context("uid")
    def _compute_can_upload(self):
        for record in self:
            if record.user_id == self.env.user:
                record.can_upload = True
            elif record.sudo().upload_group_ids:
                record.can_upload = bool(
                    record.sudo().upload_group_ids & self.env.user.group_ids
                )
            else:
                record.can_upload = self.env.user.has_group(
                    "website_slides.group_website_slides_manager"
                )

    @api.depends("user_id", "can_upload")
    @api.depends_context("uid")
    def _compute_can_publish(self):
        for record in self:
            if not record.can_upload:
                record.can_publish = False
            elif record.user_id == self.env.user:
                record.can_publish = True
            else:
                record.can_publish = self.env.user.has_group(
                    "website_slides.group_website_slides_manager"
                )

    @api.model
    def _get_can_publish_error_message(self):
        return _(
            "Publishing is restricted to the course responsible and to eLearning managers"
        )

    @api.depends("slide_partner_ids")
    @api.depends_context("uid")
    def _compute_partner_has_new_content(self):
        new_published_slides = (
            self.env["slide.slide"]
            .sudo()
            .search(
                [
                    ("is_published", "=", True),
                    (
                        "date_published",
                        ">",
                        fields.Datetime.now() - relativedelta(days=7),
                    ),
                    ("channel_id", "in", self.ids),
                    ("is_category", "=", False),
                ]
            )
        )
        slide_partner_completed = (
            self.env["slide.slide.partner"]
            .sudo()
            .search(
                [
                    ("channel_id", "in", self.ids),
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("slide_id", "in", new_published_slides.ids),
                    ("completed", "=", True),
                ]
            )
            .mapped("slide_id")
        )
        for channel in self:
            new_slides = new_published_slides.filtered(
                lambda slide, channel=channel: slide.channel_id == channel
            )
            channel.partner_has_new_content = any(
                slide not in slide_partner_completed for slide in new_slides
            )

    @api.depends("channel_type")
    def _compute_website_default_background_image_url(self):
        for channel in self:
            channel.website_default_background_image_url = f"website_slides/static/src/img/channel-{channel.channel_type}-default.jpg"

    @api.depends("name")
    def _compute_website_url(self):
        super()._compute_website_url()
        for channel in self:
            if channel.id:
                channel.website_url = f"/slides/{self.env['ir.http']._slug(channel)}"

    @api.depends("website_id.domain")
    def _compute_website_absolute_url(self):
        super()._compute_website_absolute_url()

    @api.depends(
        "can_publish",
        "is_member",
        "karma_review",
        "karma_slide_comment",
        "karma_slide_vote",
    )
    @api.depends_context("uid")
    def _compute_action_rights(self):
        user_karma = self.env.user.karma
        for channel in self:
            if channel.can_publish:
                channel.can_vote = channel.can_comment = channel.can_review = True
            elif not channel.is_member:
                channel.can_vote = channel.can_comment = channel.can_review = False
            else:
                channel.can_review = user_karma >= channel.karma_review
                channel.can_comment = user_karma >= channel.karma_slide_comment
                channel.can_vote = user_karma >= channel.karma_slide_vote

    @api.depends("prerequisite_channel_ids", "channel_partner_ids.member_status")
    @api.depends_context("uid")
    def _compute_prerequisite_user_has_completed(self):
        completed_prerequisite_channels = (
            self.env["slide.channel.partner"]
            .sudo()
            .search(
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("channel_id", "in", self.prerequisite_channel_ids.ids),
                    ("member_status", "=", "completed"),
                ]
            )
            .mapped("channel_id")
        )
        for channel in self:
            channel.prerequisite_user_has_completed = all(
                channel in completed_prerequisite_channels
                for channel in channel.prerequisite_channel_ids
            )

    def _init_column(self, column_name, *, new_column=False):
        if column_name != "access_token":
            super()._init_column(column_name, new_column=new_column)
        else:
            query = """
                UPDATE %(table_name)s
                SET access_token = md5(md5(random()::varchar || id::varchar) || clock_timestamp()::varchar)::uuid::varchar
                WHERE access_token IS NULL
            """ % {"table_name": self._table}
            self.env.cr.execute(query)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("channel_partner_ids") and not self.env.is_superuser():
                vals["channel_partner_ids"] = [
                    (0, 0, {"partner_id": self.env.user.partner_id.id})
                ]
            if not is_html_empty(vals.get("description")) and is_html_empty(
                vals.get("description_short")
            ):
                vals["description_short"] = vals["description"]

        channels = super(
            SlideChannel, self.with_context(mail_create_nosubscribe=True)
        ).create(vals_list)

        for channel in channels:
            if channel.user_id:
                channel._action_add_members(channel.user_id.partner_id)
            if channel.enroll_group_ids:
                channel._add_groups_members()

        return channels

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for channel, vals in zip(self, vals_list, strict=True):
            if "name" not in default:
                vals["name"] = f"{channel.name} ({_('copy')})"
            if "enroll" not in default and channel.visibility == "members":
                vals["enroll"] = "invite"
        return vals_list

    def write(self, vals):
        mirror_description = vals.get("description")
        if not is_html_empty(mirror_description) and is_html_empty(
            vals.get("description_short")
        ):
            linked = self.filtered(
                lambda channel: channel.description == channel.description_short
            )
            if linked and linked != self:
                (self - linked).write(vals)
                return linked.write(vals)
            if linked:
                vals["description_short"] = mirror_description

        res = super().write(vals)

        if vals.get("user_id"):
            self._action_add_members(
                self.env["res.users"].sudo().browse(vals["user_id"]).partner_id
            )
            self.activity_reschedule(
                ["mail_activity_data_todo"],
                new_user_id=vals.get("user_id"),
            )
        if "enroll_group_ids" in vals:
            self._add_groups_members()

        return res

    def unlink(self):

        _debug.lifecycle(
            "unlink", channels=self, count=len(self), slides=len(self.slide_ids)
        )
        self.slide_ids.unlink()
        return super().unlink()

    def action_archive(self):
        archived = self.filtered(self._active_name)
        res = super().action_archive()
        archived.is_published = False
        archived.slide_ids.action_archive()
        return res

    def action_unarchive(self):
        to_activate = self.filtered(lambda channel: not channel.active)
        to_activate.with_context(active_test=False).slide_ids.action_unarchive()
        return super(SlideChannel, to_activate).action_unarchive()

    def message_post(self, *, parent_id=False, subtype_id=False, **kwargs):
        self.check_singleton()
        if kwargs.get("message_type") == "comment" and not self.can_review:
            _debug.logic("channel_review_refused", reason="karma", channels=self)
            raise AccessError(_("Not enough karma to review"))
        if parent_id:
            parent_message = self.env["mail.message"].sudo().browse(parent_id)
            if parent_message.subtype_id and parent_message.subtype_id == self.env.ref(
                "website_slides.mt_channel_slide_published"
            ):
                subtype_id = self.env.ref("mail.mt_note").id
        message = super().message_post(
            parent_id=parent_id, subtype_id=subtype_id, **kwargs
        )
        if self.env.user._is_internal() and not message.rating_value:
            return message
        if message.subtype_id == self.env.ref("mail.mt_comment"):
            domain = [
                ("res_id", "=", self.id),
                ("author_id", "=", message.author_id.id),
                ("model", "=", "slide.channel"),
                ("subtype_id", "=", self.env.ref("mail.mt_comment").id),
                ("rating_ids", "!=", False),
            ]
            if self.env["mail.message"].search_count(domain, limit=2) > 1:
                raise ValidationError(
                    _("Only a single review can be posted per course.")
                )
        if message.rating_value and message.is_current_user_or_guest_author:
            self.env.user._add_karma(
                self.karma_gen_channel_rank, self, _("Course Ranked")
            )
        return message

    def action_redirect_to_members(self, status_filter=""):
        action_ctx = {}
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website_slides.slide_channel_partner_action"
        )
        if status_filter == "engaged":
            action_ctx["search_default_filter_joined"] = 1
            action_ctx["search_default_filter_ongoing"] = 1
        elif status_filter:
            action_ctx[f"search_default_filter_{status_filter}"] = 1
        action["domain"] = [("channel_id", "in", self.ids)]
        action["sample"] = 1
        if status_filter == "completed":
            help_message = {
                "header_message": _("No Attendee has completed this course yet!"),
                "body_message": "",
            }
        else:
            help_message = {
                "header_message": _("No Attendees Yet!"),
                "body_message": _(
                    "From here you'll be able to monitor attendees and to track their progress."
                ),
            }
        action["help"] = (
            Markup(
                """<p class="o_view_nocontent_smiling_face">%(header_message)s</p><p>%(body_message)s</p>"""
            )
            % help_message
        )
        if len(self) == 1:
            action["display_name"] = _("Attendees of %s", self.name)
            action_ctx["default_channel_id"] = self.id
        action["context"] = action_ctx
        return action

    def action_redirect_to_engaged_members(self):
        return self.action_redirect_to_members("engaged")

    def action_redirect_to_completed_members(self):
        return self.action_redirect_to_members("completed")

    def action_redirect_to_invited_members(self):
        return self.action_redirect_to_members("invited")

    def action_channel_enroll(self):
        template = self.env.ref(
            "website_slides.mail_template_slide_channel_enroll",
            raise_if_not_found=False,
        )
        return self._action_channel_open_invite_wizard(template, enroll_mode=True)

    def action_channel_invite(self):
        template = self.env.ref(
            "website_slides.mail_template_slide_channel_invite",
            raise_if_not_found=False,
        )
        return self._action_channel_open_invite_wizard(template)

    def _action_channel_open_invite_wizard(self, mail_template, enroll_mode=False):
        course_name = self.name if len(self) == 1 else ""
        local_context = dict(
            self.env.context,
            default_channel_id=self.id if len(self) == 1 else False,
            default_email_layout_xmlid="website_slides.mail_notification_channel_invite",
            default_enroll_mode=enroll_mode,
            default_template_id=(mail_template and mail_template.id) or False,
            default_use_template=bool(mail_template),
        )
        if enroll_mode:
            name = _(
                "Enroll Attendees to %(course_name)s",
                course_name=course_name or _("a course"),
            )
        else:
            name = _(
                "Invite Attendees to %(course_name)s",
                course_name=course_name or _("a course"),
            )

        return {
            "type": "ir.actions.act_window",
            "views": [[False, "form"]],
            "res_model": "slide.channel.invite",
            "target": "new",
            "context": local_context,
            "name": name,
        }

    def _action_add_members(
        self, target_partners, member_status="joined", raise_on_access=False
    ):
        SlideChannelPartnerSudo = self.env["slide.channel.partner"].sudo()
        allowed_channels = self._filter_add_members(raise_on_access=raise_on_access)
        if not allowed_channels or not target_partners:
            _debug.logic(
                "members_not_added",
                reason="no_allowed_channel_or_partner",
                channels=self,
                partners=len(target_partners),
            )
            return SlideChannelPartnerSudo
        _debug.pipeline("add_members", channels=allowed_channels, status=member_status)

        existing_channel_partners = (
            self.env["slide.channel.partner"]
            .with_context(active_test=False)
            .sudo()
            .search(
                [
                    ("channel_id", "in", allowed_channels.ids),
                    ("partner_id", "in", target_partners.ids),
                ]
            )
        )

        archived_channel_partners = existing_channel_partners.filtered(
            lambda channel_partner: not channel_partner.active
        )
        to_unarchived = SlideChannelPartnerSudo
        if archived_channel_partners:
            archived_channel_partners.action_unarchive()
            to_unarchived = archived_channel_partners
            to_unarchived.member_status = member_status
            if member_status == "joined":
                to_unarchived._recompute_completion()

        existing_channel_partners_map = defaultdict(
            lambda: self.env["slide.channel.partner"]
        )
        for channel_partner in existing_channel_partners:
            existing_channel_partners_map[channel_partner.channel_id] += channel_partner

        to_update_as_joined = SlideChannelPartnerSudo
        to_create_channel_partners_values = []

        for channel in allowed_channels:
            channel_partners = existing_channel_partners_map[channel]
            if member_status == "joined":
                to_update_as_joined += channel_partners.filtered(
                    lambda cp: cp.member_status == "invited"
                )
            to_create_channel_partners_values.extend(
                {
                    "channel_id": channel.id,
                    "partner_id": partner.id,
                    "member_status": member_status,
                }
                for partner in target_partners - channel_partners.partner_id
            )

        new_slide_channel_partners = SlideChannelPartnerSudo.create(
            to_create_channel_partners_values
        )
        to_update_as_joined.member_status = "joined"
        to_update_as_joined._recompute_completion()

        result_channel_partners = (
            to_unarchived + to_update_as_joined + new_slide_channel_partners
        )

        if member_status == "joined":
            result_channel_partners_map = defaultdict(list)
            for channel_partner in result_channel_partners:
                result_channel_partners_map[channel_partner.channel_id].append(
                    channel_partner.partner_id.id
                )
            for channel, partner_ids in result_channel_partners_map.items():
                channel.message_subscribe(
                    partner_ids=partner_ids,
                    subtype_ids=[
                        self.env.ref("website_slides.mt_channel_slide_published").id
                    ],
                )
        return result_channel_partners

    def _filter_add_members(self, raise_on_access=False):
        allowed = self.filtered(lambda channel: channel.enroll == "public")
        if controlled_access := (self - allowed):
            allowed += controlled_access._filtered_access("write")
            if raise_on_access and allowed != self:
                _debug.logic(
                    "add_members_refused",
                    reason="no_write_access",
                    channels=self - allowed,
                )
                raise AccessError(
                    _(
                        "You are not allowed to add members to this course. "
                        "Please contact the course responsible or an administrator."
                    )
                )
        return allowed

    def _add_groups_members(self):
        for channel in self:
            channel._action_add_members(
                channel.mapped("enroll_group_ids.all_user_ids.partner_id")
            )

    def _get_earned_karma(self, partner_ids):
        total_karma = defaultdict(list)

        slide_completed = (
            self.env["slide.slide.partner"]
            .sudo()
            .search(
                [
                    ("partner_id", "in", partner_ids),
                    ("channel_id", "in", self.ids),
                    ("completed", "=", True),
                    ("quiz_attempts_count", ">", 0),
                ]
            )
        )
        for partner_slide in slide_completed:
            slide = partner_slide.slide_id
            if not slide.has_questions:
                continue
            total_karma[partner_slide.partner_id.id].append(
                {
                    "karma": slide._get_quiz_reward(partner_slide.quiz_attempts_count),
                    "channel_id": slide.channel_id,
                }
            )

        channel_completed = (
            self.env["slide.channel.partner"]
            .sudo()
            .search(
                [
                    ("partner_id", "in", partner_ids),
                    ("channel_id", "in", self.ids),
                    ("member_status", "=", "completed"),
                ]
            )
        )
        for partner_channel in channel_completed:
            channel = partner_channel.channel_id
            total_karma[partner_channel.partner_id.id].append(
                {
                    "karma": channel.karma_gen_channel_finish,
                    "channel_id": channel,
                }
            )

        return total_karma

    def _remove_membership(self, partner_ids):
        if not partner_ids:
            raise ValueError(
                "Do not use this method with an empty partner_id recordset"
            )

        self.message_unsubscribe(partner_ids=partner_ids)
        if self:
            removed_channel_partner = (
                self.env["slide.channel.partner"]
                .sudo()
                .search(
                    [
                        ("channel_id", "in", self.ids),
                        ("partner_id", "in", partner_ids),
                    ]
                )
            )
            if removed_channel_partner:
                removed_channel_partner.action_archive()

    @api.model
    def _send_share_mail(self, template, record, emails, **extra_context):
        template = template.with_context(
            user=self.env.user,
            email=emails,
            base_url=record.get_base_url(),
            **extra_context,
        )
        email_values = {"email_to": emails}
        if self.env.user._is_portal():
            template = template.sudo()
            email_values["email_from"] = (
                self.env.company.catchall_formatted or self.env.company.email_formatted
            )
        return template.send_mail(
            record.id,
            email_layout_xmlid="mail.mail_notification_light",
            email_values=email_values,
        )

    def _send_share_email(self, emails):
        courses_without_templates = self.filtered(
            lambda channel: not channel.share_channel_template_id
        )
        if courses_without_templates:
            raise UserError(
                _(
                    'Impossible to send emails. Select a "Channel Share Template" for courses %(course_names)s first',
                    course_names=", ".join(courses_without_templates.mapped("name")),
                )
            )
        return [
            self._send_share_mail(record.share_channel_template_id, record, emails)
            for record in self
        ]

    def action_view_slides(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website_slides.slide_slide_action"
        )
        action["context"] = {
            "search_default_published": 1,
            "default_channel_id": self.id,
        }
        action["domain"] = [("channel_id", "=", self.id), ("is_category", "=", False)]
        return action

    def action_view_ratings(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website_slides.rating_rating_action_slide_channel"
        )
        action["name"] = _("Rating of %s", self.name)
        action["domain"] = Domain.AND(
            [
                ast.literal_eval(action.get("domain", "[]")),
                Domain("res_id", "in", self.ids),
            ]
        )
        return action

    def action_request_access(self):
        if self.env.user._is_public():
            return {"error": _("You have to sign in before")}
        if not self.is_published:
            return {"error": _("Course not published yet")}
        if self.is_member:
            return {"error": _("Already member")}
        if self.enroll == "invite":
            partner = self.env.user.partner_id
            if self._get_live_access_request(partner):
                return {"error": _("Already Requested")}
            self.sudo()._request_access(partner)
            return {"done": True}
        return {"done": False}

    def action_grant_access(self, partner_id):
        self.check_singleton()
        partner = self.env["res.partner"].browse(partner_id).exists()
        if not partner:
            return
        if not self._decide_access_request(partner, False, approve=True):
            self._action_add_members(partner, raise_on_access=True)

    def action_refuse_access(self, partner_id):
        self.check_singleton()
        partner = self.env["res.partner"].browse(partner_id).exists()
        if partner:
            self._decide_access_request(partner, False, approve=False)

    def _get_domain_rating(self, record_ids=None):
        return super()._get_domain_rating(record_ids=record_ids) & Domain(
            "is_internal", "=", False
        )

    def _has_access(self, partner, role=False):
        return partner in self.sudo().channel_partner_ids.partner_id

    def _grant_access(self, partner, role=False):
        self._action_add_members(partner)

    def _get_access_request_name(self, partner, role):
        return _(
            "Access to %(course)s for %(partner)s",
            course=self.name,
            partner=partner.name,
        )

    def _get_approval_activity_values(self, approver):
        partner, _role = self._get_access_subject(approver.request_id.subject_key)
        return {"request_partner_id": partner.id} if partner else {}

    @api.model
    def _backfill_access_requests(self):
        """Turn the access requests kept as bare activities into approval requests.

        For an upgrade: the requester, when they have a user, owns the request; the
        activity goes, since the engine asks the course responsible itself.
        """
        todo = self.env.ref("mail.mail_activity_data_todo")
        activities = (
            self.env["mail.activity"]
            .sudo()
            .search(
                [
                    ("res_model", "=", self._name),
                    ("request_partner_id", "!=", False),
                    ("activity_type_id", "=", todo.id),
                    ("approver_id", "=", False),
                ]
            )
        )
        for activity in activities:
            channel = self.sudo().browse(activity.res_id).exists()
            partner = activity.request_partner_id
            activity.unlink()
            if (
                not channel
                or partner in channel.channel_partner_ids.partner_id
                or channel._get_live_approval_request(
                    channel._get_access_subject_key(partner)
                )
            ):
                continue
            requester = partner.user_ids[:1] or self.env.ref("base.user_root")
            channel.with_user(requester).sudo()._raise_approval_request(
                channel._get_access_subject_key(partner)
            )

    def _get_access_action(self, access_uid=None, force_website=False):
        self.check_singleton()
        if force_website or self.website_published:
            return {
                "type": "ir.actions.act_url",
                "url": self.website_url,
                "target": "self",
                "target_type": "public",
            }
        return super()._get_access_action(
            access_uid=access_uid, force_website=force_website
        )

    def _get_categorized_slides(
        self, base_domain, order, force_void=True, limit=False, offset=False
    ):
        self.check_singleton()
        all_categories = (
            self.env["slide.slide"]
            .sudo()
            .search([("channel_id", "=", self.id), ("is_category", "=", True)])
        )
        all_slides = self.env["slide.slide"].sudo().search(base_domain, order=order)
        category_data = []

        start = offset or 0
        end = start + limit if limit else None

        slides_by_category = defaultdict(lambda: self.env["slide.slide"])
        for slide in all_slides:
            slides_by_category[slide.category_id.id] += slide

        for category in all_categories:
            category_slides = slides_by_category[category.id]
            if not category_slides and not force_void:
                continue
            category_data.append(
                {
                    "category": category,
                    "id": category.id,
                    "name": category.name,
                    "slug_name": self.env["ir.http"]._slug(category),
                    "total_slides": len(category_slides),
                    "slides": category_slides[start:end],
                }
            )

        uncategorized_slides = slides_by_category[False]
        if uncategorized_slides or force_void:
            category_data.insert(
                0,
                {
                    "category": False,
                    "id": False,
                    "name": _("Uncategorized"),
                    "slug_name": _("Uncategorized"),
                    "total_slides": len(uncategorized_slides),
                    "slides": uncategorized_slides[start:end],
                },
            )

        return category_data

    def _move_category_slides(self, category, new_category=None):
        moved_ids = category.slide_ids.ids
        if not moved_ids:
            return
        truncated_slide_ids = [
            slide_id for slide_id in self.slide_ids.ids if slide_id not in moved_ids
        ]
        if new_category:
            place_idx = truncated_slide_ids.index(new_category.id)
            ordered_slide_ids = (
                truncated_slide_ids[:place_idx]
                + moved_ids
                + truncated_slide_ids[place_idx:]
            )
        else:
            ordered_slide_ids = moved_ids + truncated_slide_ids
        self._write_sequences(ordered_slide_ids)

    def _write_sequences(self, ordered_slide_ids):
        Slide = self.env["slide.slide"]
        by_sequence = defaultdict(list)
        for index, slide_id in enumerate(ordered_slide_ids):
            by_sequence[index + 1].append(slide_id)
        for sequence, slide_ids in by_sequence.items():
            Slide.browse(slide_ids).sequence = sequence

    def _resequence_slides(self, slide, force_category=False):
        ids_to_resequence = self.slide_ids.ids
        index_of_added_slide = ids_to_resequence.index(slide.id)
        next_category_id = None
        if self.slide_category_ids:
            force_category_id = (
                force_category.id if force_category else slide.category_id.id
            )
            index_of_category = (
                self.slide_category_ids.ids.index(force_category_id)
                if force_category_id
                else None
            )
            if index_of_category is None:
                next_category_id = self.slide_category_ids.ids[0]
            elif index_of_category < len(self.slide_category_ids.ids) - 1:
                next_category_id = self.slide_category_ids.ids[index_of_category + 1]

        if next_category_id:
            added_slide_id = ids_to_resequence.pop(index_of_added_slide)
            index_of_next_category = ids_to_resequence.index(next_category_id)
            ids_to_resequence.insert(index_of_next_category, added_slide_id)
            self._write_sequences(ids_to_resequence)
        else:
            slide.write(
                {
                    "sequence": self.env["slide.slide"]
                    .browse(ids_to_resequence[-1])
                    .sequence
                    + 1
                }
            )

    def get_backend_menu_id(self):
        return self.env.ref("website_slides.website_slides_menu_root").id

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options["displayDescription"]
        with_date = options["displayDetail"]
        my = options.get("my")
        search_tags = options.get("tag")
        slide_category = options.get("slide_category")
        domain = [website.website_domain(), [("is_visible", "=", True)]]
        if my:
            domain.append([("is_member", "=", True)])
        if search_tags:
            tags = self.env["slide.channel.tag"]._search_by_slugs(search_tags)
            domain.extend(
                [("tag_ids", "in", tags_.ids)]
                for tags_ in tags.grouped("group_id").values()
            )
        if slide_category and "nbr_%s" % slide_category in self:
            domain.append([("nbr_%s" % slide_category, ">", 0)])
        search_fields = ["name"]
        fetch_fields = ["name", "website_url"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "website_url", "type": "text", "truncate": False},
        }
        if with_description:
            search_fields.append("description_short")
            fetch_fields.append("description_short")
            mapping["description"] = {
                "name": "description_short",
                "type": "text",
                "html": True,
                "match": True,
            }
        if with_date:
            fetch_fields.append("slide_last_update")
            mapping["detail"] = {"name": "slide_last_update", "type": "date"}
        return {
            "model": "slide.channel",
            "base_domain": domain,
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-graduation-cap",
        }

    def _get_placeholder_filename(self, field):
        image_fields = ["image_%s" % size for size in [1920, 1024, 512, 256, 128]]
        if field in image_fields:
            return self.website_default_background_image_url
        return super()._get_placeholder_filename(field)

    @api.model
    def _allow_publish_rating_stats(self):
        return True
