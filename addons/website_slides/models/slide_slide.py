import base64
import datetime
import io
import logging
import re
from urllib.parse import urlencode, urlsplit

import requests
from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from psycopg import IntegrityError

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools import html2plaintext
from odoo.tools.pdf import PdfReader

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class SlideSlide(models.Model):
    _name = "slide.slide"
    _inherit = [
        "mixin.mail.thread",
        "mixin.image",
        "mixin.website.seo.metadata",
        "mixin.website.published",
        "mixin.website.searchable",
    ]
    _description = "Slides"
    _mail_post_access = "read"
    _order_by_strategy = {
        "sequence": "sequence asc, id asc",
        "most_viewed": "total_views desc",
        "most_voted": "likes desc",
        "latest": "date_published desc",
    }
    _order = "sequence asc, is_category asc, id asc"
    _mail_partner_fields = ()
    _partner_unfollow_enabled = True

    YOUTUBE_VIDEO_ID_REGEX = r"^(?:(?:https?:)?//)?(?:www\.|m\.)?(?:youtu\.be/|youtube(-nocookie)?\.com/(?:embed/|v/|shorts/|live/|watch\?v=|watch\?.+&v=))((?:\w|-){11})\S*$"
    GOOGLE_DRIVE_DOCUMENT_ID_REGEX = (
        r"(^https:\/\/docs.google.com|^https:\/\/drive.google.com).*\/d\/([^\/]*)"
    )
    VIMEO_VIDEO_ID_REGEX = (
        r"\/\/(player.)?vimeo.com\/(?:[a-z]*\/)*([0-9]{6,11})\/?([0-9a-z]{6,11})?[?]?.*"
    )
    GOOGLE_DRIVE_MIME_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.ms-excel": "sheet",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "sheet",
        "application/vnd.oasis.opendocument.spreadsheet": "sheet",
        "application/vnd.google-apps.spreadsheet": "sheet",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "doc",
        "application/vnd.oasis.opendocument.text": "doc",
        "application/vnd.google-apps.document": "doc",
        "application/vnd.ms-powerpoint": "slides",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "slides",
        "application/vnd.oasis.opendocument.presentation": "slides",
        "application/vnd.google-apps.presentation": "slides",
    }

    name = fields.Char(
        string="Title",
        translate=True,
        required=True,
    )
    image_1920 = fields.Image(
        compute="_compute_image_1920",
        store=True,
        readonly=False,
    )
    active = fields.Boolean(
        default=True,
        tracking=100,
    )
    sequence = fields.Integer(default=0)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Uploaded by",
        default=lambda self: self.env.uid,
    )
    description = fields.Html(
        translate=True,
        sanitize_overridable=True,
        sanitize_attributes=False,
    )
    channel_id = fields.Many2one(
        comodel_name="slide.channel",
        string="Course",
        index=True,
        required=True,
        ondelete="cascade",
    )
    tag_ids = fields.Many2many(
        comodel_name="slide.tag",
        relation="rel_slide_tag",
        column1="slide_id",
        column2="tag_id",
        string="Tags",
    )
    is_preview = fields.Boolean(
        string="Allow Preview",
        default=False,
        help="The course is accessible by anyone : the users don't need to join the channel to access the content of the course.",
    )
    is_new_slide = fields.Boolean(compute="_compute_is_new_slide")
    completion_time = fields.Float(
        string="Duration",
        digits=(10, 4),
        compute="_compute_category_completion_time",
        recursive=True,
        store=True,
        readonly=False,
    )
    is_category = fields.Boolean(
        string="Is a category",
        default=False,
    )
    category_id = fields.Many2one(
        comodel_name="slide.slide",
        string="Section",
        compute="_compute_category_id",
        store=True,
        index="btree_not_null",
    )
    slide_ids = fields.One2many(
        comodel_name="slide.slide",
        inverse_name="category_id",
        string="Content",
    )
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="slide_slide_partner",
        column1="slide_id",
        column2="partner_id",
        string="Subscribers",
        copy=False,
        groups="website_slides.group_website_slides_officer",
    )
    slide_partner_ids = fields.One2many(
        comodel_name="slide.slide.partner",
        inverse_name="slide_id",
        string="Subscribers information",
        copy=False,
        groups="website_slides.group_website_slides_officer",
    )
    user_membership_id = fields.Many2one(
        comodel_name="slide.slide.partner",
        string="Subscriber information",
        compute="_compute_user_membership_id",
        compute_sudo=False,
        help="Subscriber information for the current logged in user",
    )
    user_vote = fields.Integer(
        string="User vote",
        compute="_compute_user_membership_id",
        compute_sudo=False,
    )
    user_has_completed = fields.Boolean(
        string="Is Member",
        compute="_compute_user_membership_id",
        compute_sudo=False,
    )
    user_has_completed_category = fields.Boolean(
        string="Is Category Completed",
        compute="_compute_category_completed",
    )
    survey_id = fields.Many2one(
        comodel_name="survey.survey",
        string="Linked Survey",
        index="btree_not_null",
    )
    has_questions = fields.Boolean(
        compute="_compute_has_questions",
        store=True,
        help="Whether this slide has quiz/certification questions (via its linked survey).",
    )
    questions_count = fields.Integer(
        string="Number of Questions",
        compute="_compute_questions_count",
    )
    quiz_first_attempt_reward = fields.Integer(
        string="Reward: first attempt",
        default=10,
    )
    quiz_second_attempt_reward = fields.Integer(
        string="Reward: second attempt",
        default=7,
    )
    quiz_third_attempt_reward = fields.Integer(
        string="Reward: third attempt",
        default=5,
    )
    quiz_fourth_attempt_reward = fields.Integer(
        string="Reward: every attempt after the third try",
        default=2,
    )
    nbr_certification = fields.Integer(
        string="Number of Certifications",
        compute="_compute_slides_statistics",
        store=True,
    )
    can_self_mark_completed = fields.Boolean(
        string="Can Mark Completed",
        compute="_compute_mark_complete_actions",
        help="The slide can be marked as completed even without opening it",
    )
    can_self_mark_uncompleted = fields.Boolean(
        string="Can Mark Uncompleted",
        compute="_compute_mark_complete_actions",
        help="The slide can be marked as not completed and the progression",
    )
    slide_category = fields.Selection(
        selection=[
            ("infographic", "Image"),
            ("article", "Article"),
            ("document", "Document"),
            ("video", "Video"),
            ("quiz", "Quiz"),
            ("certification", "Certification"),
        ],
        string="Category",
        default="document",
        required=True,
    )
    source_type = fields.Selection(
        selection=[
            ("local_file", "Upload from Device"),
            ("external", "Retrieve from Google Drive"),
        ],
        default="local_file",
        required=True,
    )
    url = fields.Char(
        string="External URL",
        help="URL of the Google Drive file or URL of the YouTube video",
    )
    binary_content = fields.Binary(
        string="File",
        attachment=True,
    )
    slide_resource_ids = fields.One2many(
        comodel_name="slide.slide.resource",
        inverse_name="slide_id",
        string="Additional Resource for this slide",
        copy=True,
    )
    slide_resource_downloadable = fields.Boolean(
        string="Allow Download",
        default=False,
        help="Allow the user to download the content of the slide.",
    )
    google_drive_id = fields.Char(
        string="Google Drive ID of the external URL",
        compute="_compute_google_drive_id",
    )
    html_content = fields.Html(
        string="HTML Content",
        translate=True,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False,
        help="Custom HTML content for slides of category 'Article'.",
    )
    image_binary_content = fields.Binary(
        related="binary_content",
        string="Image Content",
        readonly=False,
    )
    image_google_url = fields.Char(
        related="url",
        string="Image Link",
        readonly=False,
        help="Link of the image (we currently only support Google Drive as source)",
    )
    slide_icon_class = fields.Char(
        string="Slide Icon fa-class",
        compute="_compute_slide_icon_class",
    )
    slide_type = fields.Selection(
        selection=[
            ("image", "Image"),
            ("article", "Article"),
            ("quiz", "Quiz"),
            ("pdf", "PDF"),
            ("sheet", "Sheet (Excel, Google Sheet, ...)"),
            ("doc", "Document (Word, Google Doc, ...)"),
            ("slides", "Slides (PowerPoint, Google Slides, ...)"),
            ("youtube_video", "YouTube Video"),
            ("google_drive_video", "Google Drive Video"),
            ("vimeo_video", "Vimeo Video"),
            ("certification", "Certification"),
        ],
        compute="_compute_slide_type",
        store=True,
        readonly=False,
        help="Subtype of the slide category, allows more precision on the actual file type / source type.",
    )
    document_google_url = fields.Char(
        related="url",
        string="Document Link",
        readonly=False,
        help="Link of the document (we currently only support Google Drive as source)",
    )
    document_binary_content = fields.Binary(
        related="binary_content",
        string="PDF Content",
        readonly=False,
    )
    video_url = fields.Char(
        related="url",
        string="Video Link",
        readonly=False,
        help="Link of the video (we support YouTube, Google Drive and Vimeo as sources)",
    )
    video_source_type = fields.Selection(
        selection=[
            ("youtube", "YouTube"),
            ("google_drive", "Google Drive"),
            ("vimeo", "Vimeo"),
        ],
        string="Video Source",
        compute="_compute_video_source_type",
    )
    youtube_id = fields.Char(
        string="Video YouTube ID",
        compute="_compute_youtube_id",
    )
    vimeo_id = fields.Char(
        string="Video Vimeo ID",
        compute="_compute_vimeo_id",
    )
    website_id = fields.Many2one(
        related="channel_id.website_id",
        readonly=True,
    )
    date_published = fields.Datetime(
        string="Publish Date",
        copy=False,
        readonly=True,
        tracking=False,
    )
    likes = fields.Integer(
        compute="_compute_like_info",
        compute_sudo=False,
        store=True,
    )
    dislikes = fields.Integer(
        compute="_compute_like_info",
        compute_sudo=False,
        store=True,
    )
    embed_code = fields.Html(
        sanitize=False,
        compute="_compute_embed_code",
        readonly=True,
    )
    embed_code_external = fields.Html(
        string="External Embed Code",
        sanitize=False,
        compute="_compute_embed_code",
        readonly=True,
        help="Same as 'Embed Code' but used to embed the content on an external website.",
    )
    website_share_url = fields.Char(
        string="Share URL",
        compute="_compute_website_share_url",
    )
    embed_ids = fields.One2many(
        comodel_name="slide.embed",
        inverse_name="slide_id",
        string="External Slide Embeds",
    )
    embed_count = fields.Integer(
        string="# of Embed Views",
        compute="_compute_embed_count",
    )
    slide_views = fields.Integer(
        string="# of Website Views",
        compute="_compute_slide_views",
        store=True,
    )
    public_views = fields.Integer(
        string="# of Public Views",
        default=0,
        copy=False,
        readonly=True,
    )
    total_views = fields.Integer(
        string="# Total Views",
        compute="_compute_total",
        default="0",
        store=True,
    )
    comments_count = fields.Integer(
        string="Number of comments",
        compute="_compute_comments_count",
    )
    channel_type = fields.Selection(
        related="channel_id.channel_type",
        string="Channel type",
    )
    channel_allow_comment = fields.Boolean(
        related="channel_id.allow_comment",
        string="Allows comment",
    )
    nbr_document = fields.Integer(
        string="Number of Documents",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_video = fields.Integer(
        string="Number of Videos",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_infographic = fields.Integer(
        string="Number of Images",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_article = fields.Integer(
        string="Number of Articles",
        compute="_compute_slides_statistics",
        store=True,
    )
    nbr_quiz = fields.Integer(
        string="Number of Quizs",
        compute="_compute_slides_statistics",
        store=True,
    )
    total_slides = fields.Integer(
        compute="_compute_slides_statistics",
        store=True,
    )
    is_published = fields.Boolean(tracking=1)
    website_published = fields.Boolean(tracking=False)

    _exclusion_html_content_and_url = models.Constraint(
        "CHECK(html_content IS NULL OR url IS NULL)",
        "A slide is either filled with a url or HTML content. Not both.",
    )
    _check_survey_id = models.Constraint(
        "CHECK(slide_category != 'certification' OR survey_id IS NOT NULL)",
        "A slide of type 'certification' requires a certification.",
    )
    _check_certification_preview = models.Constraint(
        "CHECK(slide_category != 'certification' OR is_preview = False)",
        "A slide of type certification cannot be previewed.",
    )

    @api.depends("slide_category", "source_type", "image_binary_content")
    def _compute_image_1920(self):
        for slide in self:
            if (
                slide.slide_category == "infographic"
                and slide.source_type == "local_file"
                and slide.image_binary_content
            ):
                slide.image_1920 = slide.image_binary_content
            elif not slide.image_1920:
                slide.image_1920 = False

    @api.depends("date_published", "is_published")
    def _compute_is_new_slide(self):
        for slide in self:
            slide.is_new_slide = (
                slide.date_published > fields.Datetime.now() - relativedelta(days=7)
                if slide.is_published
                else False
            )

    def _get_placeholder_filename(self, field):
        return self.channel_id._get_placeholder_filename(field)

    @api.depends(
        "channel_id.slide_ids.is_category",
        "channel_id.slide_ids.sequence",
        "channel_id.slide_ids.slide_ids",
    )
    def _compute_category_id(self):
        self.category_id = False

        channel_slides = {}
        for slide in self:
            if slide.channel_id.id not in channel_slides:
                channel_slides[slide.channel_id.id] = slide.channel_id.slide_ids

        for slides in channel_slides.values():
            current_category = self.env["slide.slide"]
            slide_list = list(slides)
            slide_list.sort(key=lambda s: (s.sequence, not s.is_category))
            for slide in slide_list:
                if slide.is_category:
                    current_category = slide
                elif slide.category_id != current_category:
                    slide.category_id = current_category.id

    @api.depends("survey_id.question_ids")
    def _compute_has_questions(self):
        for slide in self:
            slide.has_questions = bool(slide.survey_id.question_ids)

    @api.depends("slide_category", "has_questions", "channel_id.is_member")
    @api.depends_context("uid")
    def _compute_mark_complete_actions(self):
        for slide in self:
            slide.can_self_mark_uncompleted = (
                slide.website_published and slide.channel_id.is_member
            )
            slide.can_self_mark_completed = (
                slide.website_published
                and slide.channel_id.is_member
                and slide.slide_category != "quiz"
                and not slide.has_questions
            )

    @api.depends("survey_id.question_ids")
    def _compute_questions_count(self):
        for slide in self:
            slide.questions_count = (
                len(slide.survey_id.question_ids) if slide.survey_id else 0
            )

    @api.depends(
        "website_message_ids.res_id",
        "website_message_ids.model",
        "website_message_ids.message_type",
        "website_message_ids.subtype_id",
        "website_message_ids.is_internal",
        "website_message_ids.body",
        "website_message_ids.attachment_ids",
    )
    def _compute_comments_count(self):
        counts = dict(
            self.env["mail.message"]
            .sudo()
            ._read_group(
                self._get_domain_portal_message_fetch(),
                ["res_id"],
                ["__count"],
            )
        )
        for slide in self:
            slide.comments_count = counts.get(slide.id, 0)

    @api.depends("slide_views", "public_views")
    def _compute_total(self):
        for record in self:
            record.total_views = record.slide_views + record.public_views

    @api.depends("slide_partner_ids.vote")
    def _compute_like_info(self):
        rg_data = (
            self.env["slide.slide.partner"]
            .sudo()
            ._read_group(
                [("slide_id", "in", self.ids), ("vote", "in", (-1, 1))],
                ["slide_id", "vote"],
                ["__count"],
            )
        )
        mapped_data = {(slide.id, vote): count for slide, vote, count in rg_data}

        for slide in self:
            slide.likes = mapped_data.get((slide.id, 1), 0)
            slide.dislikes = mapped_data.get((slide.id, -1), 0)

    @api.depends("slide_partner_ids.slide_id")
    def _compute_slide_views(self):
        read_group_res = (
            self.env["slide.slide.partner"]
            .sudo()
            ._read_group(
                [("slide_id", "in", self.ids)],
                ["slide_id"],
                aggregates=["__count"],
            )
        )
        mapped_data = {slide.id: count for slide, count in read_group_res}
        for slide in self:
            slide.slide_views = mapped_data.get(slide.id, 0)

    @api.depends("embed_ids.slide_id")
    def _compute_embed_count(self):
        read_group_res = (
            self.env["slide.embed"]
            .sudo()
            ._read_group(
                [("slide_id", "in", self.ids)],
                ["slide_id"],
                ["count_views:sum"],
            )
        )
        mapped_data = {
            slide.id: count_views_sum for slide, count_views_sum in read_group_res
        }

        for slide in self:
            slide.embed_count = mapped_data.get(slide.id, 0)

    @api.depends(
        "slide_ids.sequence",
        "slide_ids.active",
        "slide_ids.slide_category",
        "slide_ids.is_published",
        "slide_ids.is_category",
    )
    def _compute_slides_statistics(self):
        keys = [
            "nbr_%s" % slide_category
            for slide_category in self.env["slide.slide"]
            ._fields["slide_category"]
            .get_values(self.env)
        ]
        default_vals = dict.fromkeys(keys + ["total_slides"], 0)

        res = self.env["slide.slide"]._read_group(
            [
                ("is_published", "=", True),
                ("category_id", "in", self.filtered("is_category").ids),
                ("is_category", "=", False),
            ],
            ["category_id", "slide_category"],
            ["__count"],
        )

        result = {category_id: dict(default_vals) for category_id in self.ids}
        for category, slide_category, count in res:
            result[category.id][f"nbr_{slide_category}"] = count
            result[category.id]["total_slides"] += count

        for record in self:
            record.update(result.get(record._origin.id, default_vals))

    @api.depends(
        "category_id",
        "category_id.slide_ids",
        "category_id.slide_ids.user_has_completed",
    )
    def _compute_category_completed(self):
        for slide in self:
            if not slide.category_id:
                slide.user_has_completed_category = False
            else:
                slide.user_has_completed_category = all(
                    slide.category_id.slide_ids.mapped("user_has_completed")
                )

    @api.depends(
        "slide_ids.sequence",
        "slide_ids.active",
        "slide_ids.completion_time",
        "slide_ids.is_published",
        "slide_ids.is_category",
    )
    def _compute_category_completion_time(self):
        for category in self.filtered(lambda slide: slide.is_category):
            filtered_slides = category.slide_ids.filtered(
                lambda slide: slide.is_published
            )
            category.completion_time = sum(filtered_slides.mapped("completion_time"))

    @api.depends("slide_type")
    def _compute_slide_icon_class(self):
        icon_per_slide_type = {
            "image": "fa-regular fa-file-image",
            "article": "fa-regular fa-file-lines",
            "quiz": "fa-regular fa-circle-question",
            "pdf": "fa-regular fa-file-pdf",
            "sheet": "fa-regular fa-file-excel",
            "doc": "fa-regular fa-file-word",
            "slides": "fa-regular fa-file-powerpoint",
            "youtube_video": "fa-brands fa-youtube",
            "google_drive_video": "fa-regular fa-circle-play",
            "vimeo_video": "fa-brands fa-vimeo",
            "certification": "fa-trophy",
        }
        for slide in self:
            slide.slide_icon_class = icon_per_slide_type.get(
                slide.slide_type, "fa-regular fa-file"
            )

    @api.depends("slide_category", "source_type", "video_source_type")
    def _compute_slide_type(self):

        for slide in self:
            if slide.slide_category == "document":
                if slide.source_type == "local_file":
                    slide.slide_type = "pdf"
                elif slide.slide_type not in ["pdf", "sheet", "doc", "slides"]:
                    slide.slide_type = False
            elif slide.slide_category == "infographic":
                slide.slide_type = "image"
            elif slide.slide_category == "article":
                slide.slide_type = "article"
            elif slide.slide_category == "quiz":
                slide.slide_type = "quiz"
            elif slide.slide_category == "certification":
                slide.slide_type = "certification"
            elif (
                slide.slide_category == "video" and slide.video_source_type == "youtube"
            ):
                slide.slide_type = "youtube_video"
            elif (
                slide.slide_category == "video"
                and slide.video_source_type == "google_drive"
            ):
                slide.slide_type = "google_drive_video"
            elif slide.slide_category == "video" and slide.video_source_type == "vimeo":
                slide.slide_type = "vimeo_video"
            else:
                slide.slide_type = False

    @api.depends(
        "slide_partner_ids.partner_id",
        "slide_partner_ids.vote",
        "slide_partner_ids.completed",
    )
    @api.depends_context("uid")
    def _compute_user_membership_id(self):
        slide_partners = (
            self.env["slide.slide.partner"]
            .sudo()
            .search(
                [
                    ("slide_id", "in", self.ids),
                    ("partner_id", "=", self.env.user.partner_id.id),
                ]
            )
        )

        for record in self:
            record.user_membership_id = next(
                (
                    slide_partner
                    for slide_partner in slide_partners
                    if slide_partner.slide_id == record
                ),
                self.env["slide.slide.partner"],
            )
            record.user_vote = record.user_membership_id.vote
            record.user_has_completed = record.user_membership_id.completed

    @api.depends("slide_category", "google_drive_id", "video_source_type", "youtube_id")
    def _compute_embed_code(self):
        request_base_url = request.httprequest.url_root if request else False
        for slide in self:
            base_url = request_base_url or slide.get_base_url()
            if base_url[-1] == "/":
                base_url = base_url[:-1]

            embed_code = False
            embed_code_external = False
            if slide.slide_category == "video":
                if slide.video_source_type == "youtube":
                    query_params = urlsplit(slide.video_url).query
                    query_params = (
                        query_params + "&theme=light" if query_params else "theme=light"
                    )
                    embed_code = Markup(
                        '<iframe src="//www.youtube-nocookie.com/embed/%s?%s" allowFullScreen="true" frameborder="0" aria-label="%s"></iframe>'
                    ) % (slide.youtube_id, query_params, _("YouTube"))
                elif slide.video_source_type == "google_drive":
                    embed_code = Markup(
                        '<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0" aria-label="%s"></iframe>'
                    ) % (slide.google_drive_id, _("Google Drive"))
                elif slide.video_source_type == "vimeo":
                    if "/" in slide.vimeo_id:
                        [vimeo_id, vimeo_token] = slide.vimeo_id.split("/")
                        embed_code = (
                            Markup("""
                            <iframe src="https://player.vimeo.com/video/%s?h=%s&badge=0&amp;autopause=0&amp;player_id=0"
                                frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen aria-label="%s"></iframe>""")
                            % (vimeo_id, vimeo_token, _("Vimeo"))
                        )
                    else:
                        embed_code = (
                            Markup("""
                            <iframe src="https://player.vimeo.com/video/%s?badge=0&amp;autopause=0&amp;player_id=0"
                                frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen aria-label="%s"></iframe>""")
                            % (slide.vimeo_id, _("Vimeo"))
                        )
            elif (
                slide.slide_category in ["infographic", "document"]
                and slide.source_type == "external"
                and slide.google_drive_id
            ):
                embed_code = Markup(
                    '<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0" aria-label="%s"></iframe>'
                ) % (slide.google_drive_id, _("Google Drive"))
            elif (
                slide.slide_category == "document" and slide.source_type == "local_file"
            ):
                slide_url = base_url + self.env["ir.http"]._url_for(
                    "/slides/embed/%s?page=1" % slide.id
                )
                slide_url_external = base_url + self.env["ir.http"]._url_for(
                    "/slides/embed_external/%s?page=1" % slide.id
                )
                base_embed_code = Markup(
                    '<iframe src="%s" class="o_wslides_iframe_viewer" allowFullScreen="true" height="%s" width="%s" frameborder="0" aria-label="%s"></iframe>'
                )
                iframe_aria_label = _("Embed code")
                embed_code = base_embed_code % (slide_url, 315, 420, iframe_aria_label)
                embed_code_external = base_embed_code % (
                    slide_url_external,
                    315,
                    420,
                    iframe_aria_label,
                )

            slide.embed_code = embed_code
            slide.embed_code_external = embed_code_external or embed_code

    @api.depends("video_url")
    def _compute_video_source_type(self):
        for slide in self:
            video_source_type = False
            youtube_match = (
                re.match(self.YOUTUBE_VIDEO_ID_REGEX, slide.video_url)
                if slide.video_url
                else False
            )
            if (
                youtube_match
                and len(youtube_match.groups()) == 2
                and len(youtube_match.group(2)) == 11
            ):
                video_source_type = "youtube"
            if (
                slide.video_url
                and not video_source_type
                and re.match(self.GOOGLE_DRIVE_DOCUMENT_ID_REGEX, slide.video_url)
            ):
                video_source_type = "google_drive"
            vimeo_match = (
                re.search(self.VIMEO_VIDEO_ID_REGEX, slide.video_url)
                if slide.video_url
                else False
            )
            if not video_source_type and vimeo_match and len(vimeo_match.groups()) == 3:
                video_source_type = "vimeo"

            slide.video_source_type = video_source_type

    @api.depends("video_url", "video_source_type")
    def _compute_youtube_id(self):
        for slide in self:
            if slide.video_url and slide.video_source_type == "youtube":
                match = re.match(self.YOUTUBE_VIDEO_ID_REGEX, slide.video_url)
                if match and len(match.groups()) == 2 and len(match.group(2)) == 11:
                    slide.youtube_id = match.group(2)
                else:
                    slide.youtube_id = False
            else:
                slide.youtube_id = False

    @api.depends("video_url", "video_source_type")
    def _compute_vimeo_id(self):
        for slide in self:
            if slide.video_url and slide.video_source_type == "vimeo":
                match = re.search(self.VIMEO_VIDEO_ID_REGEX, slide.video_url)
                if match and len(match.groups()) == 3:
                    if match.group(3):
                        slide.vimeo_id = "%s/%s" % (match.group(2), match.group(3))
                    else:
                        slide.vimeo_id = match.group(2)
            else:
                slide.vimeo_id = False

    @api.depends("url", "document_google_url", "image_google_url", "video_url")
    def _compute_google_drive_id(self):

        for slide in self:
            url = (
                slide.url
                or slide.document_google_url
                or slide.image_google_url
                or slide.video_url
            )
            google_drive_id = False
            if url:
                match = re.match(self.GOOGLE_DRIVE_DOCUMENT_ID_REGEX, url)
                if match and len(match.groups()) == 2:
                    google_drive_id = match.group(2)

            slide.google_drive_id = google_drive_id

    @api.onchange("url", "document_google_url", "image_google_url", "video_url")
    def _on_change_url(self):

        self.check_singleton()
        if (
            self.url
            or self.document_google_url
            or self.image_google_url
            or self.video_url
        ):
            slide_metadata, _error = self._get_external_metadata()
            if slide_metadata:
                self.update(
                    {
                        key: value
                        for key, value in slide_metadata.items()
                        if not self[key]
                    }
                )

    @api.onchange("document_binary_content")
    def _on_change_document_binary_content(self):
        if (
            self.slide_category == "document"
            and self.source_type == "local_file"
            and self.document_binary_content
        ):
            completion_time = self._get_completion_time_pdf(
                base64.b64decode(self.document_binary_content)
            )
            if completion_time:
                self.completion_time = completion_time

    @api.onchange("slide_category")
    def _on_change_slide_category(self):
        if self.slide_category != "infographic" and self.image_binary_content:
            self.image_binary_content = False
        elif self.slide_category != "document" and self.document_binary_content:
            self.document_binary_content = False

    @api.depends("name", "channel_id.website_id.domain")
    def _compute_website_url(self):
        super()._compute_website_url()
        for slide in self:
            if slide.id:
                slide.website_url = f"/slides/slide/{self.env['ir.http']._slug(slide)}"

    @api.depends("channel_id.website_id.domain")
    def _compute_website_absolute_url(self):
        super()._compute_website_absolute_url()

    @api.depends("is_published")
    def _compute_website_share_url(self):
        self.website_share_url = False
        for slide in self:
            if slide.id:
                base_url = slide.channel_id.get_base_url()
                slide.website_share_url = "%s/slides/slide/%s/share" % (
                    base_url,
                    slide.id,
                )

    @api.depends("channel_id.can_publish")
    def _compute_can_publish(self):
        for record in self:
            record.can_publish = record.channel_id.can_publish

    @api.model
    def _get_can_publish_error_message(self):
        return self.env["slide.channel"]._get_can_publish_error_message()

    @api.model_create_multi
    def create(self, vals_list):
        default_channel_id = self.env.context.get("default_channel_id")
        channel_ids = [
            vals.get("channel_id") or default_channel_id for vals in vals_list
        ]
        can_publish_channel_ids = (
            self.env["slide.channel"]
            .browse([channel_id for channel_id in channel_ids if channel_id])
            .filtered(lambda c: c.can_publish)
            .ids
        )
        for vals, channel_id in zip(vals_list, channel_ids, strict=True):
            if channel_id not in can_publish_channel_ids:
                vals["date_published"] = False

            if vals.get("is_category"):
                vals["is_preview"] = True
                vals["is_published"] = True
            if vals.get("is_published") and not vals.get("date_published"):
                vals["date_published"] = datetime.datetime.now()

        slides = super().create(vals_list)

        for slide, vals in zip(slides, vals_list, strict=True):
            if (
                any(
                    vals.get(url_param)
                    for url_param in [
                        "url",
                        "video_url",
                        "document_google_url",
                        "image_google_url",
                    ]
                )
                and not self.env.context.get("install_mode")
                and not self.env.context.get("website_slides_skip_fetch_metadata")
            ):
                slide_metadata, _error = slide._get_external_metadata()
                if slide_metadata:
                    slide.update(
                        {
                            key: value
                            for key, value in slide_metadata.items()
                            if key not in vals
                        }
                    )

            if "completion_time" not in vals:
                slide._on_change_document_binary_content()

            if slide.is_published and not slide.is_category:
                slide._post_publication()

        published_slides = slides.filtered(
            lambda s: s.is_published and not s.is_category
        )
        published_slides.channel_id.channel_partner_ids._recompute_completion()
        return slides

    def write(self, vals):
        values = vals
        if values.get("is_category"):
            values["is_preview"] = True
            values["is_published"] = True

        if "slide_category" in values:
            if values["slide_category"] == "article":
                values = {"url": False, **values}
            else:
                values = {"html_content": False, **values}

        newly_published = (
            self.filtered(lambda slide: not slide.is_published)
            if values.get("is_published")
            else self.browse()
        )

        res = super().write(values)

        if newly_published:
            newly_published.date_published = datetime.datetime.now()
            newly_published._post_publication()

        if (
            any(
                values.get(url_param)
                for url_param in [
                    "url",
                    "video_url",
                    "document_google_url",
                    "image_google_url",
                ]
            )
            and not self.env.context.get("install_mode")
            and not self.env.context.get("website_slides_skip_fetch_metadata")
        ):
            for slide in self:
                slide_metadata, _error = slide._get_external_metadata()
                if slide_metadata:
                    slide.update(
                        {
                            key: value
                            for key, value in slide_metadata.items()
                            if key not in values and not slide[key]
                        }
                    )

        if "is_published" in values or "active" in values:
            self.filtered(
                lambda slide: (
                    not slide.active and not slide.is_category and slide.is_published
                )
            ).is_published = False
            self.channel_id.channel_partner_ids._recompute_completion()

        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        if (
            "slide.channel" not in self.env.context.get("__copy_data_seen", {})
            and "sequence" not in default
        ):
            default["sequence"] = 0
        return super().copy_data(default=default)

    def unlink(self):
        for category in self.filtered(lambda slide: slide.is_category):
            category.channel_id._move_category_slides(category, False)
        channel_partner_ids = self.channel_id.channel_partner_ids
        res = super().unlink()
        channel_partner_ids._recompute_completion()
        return res

    def _can_return_content(self, field_name=None, access_token=None):
        if self.website_published:
            return self.has_access("read")
        return super()._can_return_content(field_name, access_token)

    def message_post(self, *, message_type="notification", **kwargs):
        self.check_singleton()
        if message_type == "comment" and not self.channel_id.can_comment:
            _debug.logic("slide_comment_refused", reason="karma", slides=self)
            raise AccessError(_("Not enough karma to comment"))
        return super().message_post(message_type=message_type, **kwargs)

    def _get_access_action(self, access_uid=None, force_website=False):
        self.check_singleton()
        if force_website or self.website_published:
            return {
                "type": "ir.actions.act_url",
                "url": self.website_absolute_url,
                "target": "self",
                "target_type": "public",
                "res_id": self.id,
            }
        return super()._get_access_action(
            access_uid=access_uid, force_website=force_website
        )

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.check_singleton()
        if self.website_published:
            for _group_name, _group_method, group_data in groups:
                group_data["has_button_access"] = True

        return groups

    EMBED_URL_MAX_LENGTH = 512

    def _embed_increment(self, url):

        self.check_singleton()

        url_entry = self._normalize_embed_url(url)

        embed_entry = self.env["slide.embed"].search(
            [("url", "=", url_entry), ("slide_id", "=", self.id)], limit=1
        )

        if embed_entry:
            embed_entry._increment_fields_skiplock("count_views")
            embed_entry.invalidate_recordset(["count_views"])
        else:
            # The search above can race: two concurrent embeds of a URL with
            # no existing row can both miss it and both try to create one.
            # The (slide_id, url) unique constraint on slide.embed turns the
            # loser's create() into an IntegrityError instead of a silent
            # duplicate row; fall back to incrementing the row the winner
            # created.
            try:
                with self.env.cr.savepoint():
                    embed_entry = self.env["slide.embed"].create(
                        {
                            "slide_id": self.id,
                            "url": url_entry,
                        }
                    )
            except IntegrityError:
                embed_entry = self.env["slide.embed"].search(
                    [("url", "=", url_entry), ("slide_id", "=", self.id)], limit=1
                )
                embed_entry._increment_fields_skiplock("count_views")
                embed_entry.invalidate_recordset(["count_views"])

        return embed_entry

    @api.model
    def _normalize_embed_url(self, url):
        split = urlsplit(url or "")
        if not split.netloc:
            return False
        return f"{split.scheme}://{split.netloc}{split.path}"[
            : self.EMBED_URL_MAX_LENGTH
        ]

    def _post_publication(self):
        for slide in self.filtered(
            lambda slide: (
                slide.website_published and slide.channel_id.publish_template_id
            )
        ):
            publish_template = slide.channel_id.publish_template_id
            html_body = publish_template.with_context(
                base_url=slide.get_base_url()
            )._render_field("body_html", slide.ids)[slide.id]
            subject = publish_template._render_field("subject", slide.ids)[slide.id]
            kwargs = {}
            reply_to = publish_template._render_field("reply_to", slide.ids)[slide.id]
            if reply_to:
                kwargs["reply_to"] = reply_to
            slide.channel_id.with_context(
                mail_post_autofollow_author_skip=True
            ).message_post(
                subject=subject,
                body=html_body,
                subtype_xmlid="website_slides.mt_channel_slide_published",
                email_layout_xmlid="mail.mail_notification_light",
                **kwargs,
            )
        return True

    def _send_share_email(self, email, fullscreen):
        courses_without_templates = self.channel_id.filtered(
            lambda channel: not channel.share_slide_template_id
        )
        if courses_without_templates:
            _debug.logic(
                "slide_share_refused",
                reason="no_share_template",
                channels=courses_without_templates,
            )
            raise UserError(
                _(
                    'Impossible to send emails. Select a "Share Template" for courses %(course_names)s first',
                    course_names=", ".join(courses_without_templates.mapped("name")),
                )
            )
        Channel = self.env["slide.channel"]
        return [
            Channel._send_share_mail(
                record.channel_id.share_slide_template_id,
                record,
                email,
                fullscreen=fullscreen,
            )
            for record in self
        ]

    def action_like(self):
        self.check_access("read")
        return self._action_vote(upvote=True)

    def action_dislike(self):
        self.check_access("read")
        return self._action_vote(upvote=False)

    def _action_vote(self, upvote=True):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env["slide.slide.partner"].sudo()
        slide_partners = SlidePartnerSudo.search(
            [
                ("slide_id", "in", self.ids),
                ("partner_id", "=", self.env.user.partner_id.id),
            ]
        )
        new_slides = self_sudo - slide_partners.slide_id

        target_vote = 1 if upvote else -1
        toggled_off = slide_partners.filtered(
            lambda partner: partner.vote == target_vote
        )
        toggled_off.vote = 0
        (slide_partners - toggled_off).vote = target_vote

        SlidePartnerSudo.create(
            [
                {
                    "slide_id": new_slide.id,
                    "channel_id": new_slide.channel_id.id,
                    "partner_id": self.env.user.partner_id.id,
                    "vote": target_vote,
                }
                for new_slide in new_slides
            ]
        )

    def action_set_viewed(self, quiz_attempts_inc=False):
        if any(not slide.channel_id.is_member for slide in self):
            _debug.logic("slide_view_refused", reason="not_a_member", slides=self)
            raise UserError(
                _("You cannot mark a slide as viewed if you are not among its members.")
            )

        return bool(
            self._action_set_viewed(
                self.env.user.partner_id, quiz_attempts_inc=quiz_attempts_inc
            )
        )

    def _action_set_viewed(self, target_partner, quiz_attempts_inc=False):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env["slide.slide.partner"].sudo()
        existing_sudo = SlidePartnerSudo.search(
            [("slide_id", "in", self.ids), ("partner_id", "=", target_partner.id)]
        )
        if quiz_attempts_inc and existing_sudo:
            existing_sudo._increment_fields_skiplock("quiz_attempts_count")
            existing_sudo.invalidate_recordset(["quiz_attempts_count"])

        new_slides = self_sudo - existing_sudo.mapped("slide_id")
        return SlidePartnerSudo.create(
            [
                {
                    "slide_id": new_slide.id,
                    "channel_id": new_slide.channel_id.id,
                    "partner_id": target_partner.id,
                    "quiz_attempts_count": 1 if quiz_attempts_inc else 0,
                    "vote": 0,
                }
                for new_slide in new_slides
            ]
        )

    def action_mark_completed(self):
        if any(not slide.can_self_mark_completed for slide in self):
            raise UserError(
                _(
                    "You cannot mark a slide as completed if you are not among its members."
                )
            )

        return self._action_mark_completed()

    def _action_mark_completed(self):
        uncompleted_slides = self.filtered(lambda slide: not slide.user_has_completed)

        target_partner = self.env.user.partner_id
        uncompleted_slides._action_set_quiz_done()
        SlidePartnerSudo = self.env["slide.slide.partner"].sudo()
        existing_sudo = SlidePartnerSudo.search(
            [
                ("slide_id", "in", uncompleted_slides.ids),
                ("partner_id", "=", target_partner.id),
            ]
        )
        existing_sudo.write({"completed": True})

        new_slides = uncompleted_slides.sudo() - existing_sudo.mapped("slide_id")
        SlidePartnerSudo.create(
            [
                {
                    "slide_id": new_slide.id,
                    "channel_id": new_slide.channel_id.id,
                    "partner_id": target_partner.id,
                    "vote": 0,
                    "completed": True,
                }
                for new_slide in new_slides
            ]
        )

    def action_mark_uncompleted(self):
        if any(not slide.can_self_mark_uncompleted for slide in self):
            raise UserError(
                _(
                    "You cannot mark a slide as uncompleted if you are not among its members."
                )
            )

        completed_slides = self.filtered(lambda slide: slide.user_has_completed)

        completed_slides._action_set_quiz_done(completed=False)

        self.env["slide.slide.partner"].sudo().search(
            [
                ("slide_id", "in", completed_slides.ids),
                ("partner_id", "=", self.env.user.partner_id.id),
            ]
        ).completed = False

    def _get_quiz_gains(self):
        self.check_singleton()
        return [
            self.quiz_first_attempt_reward,
            self.quiz_second_attempt_reward,
            self.quiz_third_attempt_reward,
            self.quiz_fourth_attempt_reward,
        ]

    def _get_quiz_reward(self, attempts_count, done=True):
        self.check_singleton()
        if not self.has_questions:
            return 0
        gains = self._get_quiz_gains()
        index = (attempts_count - 1) if done else attempts_count
        return gains[max(0, min(index, len(gains) - 1))]

    def _action_set_quiz_done(self, completed=True):
        if any(
            not slide.channel_id.is_member or not slide.website_published
            for slide in self
        ):
            raise UserError(
                _(
                    "You cannot mark a slide quiz as completed if you are not among its members or it is unpublished."
                )
                if completed
                else _(
                    "You cannot mark a slide quiz as not completed if you are not among its members or it is unpublished."
                )
            )

        for slide in self:
            user_membership_sudo = slide.user_membership_id.sudo()
            if (
                not user_membership_sudo
                or user_membership_sudo.completed == completed
                or not user_membership_sudo.quiz_attempts_count
                or not slide.has_questions
            ):
                continue

            points = slide._get_quiz_reward(user_membership_sudo.quiz_attempts_count)
            if points:
                if completed:
                    reason = _("Quiz Completed")
                else:
                    points *= -1
                    reason = _("Quiz Set Uncompleted")
                self.env.user.sudo()._add_karma(points, slide, reason)

        return True

    def action_view_embeds(self):
        self.check_singleton()

        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "website_slides.slide_embed_action"
        )
        action["context"] = {"search_default_slide_id": self.id}
        return action

    def _check_quiz_survey(self):
        for slide in self.filtered(lambda s: not s.survey_id):
            survey = (
                self.env["survey.survey"]
                .sudo()
                .create(
                    {
                        "title": slide.name or _("Quiz"),
                        "scoring_type": "scoring_without_answers",
                        "scoring_success_min": 100.0,
                        "questions_layout": "one_page",
                        "questions_selection": "all",
                        "access_mode": "public",
                        "certification": False,
                        "is_attempts_limited": False,
                        "active": True,
                    }
                )
            )
            slide.survey_id = survey

    def _get_quiz_info(self, target_partner, quiz_done=False):
        result = dict.fromkeys(self.ids, False)
        slide_partners = (
            self.env["slide.slide.partner"]
            .sudo()
            .search(
                [
                    ("slide_id", "in", self.ids),
                    ("partner_id", "=", target_partner.id),
                ]
            )
        )
        slide_partners_map = {sp.slide_id.id: sp for sp in slide_partners}
        for slide in self:
            first_attempt_reward = (
                slide._get_quiz_reward(1) if slide.has_questions else 0
            )
            info = {
                "quiz_karma_max": first_attempt_reward,
                "quiz_karma_gain": first_attempt_reward,
                "quiz_karma_won": 0,
                "quiz_attempts_count": 0,
            }
            result[slide.id] = info
            slide_partner = slide_partners_map.get(slide.id)
            attempts = slide_partner.quiz_attempts_count if slide_partner else 0
            if slide.has_questions and attempts:
                info["quiz_attempts_count"] = attempts
                info["quiz_karma_gain"] = slide._get_quiz_reward(attempts, done=False)
                if quiz_done or slide_partner.completed:
                    info["quiz_karma_won"] = slide._get_quiz_reward(attempts)
        return result

    EXTERNAL_FETCH_TIMEOUT = 3
    THUMBNAIL_MAX_BYTES = 5 * 1024 * 1024

    @api.model
    def _get_external_json(self, url, params=None, not_found_message=None):
        try:
            response = self.env["ir.egress"].request(
                "GET",
                url,
                purpose="slide_metadata",
                timeout=self.EXTERNAL_FETCH_TIMEOUT,
                params=params or {},
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            resp = error.response
            if not_found_message and resp is not None and resp.status_code == 404:
                return {}, not_found_message
            return {}, self._log_external_metadata_error(
                url, resp.text if resp else error
            )
        except requests.exceptions.RequestException as error:
            return {}, self._log_external_metadata_error(url, error)

        if "application/json" not in (response.headers.get("content-type") or ""):
            return {}, self._log_external_metadata_error(url, "response is not JSON")

        try:
            payload = response.json()
        except ValueError as error:
            return {}, self._log_external_metadata_error(url, error)

        if isinstance(payload, dict) and payload.get("error"):
            reason = payload["error"].get("errors", [{}])[0].get("reason")
            return {}, self._log_external_metadata_error(
                url, reason or payload["error"]
            )
        return payload, None

    @api.model
    def _log_external_metadata_error(self, url, detail):
        message = str(detail)[:500]
        _logger.warning("Could not fetch slide metadata from %s: %s", url, message)
        return message

    @api.model
    def _get_thumbnail(self, url):
        try:
            response = self.env["ir.egress"].request(
                "GET",
                url,
                purpose="slide_thumbnail",
                timeout=self.EXTERNAL_FETCH_TIMEOUT,
                max_bytes=self.THUMBNAIL_MAX_BYTES,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            _logger.debug("Could not download slide thumbnail %s", url, exc_info=True)
            return False
        if not (response.headers.get("content-type") or "").startswith("image/"):
            return False
        content = response.content[: self.THUMBNAIL_MAX_BYTES]
        return base64.b64encode(content) if content else False

    def _set_thumbnail(self, slide_metadata, thumbnail_url, image_url_only):
        if not thumbnail_url:
            return
        if image_url_only:
            slide_metadata["image_url"] = thumbnail_url
        else:
            image = self._get_thumbnail(thumbnail_url)
            if image:
                slide_metadata["image_1920"] = image

    def _get_external_metadata(self, image_url_only=False):
        self.check_singleton()

        slide_metadata = {}
        error = False
        if self.slide_category == "video" and self.video_source_type == "youtube":
            slide_metadata, error = self._get_youtube_metadata(image_url_only)
        elif (
            self.slide_category == "video" and self.video_source_type == "google_drive"
        ):
            slide_metadata, error = self._get_google_drive_metadata(image_url_only)
        elif self.slide_category == "video" and self.video_source_type == "vimeo":
            slide_metadata, error = self._get_vimeo_metadata(image_url_only)
        elif (
            self.slide_category in ["document", "infographic"]
            and self.source_type == "external"
        ):
            slide_metadata, error = self._get_google_drive_metadata(image_url_only)

        return slide_metadata, error

    def _get_youtube_metadata(self, image_url_only=False):

        self.check_singleton()
        response, error = self._get_external_json(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "fields": "items(id,snippet,contentDetails)",
                "id": self.youtube_id,
                "key": self._get_google_app_key(),
                "part": "snippet,contentDetails",
            },
            not_found_message=_(
                "Your video could not be found on YouTube, please check the link and/or privacy settings"
            ),
        )
        if error:
            return {}, error
        if not response.get("items"):
            return {}, _(
                "Your video could not be found on YouTube, please check the link and/or privacy settings"
            )

        slide_metadata = {"slide_type": "youtube_video"}
        youtube_values = response["items"][0]
        youtube_duration = youtube_values.get("contentDetails", {}).get("duration")
        if youtube_duration:
            parsed_duration = re.search(
                r"^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$", youtube_duration
            )
            if parsed_duration:
                slide_metadata["completion_time"] = (
                    (int(parsed_duration.group(1) or 0))
                    + (int(parsed_duration.group(2) or 0) / 60)
                    + (round(int(parsed_duration.group(3) or 0) / 60) / 60)
                )

        snippet = youtube_values.get("snippet")
        if snippet:
            slide_metadata.update(
                {
                    "name": snippet["title"],
                    "description": snippet["description"],
                }
            )
            self._set_thumbnail(
                slide_metadata,
                snippet.get("thumbnails", {}).get("high", {}).get("url"),
                image_url_only,
            )

        return slide_metadata, None

    @api.model
    def _get_google_app_key(self):
        return (
            self.env["website"]
            .get_current_website()
            .sudo()
            .website_slide_google_app_key
        )

    def _get_google_drive_metadata(self, image_url_only=False):

        self.check_singleton()
        google_drive_values, error = self._get_external_json(
            "https://www.googleapis.com/drive/v2/files/%s" % self.google_drive_id,
            params={"projection": "BASIC", "key": self._get_google_app_key()},
            not_found_message=_(
                "Your file could not be found on Google Drive, please check the link and/or privacy settings"
            ),
        )
        if error:
            return {}, error

        slide_metadata = {"name": google_drive_values.get("title")}

        thumbnail_link = google_drive_values.get("thumbnailLink")
        if thumbnail_link:
            self._set_thumbnail(
                slide_metadata, thumbnail_link.replace("=s220", ""), image_url_only
            )

        if self.slide_category == "document":
            mime_type = google_drive_values.get("mimeType")
            slide_type = self.GOOGLE_DRIVE_MIME_TYPES.get(mime_type)
            if not slide_type and mime_type:
                if mime_type.startswith("image/"):
                    slide_type = "image"
                elif mime_type.startswith("video/"):
                    slide_type = "google_drive_video"
            if slide_type:
                slide_metadata["slide_type"] = slide_type
            if slide_type == "pdf" and google_drive_values.get("downloadUrl"):
                completion_time = self._get_completion_time_google_drive_pdf(
                    google_drive_values["downloadUrl"]
                )
                if completion_time:
                    slide_metadata["completion_time"] = completion_time

        elif self.slide_category == "video":
            completion_time = (
                round(
                    float(
                        google_drive_values.get("videoMediaMetadata", {}).get(
                            "durationMillis", 0
                        )
                    )
                    / (60 * 1000)
                )
                / 60
            )
            if completion_time:
                slide_metadata["completion_time"] = completion_time

        return slide_metadata, None

    def _get_completion_time_google_drive_pdf(self, download_url):
        try:
            pdf_response = self.env["ir.egress"].request(
                "GET",
                download_url,
                purpose="slide_metadata",
                timeout=self.EXTERNAL_FETCH_TIMEOUT,
            )
            pdf_response.raise_for_status()
        except requests.exceptions.RequestException:
            _logger.debug(
                "Could not derive completion_time from the Google Drive PDF at %s",
                download_url,
                exc_info=True,
            )
            return False
        return self._get_completion_time_pdf(pdf_response.content)

    def _get_vimeo_metadata(self, image_url_only=False):

        self.check_singleton()
        vimeo_values, error = self._get_external_json(
            "https://vimeo.com/api/oembed.json?%s" % urlencode({"url": self.video_url}),
            not_found_message=_(
                "Your video could not be found on Vimeo, please check the link and/or privacy settings"
            ),
        )
        if error:
            return {}, error
        if not vimeo_values:
            return {}, _("Please enter a valid Vimeo video link")

        slide_metadata = {"slide_type": "vimeo_video"}
        if vimeo_values.get("title"):
            slide_metadata["name"] = vimeo_values["title"]
        if vimeo_values.get("description"):
            slide_metadata["description"] = vimeo_values["description"]
        if vimeo_values.get("duration"):
            slide_metadata["completion_time"] = (
                round(vimeo_values["duration"] / 60) / 60
            )
        self._set_thumbnail(
            slide_metadata, vimeo_values.get("thumbnail_url"), image_url_only
        )

        return slide_metadata, None

    def _get_default_website_meta(self):
        res = super()._get_default_website_meta()
        res["default_opengraph"]["og:title"] = res["default_twitter"][
            "twitter:title"
        ] = self.name
        res["default_opengraph"]["og:description"] = res["default_twitter"][
            "twitter:description"
        ] = html2plaintext(self.description)
        res["default_opengraph"]["og:image"] = res["default_twitter"][
            "twitter:image"
        ] = self.env["website"].image_url(self, "image_1024")
        res["default_meta_description"] = html2plaintext(self.description)
        return res

    def _get_completion_time_pdf(self, data_bytes):

        if data_bytes.startswith(b"%PDF-"):
            try:
                pdf = PdfReader(io.BytesIO(data_bytes))
                return (5 * len(pdf.pages)) / 60
            except Exception:
                _logger.debug(
                    "Could not read PDF to estimate its completion time", exc_info=True
                )

        return False

    def _get_next_category(self):
        channel_category_ids = self.channel_id.slide_category_ids.ids
        if not channel_category_ids:
            return self.env["slide.slide"]
        if not self.category_id and all(
            self.channel_id.slide_ids.filtered(
                lambda s: not s.is_category and not s.category_id
            ).mapped("user_has_completed")
        ):
            return self.env["slide.slide"].browse(channel_category_ids[0])
        elif (
            self.user_has_completed_category
            and self.category_id.id in channel_category_ids
            and self.category_id.id != channel_category_ids[-1]
        ):
            index_current_category = channel_category_ids.index(self.category_id.id)
            return self.env["slide.slide"].browse(
                channel_category_ids[index_current_category + 1]
            )
        return self.env["slide.slide"]

    def get_backend_menu_id(self):
        return self.env.ref("website_slides.website_slides_menu_root").id

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options["displayDescription"]
        search_fields = ["name"]
        fetch_fields = ["id", "name"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "website_url": {"name": "url", "type": "text", "truncate": False},
            "extra_link": {"name": "course", "type": "text"},
            "extra_link_url": {"name": "course_url", "type": "text", "truncate": False},
        }
        if with_description:
            search_fields.append("description")
            fetch_fields.append("description")
            mapping["description"] = {
                "name": "description",
                "type": "text",
                "html": True,
                "match": True,
            }
        return {
            "model": "slide.slide",
            "base_domain": [website.website_domain()],
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-graduation-cap",
            "order": "name desc, id desc"
            if "name desc" in order
            else "name asc, id desc",
        }

    ICON_PER_SLIDE_CATEGORY = {
        "infographic": "fa-regular fa-file-image",
        "article": "fa-regular fa-file-lines",
        "document": "fa-regular fa-file-pdf",
        "video": "fa-regular fa-circle-play",
        "quiz": "fa-regular fa-circle-question",
        "certification": "fa-trophy",
    }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        icon_per_category = self.ICON_PER_SLIDE_CATEGORY
        results_data = super()._search_render_results(
            fetch_fields, mapping, icon, limit
        )
        for slide, data in zip(self, results_data, strict=False):
            data["_fa"] = icon_per_category.get(
                slide.slide_category, "fa-regular fa-file-pdf"
            )
            data["url"] = slide.website_absolute_url
            data["course"] = _("Course: %s", slide.channel_id.name)
            data["course_url"] = slide.channel_id.website_absolute_url
        return results_data

    def get_base_url(self):
        return self.channel_id.get_base_url()
