# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import io
import logging
import re
import requests

from dateutil.relativedelta import relativedelta
from markupsafe import Markup
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, AccessError
from odoo.http import request
from odoo.tools import html2plaintext, sql
from odoo.tools.pdf import PdfFileReader

_logger = logging.getLogger(__name__)


class SlideSlidePartner(models.Model):
    _name = 'slide.slide.partner'
    _description = 'Slide / Partner decorated m2m'
    _table = 'slide_slide_partner'
    _rec_name = 'partner_id'

    slide_id = fields.Many2one('slide.slide', string="Content", ondelete="cascade", index=True, required=True)
    slide_category = fields.Selection(related='slide_id.slide_category')
    channel_id = fields.Many2one(
        'slide.channel', string="Channel",
        related="slide_id.channel_id", store=True, index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', index=True, required=True, ondelete='cascade')
    vote = fields.Integer('Vote', default=0)
    completed = fields.Boolean('Completed')
    quiz_attempts_count = fields.Integer('Quiz attempts count', default=0)

    _slide_partner_uniq = models.Constraint(
        'unique(slide_id, partner_id)',
        'A partner membership to a slide must be unique!',
    )
    _check_vote = models.Constraint(
        'CHECK(vote IN (-1, 0, 1))',
        'The vote must be 1, 0 or -1.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        completed = res.filtered('completed')
        if completed:
            completed._recompute_completion()
        return res

    def write(self, values):
        slides_completion_to_recompute = self.env['slide.slide.partner']
        if 'completed' in values:
            slides_completion_to_recompute = self.filtered(
                lambda slide_partner: slide_partner.completed != values['completed'])

        res = super().write(values)

        if slides_completion_to_recompute:
            slides_completion_to_recompute._recompute_completion()

        return res

    def _recompute_completion(self):
        self.env['slide.channel.partner'].search([
            ('channel_id', 'in', self.channel_id.ids),
            ('partner_id', 'in', self.partner_id.ids),
            ('member_status', 'not in', ('completed', 'invited'))
        ])._recompute_completion()


class SlideTag(models.Model):
    """ Tag to search slides across channels. """
    _name = 'slide.tag'
    _description = 'Slide Tag'

    name = fields.Char('Name', required=True, translate=True)

    _slide_tag_unique = models.Constraint(
        'UNIQUE(name)',
        'A tag must be unique!',
    )


class SlideSlide(models.Model):
    _name = 'slide.slide'
    _inherit = [
        'mail.thread',
        'image.mixin',
        'website.seo.metadata',
        'website.published.mixin',
        'website.searchable.mixin',
    ]
    _description = 'Slides'
    _mail_post_access = 'read'
    _order_by_strategy = {
        'sequence': 'sequence asc, id asc',
        'most_viewed': 'total_views desc',
        'most_voted': 'likes desc',
        'latest': 'date_published desc',
    }
    _order = 'sequence asc, is_category asc, id asc'
    _partner_unfollow_enabled = True

    YOUTUBE_VIDEO_ID_REGEX = r'^(?:(?:https?:)?//)?(?:www\.|m\.)?(?:youtu\.be/|youtube(-nocookie)?\.com/(?:embed/|v/|shorts/|live/|watch\?v=|watch\?.+&v=))((?:\w|-){11})\S*$'
    GOOGLE_DRIVE_DOCUMENT_ID_REGEX = r'(^https:\/\/docs.google.com|^https:\/\/drive.google.com).*\/d\/([^\/]*)'
    VIMEO_VIDEO_ID_REGEX = r'\/\/(player.)?vimeo.com\/(?:[a-z]*\/)*([0-9]{6,11})\/?([0-9a-z]{6,11})?[?]?.*'

    # description
    name = fields.Char('Title', required=True, translate=True)
    image_1920 = fields.Image(compute="_compute_image_1920", store=True, readonly=False)  # image.mixin override
    active = fields.Boolean(default=True, tracking=100)
    sequence = fields.Integer('Sequence', default=0)
    user_id = fields.Many2one('res.users', string='Uploaded by', default=lambda self: self.env.uid)
    description = fields.Html('Description', translate=True, sanitize_attributes=False, sanitize_overridable=True)
    channel_id = fields.Many2one('slide.channel', string="Course", required=True, ondelete='cascade')
    tag_ids = fields.Many2many('slide.tag', 'rel_slide_tag', 'slide_id', 'tag_id', string='Tags')
    is_preview = fields.Boolean('Allow Preview', default=False, help="The course is accessible by anyone : the users don't need to join the channel to access the content of the course.")
    is_new_slide = fields.Boolean('Is New Slide', compute='_compute_is_new_slide')
    completion_time = fields.Float('Duration', digits=(10, 4), compute='_compute_category_completion_time', recursive=True, readonly=False, store=True)
    # Categories
    is_category = fields.Boolean('Is a category', default=False)
    category_id = fields.Many2one('slide.slide', string="Section", compute="_compute_category_id", store=True)
    slide_ids = fields.One2many('slide.slide', "category_id", string="Content")
    # subscribers
    partner_ids = fields.Many2many('res.partner', 'slide_slide_partner', 'slide_id', 'partner_id',
                                   string='Subscribers', groups='website_slides.group_website_slides_officer', copy=False)
    slide_partner_ids = fields.One2many('slide.slide.partner', 'slide_id', string='Subscribers information', groups='website_slides.group_website_slides_officer', copy=False)
    user_membership_id = fields.Many2one(
        'slide.slide.partner', string="Subscriber information",
        compute='_compute_user_membership_id', compute_sudo=False,
        help="Subscriber information for the current logged in user")
    # current user membership
    user_vote = fields.Integer('User vote', compute='_compute_user_membership_id', compute_sudo=False)
    user_has_completed = fields.Boolean('Is Member', compute='_compute_user_membership_id', compute_sudo=False)
    user_has_completed_category = fields.Boolean('Is Category Completed', compute='_compute_category_completed')
    # Quiz related fields
    question_ids = fields.One2many("slide.question", "slide_id", string="Questions", copy=True)
    questions_count = fields.Integer(string="Numbers of Questions", compute='_compute_questions_count')
    quiz_first_attempt_reward = fields.Integer("Reward: first attempt", default=10)
    quiz_second_attempt_reward = fields.Integer("Reward: second attempt", default=7)
    quiz_third_attempt_reward = fields.Integer("Reward: third attempt", default=5,)
    quiz_fourth_attempt_reward = fields.Integer("Reward: every attempt after the third try", default=2)
    # content
    can_self_mark_completed = fields.Boolean('Can Mark Completed', compute='_compute_mark_complete_actions',
        help='The slide can be marked as completed even without opening it')
    can_self_mark_uncompleted = fields.Boolean('Can Mark Uncompleted', compute='_compute_mark_complete_actions',
        help='The slide can be marked as not completed and the progression')
    slide_category = fields.Selection([
        ('infographic', 'Image'),
        ('article', 'Article'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('quiz', "Quiz")],
        string='Category', required=True,
        default='document')
    source_type = fields.Selection([
        ('local_file', 'Upload from Device'),
        ('external', 'Retrieve from Google Drive')],
        default='local_file', required=True)
    # generic
    url = fields.Char('External URL', help="URL of the Google Drive file or URL of the YouTube video")
    binary_content = fields.Binary('File', attachment=True)
    slide_resource_ids = fields.One2many('slide.slide.resource', 'slide_id', string="Additional Resource for this slide", copy=True)
    slide_resource_downloadable = fields.Boolean('Allow Download', default=False, help="Allow the user to download the content of the slide.")
    # google
    google_drive_id = fields.Char('Google Drive ID of the external URL', compute='_compute_google_drive_id')
    # content - webpage
    html_content = fields.Html(
        "HTML Content", translate=True,
        sanitize_attributes=False, sanitize_form=False, sanitize_overridable=True,
        help="Custom HTML content for slides of category 'Article'.")
    # content - images
    image_binary_content = fields.Binary('Image Content', related='binary_content', readonly=False) # Used to filter file input to images only
    image_google_url = fields.Char('Image Link', related='url', readonly=False,
        help="Link of the image (we currently only support Google Drive as source)")
    # content - documents
    slide_icon_class = fields.Char('Slide Icon fa-class', compute='_compute_slide_icon_class')
    slide_type = fields.Selection([
        ('image', 'Image'),
        ('article', 'Article'),
        ('quiz', 'Quiz'),
        ('pdf', 'PDF'),
        ('sheet', 'Sheet (Excel, Google Sheet, ...)'),
        ('doc', 'Document (Word, Google Doc, ...)'),
        ('slides', 'Slides (PowerPoint, Google Slides, ...)'),
        ('youtube_video', 'YouTube Video'),
        ('google_drive_video', 'Google Drive Video'),
        ('vimeo_video', 'Vimeo Video')],
        string="Slide Type", compute='_compute_slide_type', store=True, readonly=False,
        help="Subtype of the slide category, allows more precision on the actual file type / source type.")
    document_google_url = fields.Char('Document Link', related='url', readonly=False,
        help="Link of the document (we currently only support Google Drive as source)")
    document_binary_content = fields.Binary('PDF Content', related='binary_content', readonly=False) # Used to filter file input to PDF only
    # content - videos
    video_url = fields.Char('Video Link', related='url', readonly=False,
        help="Link of the video (we support YouTube, Google Drive and Vimeo as sources)")
    video_source_type = fields.Selection([
        ('youtube', 'YouTube'),
        ('google_drive', 'Google Drive'),
        ('vimeo', 'Vimeo')],
        string='Video Source', compute="_compute_video_source_type")
    youtube_id = fields.Char('Video YouTube ID', compute='_compute_youtube_id')
    vimeo_id = fields.Char('Video Vimeo ID', compute='_compute_vimeo_id')
    # website
    website_id = fields.Many2one(related='channel_id.website_id', readonly=True)
    date_published = fields.Datetime('Publish Date', readonly=True, tracking=False, copy=False)
    likes = fields.Integer('Likes', compute='_compute_like_info', store=True, compute_sudo=False)
    dislikes = fields.Integer('Dislikes', compute='_compute_like_info', store=True, compute_sudo=False)
    embed_code = fields.Html('Embed Code', readonly=True, compute='_compute_embed_code', sanitize=False)
    embed_code_external = fields.Html('External Embed Code', readonly=True, compute='_compute_embed_code', sanitize=False,
        help="Same as 'Embed Code' but used to embed the content on an external website.")
    website_share_url = fields.Char('Share URL', compute='_compute_website_share_url')
    # views
    embed_ids = fields.One2many('slide.embed', 'slide_id', string="External Slide Embeds")
    embed_count = fields.Integer('# of Embeds', compute='_compute_embed_counts')
    slide_views = fields.Integer('# of Website Views', store=True, compute="_compute_slide_views")
    public_views = fields.Integer('# of Public Views', copy=False, default=0, readonly=True)
    total_views = fields.Integer("# Total Views", default="0", compute='_compute_total', store=True)
    # comments
    comments_count = fields.Integer('Number of comments', compute="_compute_comments_count")
    # channel
    channel_type = fields.Selection(related="channel_id.channel_type", string="Channel type")
    channel_allow_comment = fields.Boolean(related="channel_id.allow_comment", string="Allows comment")
    # Statistics in case the slide is a category
    nbr_document = fields.Integer("Number of Documents", compute='_compute_slides_statistics', store=True)
    nbr_video = fields.Integer("Number of Videos", compute='_compute_slides_statistics', store=True)
    nbr_infographic = fields.Integer("Number of Images", compute='_compute_slides_statistics', store=True)
    nbr_article = fields.Integer("Number of Articles", compute='_compute_slides_statistics', store=True)
    nbr_quiz = fields.Integer("Number of Quizs", compute="_compute_slides_statistics", store=True)
    total_slides = fields.Integer(compute='_compute_slides_statistics', store=True)
    is_published = fields.Boolean(tracking=1)
    website_published = fields.Boolean(tracking=False)

    _exclusion_html_content_and_url = models.Constraint(
        'CHECK(html_content IS NULL OR url IS NULL)',
        'A slide is either filled with a url or HTML content. Not both.',
    )

    @api.depends('slide_category', 'source_type', 'image_binary_content')
    def _compute_image_1920(self):
        for slide in self:
            if slide.slide_category == 'infographic' and slide.source_type == 'local_file' and slide.image_binary_content:
                slide.image_1920 = slide.image_binary_content
            elif not slide.image_1920:
                slide.image_1920 = False

    @api.depends('date_published', 'is_published')
    def _compute_is_new_slide(self):
        for slide in self:
            slide.is_new_slide = slide.date_published > fields.Datetime.now() - relativedelta(days=7) if slide.is_published else False

    def _get_placeholder_filename(self, field):
        return self.channel_id._get_placeholder_filename(field)

    @api.depends('channel_id.slide_ids.is_category', 'channel_id.slide_ids.sequence', 'channel_id.slide_ids.slide_ids')
    def _compute_category_id(self):
        """ Will take all the slides of the channel for which the index is higher
        than the index of this category and lower than the index of the next category.

        Lists are manually sorted because when adding a new browse record order
        will not be correct as the added slide would actually end up at the
        first place no matter its sequence."""
        self.category_id = False  # initialize whatever the state

        channel_slides = {}
        for slide in self:
            if slide.channel_id.id not in channel_slides:
                channel_slides[slide.channel_id.id] = slide.channel_id.slide_ids

        for slides in channel_slides.values():
            current_category = self.env['slide.slide']
            slide_list = list(slides)
            slide_list.sort(key=lambda s: (s.sequence, not s.is_category))
            for slide in slide_list:
                if slide.is_category:
                    current_category = slide
                elif slide.category_id != current_category:
                    slide.category_id = current_category.id

    @api.depends('slide_category', 'question_ids', 'channel_id.is_member')
    @api.depends_context('uid')
    def _compute_mark_complete_actions(self):
        """Determine if the slide can be marked as (un)completed.

        We can't mark a slide with questions as completed manually because we need to
        complete the quiz first. But we can mark as uncompleted a slide with questions,
        and the answers will be reset, the karma removed, etc (see mark_uncompleted).
        """
        for slide in self:
            slide.can_self_mark_uncompleted = slide.website_published and slide.channel_id.is_member
            slide.can_self_mark_completed = (
                slide.website_published
                and slide.channel_id.is_member
                and slide.slide_category != 'quiz'
                and not slide.question_ids
            )

    @api.depends('question_ids')
    def _compute_questions_count(self):
        for slide in self:
            slide.questions_count = len(slide.question_ids)

    @api.depends('website_message_ids.res_id', 'website_message_ids.model', 'website_message_ids.message_type')
    def _compute_comments_count(self):
        for slide in self:
            slide.comments_count = len(slide.website_message_ids)

    @api.depends('slide_views', 'public_views')
    def _compute_total(self):
        for record in self:
            record.total_views = record.slide_views + record.public_views

    @api.depends('slide_partner_ids.vote')
    def _compute_like_info(self):
        rg_data = self.env['slide.slide.partner'].sudo()._read_group(
            [('slide_id', 'in', self.ids), ('vote', 'in', (-1, 1))],
            ['slide_id', 'vote'], ['__count'],
        )
        mapped_data = {
            (slide.id, vote): count
            for slide, vote, count in rg_data
        }

        for slide in self:
            slide.likes = mapped_data.get((slide.id, 1), 0)
            slide.dislikes = mapped_data.get((slide.id, -1), 0)

    @api.depends('slide_partner_ids.slide_id')
    def _compute_slide_views(self):
        # TODO awa: tried compute_sudo, for some reason it doesn't work in here...
        read_group_res = self.env['slide.slide.partner'].sudo()._read_group(
            [('slide_id', 'in', self.ids)],
            ['slide_id'],
            aggregates=['__count'],
        )
        mapped_data = {slide.id: count for slide, count in read_group_res}
        for slide in self:
            slide.slide_views = mapped_data.get(slide.id, 0)

    @api.depends('embed_ids.slide_id')
    def _compute_embed_counts(self):
        read_group_res = self.env['slide.embed']._read_group(
            [('slide_id', 'in', self.ids)],
            ['slide_id'],
            ['count_views:sum'],
        )
        mapped_data = {
            slide.id: count_views_sum
            for slide, count_views_sum in read_group_res
        }

        for slide in self:
            slide.embed_count = mapped_data.get(slide.id, 0)

    @api.depends('slide_ids.sequence', 'slide_ids.active', 'slide_ids.slide_category', 'slide_ids.is_published', 'slide_ids.is_category')
    def _compute_slides_statistics(self):
        # Do not use dict.fromkeys(self.ids, dict()) otherwise it will use the same dictionnary for all keys.
        # Therefore, when updating the dict of one key, it updates the dict of all keys.
        keys = ['nbr_%s' % slide_category for slide_category in self.env['slide.slide']._fields['slide_category'].get_values(self.env)]
        default_vals = dict((key, 0) for key in keys + ['total_slides'])

        res = self.env['slide.slide']._read_group(
            [('is_published', '=', True), ('category_id', 'in', self.filtered('is_category').ids), ('is_category', '=', False)],
            ['category_id', 'slide_category'], ['__count'])

        result = {category_id: dict(default_vals) for category_id in self.ids}
        for category, slide_category, count in res:
            result[category.id][f'nbr_{slide_category}'] = count
            result[category.id]['total_slides'] += count

        for record in self:
            record.update(result.get(record._origin.id, default_vals))

    @api.depends('category_id', 'category_id.slide_ids', 'category_id.slide_ids.user_has_completed')
    def _compute_category_completed(self):
        for slide in self:
            if not slide.category_id:
                slide.user_has_completed_category = False
            else:
                slide.user_has_completed_category = all(slide.category_id.slide_ids.mapped('user_has_completed'))

    @api.depends('slide_ids.sequence', 'slide_ids.active', 'slide_ids.completion_time', 'slide_ids.is_published', 'slide_ids.is_category')
    def _compute_category_completion_time(self):
        # We don't use read_group() function, otherwise we will have issue with flushing the
        # data as completion_time is recursive and when it'll try to flush data before it is calculated
        for category in self.filtered(lambda slide: slide.is_category):
            filtered_slides = category.slide_ids.filtered(lambda slide: slide.is_published)
            category.completion_time = sum(filtered_slides.mapped("completion_time"))

    @api.depends('slide_type')
    def _compute_slide_icon_class(self):
        icon_per_slide_type = {
            'image': 'fa-file-picture-o',
            'article': 'fa-file-text-o',
            'quiz': 'fa-question-circle-o',
            'pdf': 'fa-file-pdf-o',
            'sheet': 'fa-file-excel-o',
            'doc': 'fa-file-word-o',
            'slides': 'fa-file-powerpoint-o',
            'youtube_video': 'fa-youtube-play',
            'google_drive_video': 'fa-play-circle-o',
            'vimeo_video': 'fa-vimeo',
        }
        for slide in self:
            slide.slide_icon_class = icon_per_slide_type.get(slide.slide_type, 'fa-file-o')

    @api.depends('slide_category', 'source_type', 'video_source_type')
    def _compute_slide_type(self):
        """ For 'local content' or specific slide categories, the slide type is directly derived
        from the slide category.

        For external content, the slide type is determined from the metadata and the mime_type.
        (See #_fetch_google_drive_metadata() for more details)."""

        for slide in self:
            if slide.slide_category == 'document':
                if slide.source_type == 'local_file':
                    slide.slide_type = 'pdf'
                elif slide.slide_type not in ['pdf', 'sheet', 'doc', 'slides']:
                    slide.slide_type = False
            elif slide.slide_category == 'infographic':
                slide.slide_type = 'image'
            elif slide.slide_category == 'article':
                slide.slide_type = 'article'
            elif slide.slide_category == 'quiz':
                slide.slide_type = 'quiz'
            elif slide.slide_category == 'video' and slide.video_source_type == 'youtube':
                slide.slide_type = 'youtube_video'
            elif slide.slide_category == 'video' and slide.video_source_type == 'google_drive':
                slide.slide_type = 'google_drive_video'
            elif slide.slide_category == 'video' and slide.video_source_type == 'vimeo':
                slide.slide_type = 'vimeo_video'
            else:
                slide.slide_type = False

    @api.depends('slide_partner_ids.partner_id', 'slide_partner_ids.vote', 'slide_partner_ids.completed')
    @api.depends('uid')
    def _compute_user_membership_id(self):
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id),
        ])

        for record in self:
            record.user_membership_id = next(
                (slide_partner for slide_partner in slide_partners if slide_partner.slide_id == record),
                self.env['slide.slide.partner']
            )
            record.user_vote = record.user_membership_id.vote
            record.user_has_completed = record.user_membership_id.completed

    @api.depends('slide_category', 'google_drive_id', 'video_source_type', 'youtube_id')
    def _compute_embed_code(self):
        request_base_url = request.httprequest.url_root if request else False
        for slide in self:
            base_url = request_base_url or slide.get_base_url()
            if base_url[-1] == '/':
                base_url = base_url[:-1]

            embed_code = False
            embed_code_external = False
            if slide.slide_category == 'video':
                if slide.video_source_type == 'youtube':
                    query_params = urls.url_parse(slide.video_url).query
                    query_params = query_params + '&theme=light' if query_params else 'theme=light'
                    embed_code = Markup('<iframe src="//www.youtube-nocookie.com/embed/%s?%s" allowFullScreen="true" frameborder="0" aria-label="%s"></iframe>') % (slide.youtube_id, query_params, _('YouTube'))
                elif slide.video_source_type == 'google_drive':
                    embed_code = Markup('<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0" aria-label="%s"></iframe>') % (slide.google_drive_id, _('Google Drive'))
                elif slide.video_source_type == 'vimeo':
                    if '/' in slide.vimeo_id:
                        # in case of privacy 'with URL only', vimeo adds a token after the video ID
                        # the embed url needs to receive that token as a "h" parameter
                        [vimeo_id, vimeo_token] = slide.vimeo_id.split('/')
                        embed_code = Markup("""
                            <iframe src="https://player.vimeo.com/video/%s?h=%s&badge=0&amp;autopause=0&amp;player_id=0"
                                frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen aria-label="%s"></iframe>""") % (
                                vimeo_id, vimeo_token, _('Vimeo'))
                    else:
                        embed_code = Markup("""
                            <iframe src="https://player.vimeo.com/video/%s?badge=0&amp;autopause=0&amp;player_id=0"
                                frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen aria-label="%s"></iframe>""") % (slide.vimeo_id, _('Vimeo'))
            elif slide.slide_category in ['infographic', 'document'] and slide.source_type == 'external' and slide.google_drive_id:
                embed_code = Markup('<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0" aria-label="%s"></iframe>') % (slide.google_drive_id, _('Google Drive'))
            elif slide.slide_category == 'document' and slide.source_type == 'local_file':
                slide_url = base_url + self.env['ir.http']._url_for('/slides/embed/%s?page=1' % slide.id)
                slide_url_external = base_url + self.env['ir.http']._url_for('/slides/embed_external/%s?page=1' % slide.id)
                base_embed_code = Markup('<iframe src="%s" class="o_wslides_iframe_viewer" allowFullScreen="true" height="%s" width="%s" frameborder="0" aria-label="%s"></iframe>')
                iframe_aria_label = _('Embed code')
                embed_code = base_embed_code % (slide_url, 315, 420, iframe_aria_label)
                embed_code_external = base_embed_code % (slide_url_external, 315, 420, iframe_aria_label)

            slide.embed_code = embed_code
            slide.embed_code_external = embed_code_external or embed_code

    @api.depends('video_url')
    def _compute_video_source_type(self):
        for slide in self:
            video_source_type = False
            youtube_match = re.match(self.YOUTUBE_VIDEO_ID_REGEX, slide.video_url) if slide.video_url else False
            if youtube_match and len(youtube_match.groups()) == 2 and len(youtube_match.group(2)) == 11:
                video_source_type = 'youtube'
            if slide.video_url and not video_source_type and re.match(self.GOOGLE_DRIVE_DOCUMENT_ID_REGEX, slide.video_url):
                video_source_type = 'google_drive'
            vimeo_match = re.search(self.VIMEO_VIDEO_ID_REGEX, slide.video_url) if slide.video_url else False
            if not video_source_type and vimeo_match and len(vimeo_match.groups()) == 3:
                video_source_type = 'vimeo'

            slide.video_source_type = video_source_type

    @api.depends('video_url', 'video_source_type')
    def _compute_youtube_id(self):
        for slide in self:
            if slide.video_url and slide.video_source_type == 'youtube':
                match = re.match(self.YOUTUBE_VIDEO_ID_REGEX, slide.video_url)
                if match and len(match.groups()) == 2 and len(match.group(2)) == 11:
                    slide.youtube_id = match.group(2)
                else:
                    slide.youtube_id = False
            else:
                slide.youtube_id = False

    @api.depends('video_url', 'video_source_type')
    def _compute_vimeo_id(self):
        for slide in self:
            if slide.video_url and slide.video_source_type == 'vimeo':
                match = re.search(self.VIMEO_VIDEO_ID_REGEX, slide.video_url)
                if match and len(match.groups()) == 3:
                    if match.group(3):
                        # in case of privacy 'with URL only', vimeo adds a token after the video ID
                        # the share url is then 'vimeo_id/token'
                        # the token will be captured in the third group of the regex (if any)
                        slide.vimeo_id = '%s/%s' % (match.group(2), match.group(3))
                    else:
                        # regular video, we just capture the vimeo_id
                        slide.vimeo_id = match.group(2)
            else:
                slide.vimeo_id = False

    @api.depends('url', 'document_google_url', 'image_google_url', 'video_url')
    def _compute_google_drive_id(self):
        """ Extracts the Google Drive ID from the url based on the slide category. """

        for slide in self:
            url = slide.url or slide.document_google_url or slide.image_google_url or slide.video_url
            google_drive_id = False
            if url:
                match = re.match(self.GOOGLE_DRIVE_DOCUMENT_ID_REGEX, url)
                if match and len(match.groups()) == 2:
                    google_drive_id = match.group(2)

            slide.google_drive_id = google_drive_id

    @api.onchange('url', 'document_google_url', 'image_google_url', 'video_url')
    def _on_change_url(self):
        """ Keeping a 'onchange' because we want this behavior for the frontend.
        Changing the document / video external URL will populate some metadata on the form view.
        We only populate the field that are empty to avoid overriding user assigned values.
        The slide metadata are also fetched in create / write overrides to ensure consistency. """

        self.ensure_one()
        if self.url or self.document_google_url or self.image_google_url or self.video_url:
            slide_metadata, _error = self._fetch_external_metadata()
            if slide_metadata:
                self.update({
                    key: value
                    for key, value in slide_metadata.items()
                    if not self[key]
                })

    @api.onchange('document_binary_content')
    def _on_change_document_binary_content(self):
        if self.slide_category == 'document' and self.source_type == 'local_file' and self.document_binary_content:
            completion_time = self._get_completion_time_pdf(base64.b64decode(self.document_binary_content))
            if completion_time:
                self.completion_time = completion_time

    @api.onchange('slide_category')
    def _on_change_slide_category(self):
        """ Prevents mis-match when ones uploads an image and then a pdf without saving the form. """
        if self.slide_category != 'infographic' and self.image_binary_content:
            self.image_binary_content = False
        elif self.slide_category != 'document' and self.document_binary_content:
            self.document_binary_content = False

    @api.depends('name', 'channel_id.website_id.domain')
    def _compute_website_url(self):
        super()._compute_website_url()
        for slide in self:
            if slide.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                base_url = slide.channel_id.get_base_url()
                slide.website_url = '%s/slides/slide/%s' % (base_url, self.env['ir.http']._slug(slide))

    @api.depends('is_published')
    def _compute_website_share_url(self):
        self.website_share_url = False
        for slide in self:
            if slide.id:  # ensure we can build the URL
                base_url = slide.channel_id.get_base_url()
                slide.website_share_url = '%s/slides/slide/%s/share' % (base_url, slide.id)

    @api.depends('channel_id.can_publish')
    def _compute_can_publish(self):
        for record in self:
            record.can_publish = record.channel_id.can_publish

    @api.model
    def _get_can_publish_error_message(self):
        return _("Publishing is restricted to the responsible of training courses or members of the publisher group for documentation courses")

    # ---------------------------------------------------------
    # ORM Overrides
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        channel_ids = [vals['channel_id'] for vals in vals_list]
        can_publish_channel_ids = self.env['slide.channel'].browse(channel_ids).filtered(lambda c: c.can_publish).ids
        for vals in vals_list:
            # Do not publish slide if user has not publisher rights
            if vals['channel_id'] not in can_publish_channel_ids:
                # 'website_published' is handled by mixin
                vals['date_published'] = False

            if vals.get('is_category'):
                vals['is_preview'] = True
                vals['is_published'] = True
            if vals.get('is_published') and not vals.get('date_published'):
                vals['date_published'] = datetime.datetime.now()

        slides = super().create(vals_list)

        for slide, vals in zip(slides, vals_list):
            # avoid fetching external metadata when installing the module (i.e. for demo data)
            # we also support a context key if you don't want to fetch the metadata when creating a slide
            if any(vals.get(url_param) for url_param in ['url', 'video_url', 'document_google_url', 'image_google_url']) \
               and not self.env.context.get('install_mode') \
               and not self.env.context.get('website_slides_skip_fetch_metadata'):
                slide_metadata, _error = slide._fetch_external_metadata()
                if slide_metadata:
                    # only update keys that are not set in the incoming vals
                    slide.update({key: value for key, value in slide_metadata.items() if key not in vals.keys()})

            if 'completion_time' not in vals:
                slide._on_change_document_binary_content()

            if slide.is_published and not slide.is_category:
                slide._post_publication()
                slide.channel_id.channel_partner_ids._recompute_completion()
        return slides

    def write(self, values):
        if values.get('is_category'):
            values['is_preview'] = True
            values['is_published'] = True

        # if the slide type is changed, remove incompatible url or html_content
        # done here to satisfy the SQL constraint
        # using a stored-computed field in place does not work
        if 'slide_category' in values:
            if values['slide_category'] == 'article':
                values = {'url': False, **values}
            elif values['slide_category'] != 'article':
                values = {'html_content': False, **values}

        res = super().write(values)

        if values.get('is_published'):
            self.date_published = datetime.datetime.now()
            self._post_publication()

        # avoid fetching external metadata when installing the module (i.e. for demo data)
        # we also support a context key if you don't want to fetch the metadata when modifying a slide
        if any(values.get(url_param) for url_param in ['url', 'video_url', 'document_google_url', 'image_google_url']) \
           and not self.env.context.get('install_mode') \
           and not self.env.context.get('website_slides_skip_fetch_metadata'):
            slide_metadata, _error = self._fetch_external_metadata()
            if slide_metadata:
                # only update keys that are not set in the incoming values and for which we don't have a value yet
                self.update({
                    key: value
                    for key, value in slide_metadata.items()
                    if key not in values.keys() and not any(slide[key] for slide in self)
                })

        if 'is_published' in values or 'active' in values:
            # archiving a channel unpublishes its slides
            self.filtered(lambda slide: not slide.active and not slide.is_category and slide.is_published).is_published = False
            # recompute the completion for all partners of the channel
            self.channel_id.channel_partner_ids._recompute_completion()

        return res

    def copy_data(self, default=None):
        """Sets the sequence to zero so that it always lands at the beginning
        of the newly selected course as an uncategorized slide"""
        default = dict(default or {})
        default['sequence'] = 0
        return super().copy_data(default=default)

    def unlink(self):
        for category in self.filtered(lambda slide: slide.is_category):
            category.channel_id._move_category_slides(category, False)
        channel_partner_ids = self.channel_id.channel_partner_ids
        res = super().unlink()
        channel_partner_ids._recompute_completion()
        return res

    # ---------------------------------------------------------
    # Mail/Rating
    # ---------------------------------------------------------

    def message_post(self, *, message_type='notification', **kwargs):
        self.ensure_one()
        if message_type == 'comment' and not self.channel_id.can_comment:  # user comments have a restriction on karma
            raise AccessError(_('Not enough karma to comment'))
        return super().message_post(message_type=message_type, **kwargs)

    def _get_access_action(self, access_uid=None, force_website=False):
        """ Instead of the classic form view, redirect to website if it is published. """
        self.ensure_one()
        if force_website or self.website_published:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s' % self.website_url,
                'target': 'self',
                'target_type': 'public',
                'res_id': self.id,
            }
        return super()._get_access_action(access_uid=access_uid, force_website=force_website)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()
        if self.website_published:
            for _group_name, _group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def _embed_increment(self, url):
        """ Increment the view count of the record we have based on the passed url.
        If the url is empty, which typically happens if the browser does not pass the 'referer'
        header properly, then we increment the entry that has 'False' as url value. """

        self.ensure_one()

        url_entry = url
        if not urls.url_parse(url).netloc:
            url_entry = False

        embed_entry = self.env['slide.embed'].search([
            ('url', '=', url_entry),
            ('slide_id', '=', self.id)
        ], limit=1)

        if embed_entry:
            embed_entry.count_views += 1
        else:
            embed_entry = self.env['slide.embed'].create({
                'slide_id': self.id,
                'url': url_entry,
            })

        return embed_entry

    def _post_publication(self):
        for slide in self.filtered(lambda slide: slide.website_published and slide.channel_id.publish_template_id):
            publish_template = slide.channel_id.publish_template_id
            html_body = publish_template.with_context(base_url=slide.get_base_url())._render_field('body_html', slide.ids)[slide.id]
            subject = publish_template._render_field('subject', slide.ids)[slide.id]
            # We want to use the 'reply_to' of the template if set. However, `mail.message` will check
            # if the key 'reply_to' is in the kwargs before calling _get_reply_to. If the value is
            # falsy, we don't include it in the 'message_post' call.
            kwargs = {}
            reply_to = publish_template._render_field('reply_to', slide.ids)[slide.id]
            if reply_to:
                kwargs['reply_to'] = reply_to
            slide.channel_id.with_context(mail_create_nosubscribe=True).message_post(
                subject=subject,
                body=html_body,
                subtype_xmlid='website_slides.mt_channel_slide_published',
                email_layout_xmlid='mail.mail_notification_light',
                **kwargs,
            )
        return True

    def _generate_signed_token(self, partner_id):
        """ Lazy generate the acces_token and return it signed by the given partner_id
            :rtype tuple (string, int)
            :return (signed_token, partner_id)
        """
        if not self.access_token:
            self.write({'access_token': self._default_access_token()})
        return self._sign_token(partner_id)

    def _send_share_email(self, email, fullscreen):
        courses_without_templates = self.channel_id.filtered(lambda channel: not channel.share_slide_template_id)
        if courses_without_templates:
            raise UserError(_('Impossible to send emails. Select a "Share Template" for courses %(course_names)s first',
                                 course_names=', '.join(courses_without_templates.mapped('name'))))
        mail_ids = []
        for record in self:
            template = record.channel_id.share_slide_template_id.with_context(
                user=self.env.user,
                email=email,
                base_url=record.get_base_url(),
                fullscreen=fullscreen
            )
            email_values = {'email_to': email}
            if self.env.user._is_portal():
                template = template.sudo()
                email_values['email_from'] = self.env.company.catchall_formatted or self.env.company.email_formatted

            mail_ids.append(template.send_mail(record.id, email_layout_xmlid='mail.mail_notification_light', email_values=email_values))
        return mail_ids

    def action_like(self):
        self.check_access('read')
        return self._action_vote(upvote=True)

    def action_dislike(self):
        self.check_access('read')
        return self._action_vote(upvote=False)

    def _action_vote(self, upvote=True):
        """ Private implementation of voting. It does not check for any real access
        rights; public methods should grant access before calling this method.

          :param upvote: if True, is a like; if False, is a dislike
        """
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        slide_partners = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id)
        ])
        slide_id = slide_partners.mapped('slide_id')
        new_slides = self_sudo - slide_id

        for slide_partner in slide_partners:
            if upvote:
                slide_partner.vote = 0 if slide_partner.vote == 1 else 1
            else:
                slide_partner.vote = 0 if slide_partner.vote == -1 else -1

        for new_slide in new_slides:
            new_vote = 1 if upvote else -1
            new_slide.write({
                'slide_partner_ids': [(0, 0, {'vote': new_vote, 'partner_id': self.env.user.partner_id.id})]
            })

    def action_set_viewed(self, quiz_attempts_inc=False):
        if any(not slide.channel_id.is_member for slide in self):
            raise UserError(_('You cannot mark a slide as viewed if you are not among its members.'))

        return bool(self._action_set_viewed(self.env.user.partner_id, quiz_attempts_inc=quiz_attempts_inc))

    def _action_set_viewed(self, target_partner, quiz_attempts_inc=False):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        if quiz_attempts_inc and existing_sudo:
            sql.increment_fields_skiplock(existing_sudo, 'quiz_attempts_count')
            existing_sudo.invalidate_recordset(['quiz_attempts_count'])

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        return SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'quiz_attempts_count': 1 if quiz_attempts_inc else 0,
            'vote': 0} for new_slide in new_slides])

    def action_mark_completed(self):
        if any(not slide.can_self_mark_completed for slide in self):
            raise UserError(_('You cannot mark a slide as completed if you are not among its members.'))

        return self._action_mark_completed()

    def _action_mark_completed(self):
        uncompleted_slides = self.filtered(lambda slide: not slide.user_has_completed)

        target_partner = self.env.user.partner_id
        uncompleted_slides._action_set_quiz_done()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('slide_id', 'in', uncompleted_slides.ids),
            ('partner_id', '=', target_partner.id)
        ])
        existing_sudo.write({'completed': True})

        new_slides = uncompleted_slides.sudo() - existing_sudo.mapped('slide_id')
        SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'vote': 0,
            'completed': True} for new_slide in new_slides])

    def action_mark_uncompleted(self):
        if any(not slide.can_self_mark_uncompleted for slide in self):
            raise UserError(_('You cannot mark a slide as uncompleted if you are not among its members.'))

        completed_slides = self.filtered(lambda slide: slide.user_has_completed)

        # Remove the Karma point gained
        completed_slides._action_set_quiz_done(completed=False)

        self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', completed_slides.ids),
            ('partner_id', '=', self.env.user.partner_id.id),
        ]).completed = False

    def _action_set_quiz_done(self, completed=True):
        """Add or remove karma point related to the quiz.

        :param completed:
            True if the quiz will be marked as completed (karma will be increased)
            If set to False, we will remove the karma instead of increasing it,
            so that the user can take the quiz multiple times but not gain karma infinitely
        """
        if any(not slide.channel_id.is_member or not slide.website_published for slide in self):
            raise UserError(
                _('You cannot mark a slide quiz as completed if you are not among its members or it is unpublished.') if completed
                else _('You cannot mark a slide quiz as not completed if you are not among its members or it is unpublished.')
            )

        points = 0
        for slide in self:
            user_membership_sudo = slide.user_membership_id.sudo()
            if not user_membership_sudo \
               or user_membership_sudo.completed == completed \
               or not user_membership_sudo.quiz_attempts_count \
               or not slide.question_ids:
                continue

            gains = [slide.quiz_first_attempt_reward,
                     slide.quiz_second_attempt_reward,
                     slide.quiz_third_attempt_reward,
                     slide.quiz_fourth_attempt_reward]
            points = gains[min(user_membership_sudo.quiz_attempts_count, len(gains)) - 1]
            if points:
                if completed:
                    reason = _('Quiz Completed')
                else:
                    points *= -1
                    reason = _('Quiz Set Uncompleted')
                self.env.user.sudo()._add_karma(points, slide, reason)

        return True

    def action_view_embeds(self):
        self.ensure_one()

        action = self.env["ir.actions.actions"]._for_xml_id("website_slides.slide_embed_action")
        action['context'] = {'search_default_slide_id': self.id}
        return action

    def _compute_quiz_info(self, target_partner, quiz_done=False):
        result = dict.fromkeys(self.ids, False)
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        slide_partners_map = dict((sp.slide_id.id, sp) for sp in slide_partners)
        for slide in self:
            if not slide.question_ids:
                gains = [0]
            else:
                gains = [slide.quiz_first_attempt_reward,
                         slide.quiz_second_attempt_reward,
                         slide.quiz_third_attempt_reward,
                         slide.quiz_fourth_attempt_reward]
            result[slide.id] = {
                'quiz_karma_max': gains[0],  # what could be gained if succeed at first try
                'quiz_karma_gain': gains[0],  # what would be gained at next test
                'quiz_karma_won': 0,  # what has been gained
                'quiz_attempts_count': 0,  # number of attempts
            }
            slide_partner = slide_partners_map.get(slide.id)
            if slide.question_ids and slide_partner and slide_partner.quiz_attempts_count:
                result[slide.id]['quiz_karma_gain'] = gains[slide_partner.quiz_attempts_count] if slide_partner.quiz_attempts_count < len(gains) else gains[-1]
                result[slide.id]['quiz_attempts_count'] = slide_partner.quiz_attempts_count
                if quiz_done or slide_partner.completed:
                    result[slide.id]['quiz_karma_won'] = gains[slide_partner.quiz_attempts_count-1] if slide_partner.quiz_attempts_count < len(gains) else gains[-1]
        return result

    # --------------------------------------------------
    # Parsing methods
    # --------------------------------------------------

    def _fetch_external_metadata(self, image_url_only=False):
        self.ensure_one()

        slide_metadata = {}
        error = False
        if self.slide_category == 'video' and self.video_source_type == 'youtube':
            slide_metadata, error = self._fetch_youtube_metadata(image_url_only)
        elif self.slide_category == 'video' and self.video_source_type == 'google_drive':
            slide_metadata, error = self._fetch_google_drive_metadata(image_url_only)
        elif self.slide_category == 'video' and self.video_source_type == 'vimeo':
            slide_metadata, error = self._fetch_vimeo_metadata(image_url_only)
        elif self.slide_category in ['document', 'infographic'] and self.source_type == 'external':
            # external documents & google drive videos share the same method currently
            slide_metadata, error = self._fetch_google_drive_metadata(image_url_only)

        return slide_metadata, error

    def _fetch_youtube_metadata(self, image_url_only=False):
        """ Fetches video metadata from the YouTube API.

        Returns a dict containing video metadata with the following keys (matching slide.slide fields):
        - 'name' matching the video title
        - 'description' matching the video description
        - 'image_1920' binary data of the video thumbnail
          OR 'image_url' containing an external link to the thumbnail when 'image_url_only' param is True
        - 'completion_time' matching the video duration
          The received duration is under a special format (e.g: PT1M21S15, meaning 1h 21m 15s).

        :param image_url_only: if True, will return 'image_url' instead of binary data
          Typically used when displaying a slide preview to the end user.
        :return a tuple (values, error) containing the values of the slide and a potential error
          (e.g: 'Video could not be found') """

        self.ensure_one()
        google_app_key = self.env['website'].get_current_website().sudo().website_slide_google_app_key
        error_message = False
        try:
            response = requests.get(
                'https://www.googleapis.com/youtube/v3/videos',
                timeout=3,
                params={
                    'fields': 'items(id,snippet,contentDetails)',
                    'id': self.youtube_id,
                    'key': google_app_key,
                    'part': 'snippet,contentDetails'
                }
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_message = e.response.content
            if 'application/json' in e.response.headers.get('content-type'):
                json_response = e.response.json()
                if json_response.get('error', {}).get('code') == 404:
                    return {}, _('Your video could not be found on YouTube, please check the link and/or privacy settings')
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)

        if not error_message:
            response = response.json()
            if response.get('error'):
                error_message = response.get('error', {}).get('errors', [{}])[0].get('reason')

            if not response.get('items'):
                error_message = _('Your video could not be found on YouTube, please check the link and/or privacy settings')

        if error_message:
            _logger.warning('Could not fetch YouTube metadata: %s', error_message)
            return {}, error_message

        slide_metadata = {'slide_type': 'youtube_video'}
        youtube_values = response.get('items')[0]
        youtube_duration = youtube_values.get('contentDetails', {}).get('duration')
        if youtube_duration:
            parsed_duration = re.search(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', youtube_duration)
            if parsed_duration:
                slide_metadata['completion_time'] = (int(parsed_duration.group(1) or 0)) + \
                                                    (int(parsed_duration.group(2) or 0) / 60) + \
                                                    (round(int(parsed_duration.group(3) or 0) /60) / 60)

        if youtube_values.get('snippet'):
            snippet = youtube_values['snippet']
            slide_metadata.update({
                'name': snippet['title'],
                'description': snippet['description'],
            })

            thumbnail_url = snippet['thumbnails']['high']['url']
            if image_url_only:
                slide_metadata['image_url'] = thumbnail_url
            else:
                slide_metadata['image_1920'] = base64.b64encode(
                    requests.get(thumbnail_url, timeout=3).content
                )

        return slide_metadata, None

    def _fetch_google_drive_metadata(self, image_url_only=False):
        """ Fetches document / video metadata from the Google Drive API.

        Returns a dict containing metadata with the following keys (matching slide.slide fields):
        - 'name' matching the external file title
        - 'image_1920' binary data of the file thumbnail
          OR 'image_url' containing an external link to the thumbnail when 'image_url_only' param is True
        - 'completion_time' which is computed for 2 types of files:
          - pdf files where we download the content and then use slide.slide#_get_completion_time_pdf()
          - videos where we use the 'videoMediaMetadata' to extract the 'durationMillis'

        :param image_url_only: if True, will return 'image_url' instead of binary data
          Typically used when displaying a slide preview to the end user.
        :return a tuple (values, error) containing the values of the slide and a potential error
          (e.g: 'File could not be found') """

        params = {}
        params['projection'] = 'BASIC'
        if 'google.drive.config' in self.env:
            access_token = False
            try:
                access_token = self.env['google.drive.config'].get_access_token()
            except (RedirectWarning, UserError):
                pass  # ignore and use the 'key' fallback

            if access_token:
                params['access_token'] = access_token

        if not params.get('access_token'):
            params['key'] = self.env['website'].get_current_website().sudo().website_slide_google_app_key

        error_message = False
        try:
            response = requests.get(
                'https://www.googleapis.com/drive/v2/files/%s' % self.google_drive_id,
                timeout=3,
                params=params
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_message = e.response.content
            if 'application/json' in e.response.headers.get('content-type'):
                json_response = e.response.json()
                if json_response.get('error', {}).get('code') == 404:
                    # in case we don't find the file on GDrive, we want to give some feedback to our user
                    return {}, _('Your file could not be found on Google Drive, please check the link and/or privacy settings')
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)

        if not error_message:
            response = response.json()
            if response.get('error'):
                error_message = response.get('error', {}).get('errors', [{}])[0].get('reason')

        if error_message:
            _logger.warning('Could not fetch Google Drive metadata: %s', error_message)
            return {}, error_message

        google_drive_values = response
        slide_metadata = {
            'name': google_drive_values.get('title')
        }

        if google_drive_values.get('thumbnailLink'):
            # small trick, we remove '=s220' to get a higher definition
            thumbnail_url = google_drive_values['thumbnailLink'].replace('=s220', '')
            if image_url_only:
                slide_metadata['image_url'] = thumbnail_url
            else:
                slide_metadata['image_1920'] = base64.b64encode(
                    requests.get(thumbnail_url, timeout=3).content
                )

        if self.slide_category == 'document':
            sheet_mimetypes = [
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.oasis.opendocument.spreadsheet',
                'application/vnd.google-apps.spreadsheet'
            ]

            doc_mimetypes = [
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.oasis.opendocument.text',
                'application/vnd.google-apps.document'
            ]

            slides_mimetypes = [
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.oasis.opendocument.presentation',
                'application/vnd.google-apps.presentation'
            ]

            mime_type = google_drive_values.get('mimeType')
            if mime_type == 'application/pdf':
                slide_metadata['slide_type'] = 'pdf'
                if google_drive_values.get('downloadUrl'):
                    # attempt to download PDF content to extract a completion_time based on the number of pages
                    try:
                        pdf_response = requests.get(google_drive_values.get('downloadUrl'), timeout=5)
                        completion_time = self._get_completion_time_pdf(pdf_response.content)
                        if completion_time:
                            slide_metadata['completion_time'] = completion_time
                    except Exception:
                        pass  # fail silently as this is nice to have
            elif mime_type in sheet_mimetypes:
                slide_metadata['slide_type'] = 'sheet'
            elif mime_type in doc_mimetypes:
                slide_metadata['slide_type'] = 'doc'
            elif mime_type in slides_mimetypes:
                slide_metadata['slide_type'] = 'slides'
            elif mime_type and mime_type.startswith('image/'):
                # image and videos should be input using another "slide_category" but let's be nice and
                # assign them a matching slide_type
                slide_metadata['slide_type'] = 'image'
            elif mime_type and mime_type.startswith('video/'):
                slide_metadata['slide_type'] = 'google_drive_video'

        elif self.slide_category == 'video':
            completion_time = round(float(
                google_drive_values.get('videoMediaMetadata', {}).get('durationMillis', 0)
                ) / (60 * 1000)) / 60  # millis to hours conversion rounded to the minute
            if completion_time:
                slide_metadata['completion_time'] = completion_time

        return slide_metadata, None

    def _fetch_vimeo_metadata(self, image_url_only=False):
        """ Fetches video metadata from the Vimeo API.
        See https://developer.vimeo.com/api/oembed/showcases for more information.

        Returns a dict containing video metadata with the following keys (matching slide.slide fields):
        - 'name' matching the video title
        - 'description' matching the video description
        - 'image_1920' binary data of the video thumbnail
          OR 'image_url' containing an external link to the thumbnail when 'fetch_image' param is False
        - 'completion_time' matching the video duration

        :param image_url_only: if False, will return 'image_url' instead of binary data
          Typically used when displaying a slide preview to the end user.
        :return a tuple (values, error) containing the values of the slide and a potential error
          (e.g: 'Video could not be found') """

        self.ensure_one()
        error_message = False
        try:
            response = requests.get(
                'https://vimeo.com/api/oembed.json?%s' % urls.url_encode({'url': self.video_url}),
                timeout=3
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_message = e.response.content
            if e.response.status_code == 404:
                return {}, _('Your video could not be found on Vimeo, please check the link and/or privacy settings')
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)

        if not error_message and 'application/json' in response.headers.get('content-type'):
            response = response.json()
            if response.get('error'):
                error_message = response.get('error', {}).get('errors', [{}])[0].get('reason')

            if not response:
                error_message = _('Please enter a valid Vimeo video link')

        if error_message:
            _logger.warning('Could not fetch Vimeo metadata: %s', error_message)
            return {}, error_message

        vimeo_values = response
        slide_metadata = {'slide_type': 'vimeo_video'}

        if vimeo_values.get('title'):
            slide_metadata['name'] = vimeo_values.get('title')

        if vimeo_values.get('description'):
            slide_metadata['description'] = vimeo_values.get('description')

        if vimeo_values.get('duration'):
            # seconds to hours conversion
            slide_metadata['completion_time'] = round(vimeo_values.get('duration') / 60) / 60

        thumbnail_url = vimeo_values.get('thumbnail_url')
        if thumbnail_url:
            if image_url_only:
                slide_metadata['image_url'] = thumbnail_url
            else:
                slide_metadata['image_1920'] = base64.b64encode(
                    requests.get(thumbnail_url, timeout=3).content
                )

        return slide_metadata, None

    def _default_website_meta(self):
        res = super()._default_website_meta()
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = html2plaintext(self.description)
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = self.env['website'].image_url(self, 'image_1024')
        res['default_meta_description'] = html2plaintext(self.description)
        return res

    # ---------------------------------------------------------
    # Data / Misc
    # ---------------------------------------------------------

    def _get_completion_time_pdf(self, data_bytes):
        """ For PDFs, we assume that it takes 5 minutes to read a page.
        This method receives the data of the PDF as bytes. """

        if data_bytes.startswith(b'%PDF-'):
            try:
                pdf = PdfFileReader(io.BytesIO(data_bytes), overwriteWarnings=False)
                return (5 * len(pdf.pages)) / 60
            except Exception:
                pass  # as this is a nice to have, fail silently

        return False

    def _get_next_category(self):
        channel_category_ids = self.channel_id.slide_category_ids.ids
        if not channel_category_ids:
            return self.env['slide.slide']
        # If current slide is uncategorized and all the channel uncategorized slides are completed, return the first category
        if not self.category_id and all(self.channel_id.slide_ids.filtered(
            lambda s: not s.is_category and not s.category_id).mapped('user_has_completed')):
            return self.env['slide.slide'].browse(channel_category_ids[0])
        # If current category is completed and current category is not the last one, get next category
        elif self.user_has_completed_category and self.category_id.id in channel_category_ids and self.category_id.id != channel_category_ids[-1]:
            index_current_category = channel_category_ids.index(self.category_id.id)
            return self.env['slide.slide'].browse(channel_category_ids[index_current_category+1])
        return self.env['slide.slide']

    def get_backend_menu_id(self):
        return self.env.ref('website_slides.website_slides_menu_root').id

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        search_fields = ['name']
        fetch_fields = ['id', 'name']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'url', 'type': 'text', 'truncate': False},
            'extra_link': {'name': 'course', 'type': 'text'},
            'extra_link_url': {'name': 'course_url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('description')
            fetch_fields.append('description')
            mapping['description'] = {'name': 'description', 'type': 'text', 'html': True, 'match': True}
        return {
            'model': 'slide.slide',
            'base_domain': [website.website_domain()],
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-shopping-cart',
            'order': 'name desc, id desc' if 'name desc' in order else 'name asc, id desc',
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        icon_per_category = {
            'infographic': 'fa-file-picture-o',
            'article': 'fa-file-text',
            'presentation': 'fa-file-pdf-o',
            'document': 'fa-file-pdf-o',
            'video': 'fa-play-circle',
            'quiz': 'fa-question-circle',
            'link': 'fa-file-code-o', # appears in template "slide_icon"
        }
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for slide, data in zip(self, results_data):
            data['_fa'] = icon_per_category.get(slide.slide_category, 'fa-file-pdf-o')
            data['url'] = slide.website_url
            data['course'] = _('Course: %s', slide.channel_id.name)
            data['course_url'] = slide.channel_id.website_url
        return results_data

    def open_website_url(self):
        """ Overridden to use a relative URL instead of an absolute when website_id is False. """
        if self.website_id:
            return super().open_website_url()
        return self.env['website'].get_client_action(f'/slides/slide/{self.env["ir.http"]._slug(self)}')
