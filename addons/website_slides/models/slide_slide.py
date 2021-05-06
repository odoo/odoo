# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import io
import logging
import re
import requests
import PyPDF2

from dateutil.relativedelta import relativedelta
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug, url_for
from odoo.exceptions import RedirectWarning, UserError, AccessError
from odoo.http import request
from odoo.tools import sql

_logger = logging.getLogger(__name__)


class SlidePartnerRelation(models.Model):
    _name = 'slide.slide.partner'
    _description = 'Slide / Partner decorated m2m'
    _table = 'slide_slide_partner'

    slide_id = fields.Many2one('slide.slide', ondelete="cascade", index=True, required=True)
    channel_id = fields.Many2one(
        'slide.channel', string="Channel",
        related="slide_id.channel_id", store=True, index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', index=True, required=True, ondelete='cascade')
    vote = fields.Integer('Vote', default=0)
    completed = fields.Boolean('Completed')
    quiz_attempts_count = fields.Integer('Quiz attempts count', default=0)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        completed = res.filtered('completed')
        if completed:
            completed._set_completed_callback()
        return res

    def write(self, values):
        res = super(SlidePartnerRelation, self).write(values)
        if values.get('completed'):
            self._set_completed_callback()
        return res

    def _set_completed_callback(self):
        self.env['slide.channel.partner'].search([
            ('channel_id', 'in', self.channel_id.ids),
            ('partner_id', 'in', self.partner_id.ids),
        ])._recompute_completion()


class SlideLink(models.Model):
    _name = 'slide.slide.link'
    _description = "External URL for a particular slide"

    slide_id = fields.Many2one('slide.slide', required=True, ondelete='cascade')
    name = fields.Char('Title', required=True)
    link = fields.Char('Link', required=True)


class SlideResource(models.Model):
    _name = 'slide.slide.resource'
    _description = "Additional resource for a particular slide"

    slide_id = fields.Many2one('slide.slide', required=True, ondelete='cascade')
    name = fields.Char('Name', required=True)
    data = fields.Binary('Resource')


class EmbeddedSlide(models.Model):
    """ Embedding in third party websites. Track view count, generate statistics. """
    _name = 'slide.embed'
    _description = 'Embedded Slides View Counter'
    _rec_name = 'slide_id'

    slide_id = fields.Many2one('slide.slide', string="Presentation", required=True, index=True)
    url = fields.Char('Third Party Website URL', required=True)
    count_views = fields.Integer('# Views', default=1)

    def _add_embed_url(self, slide_id, url):
        baseurl = urls.url_parse(url).netloc
        if not baseurl:
            return 0
        embeds = self.search([('url', '=', baseurl), ('slide_id', '=', int(slide_id))], limit=1)
        if embeds:
            embeds.count_views += 1
        else:
            embeds = self.create({
                'slide_id': slide_id,
                'url': baseurl,
            })
        return embeds.count_views


class SlideTag(models.Model):
    """ Tag to search slides accross channels. """
    _name = 'slide.tag'
    _description = 'Slide Tag'

    name = fields.Char('Name', required=True, translate=True)

    _sql_constraints = [
        ('slide_tag_unique', 'UNIQUE(name)', 'A tag must be unique!'),
    ]


class Slide(models.Model):
    _name = 'slide.slide'
    _inherit = [
        'mail.thread',
        'image.mixin',
        'website.seo.metadata', 'website.published.mixin']
    _description = 'Slides'
    _mail_post_access = 'read'
    _order_by_strategy = {
        'sequence': 'sequence asc, id asc',
        'most_viewed': 'total_views desc',
        'most_voted': 'likes desc',
        'latest': 'date_published desc',
    }
    _order = 'sequence asc, is_category asc, id asc'

    YOUTUBE_VIDEO_ID_REGEX = r'^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*'
    GOOGLE_DRIVE_DOCUMENT_ID_REGEX = r'(^https:\/\/docs.google.com|^https:\/\/drive.google.com).*\/d\/([^\/]*)'
    VIMEO_VIDEO_ID_REGEX = r'\/\/(player.)?vimeo.com\/([a-z]*\/)*([0-9]{6,11})[?]?.*'

    # description
    name = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True, tracking=100)
    sequence = fields.Integer('Sequence', default=0)
    user_id = fields.Many2one('res.users', string='Uploaded by', default=lambda self: self.env.uid)
    description = fields.Text('Description', translate=True)
    channel_id = fields.Many2one('slide.channel', string="Course", required=True)
    tag_ids = fields.Many2many('slide.tag', 'rel_slide_tag', 'slide_id', 'tag_id', string='Tags')
    is_preview = fields.Boolean('Allow Preview', default=False, help="The course is accessible by anyone : the users don't need to join the channel to access the content of the course.")
    is_new_slide = fields.Boolean('Is New Slide', compute='_compute_is_new_slide')
    completion_time = fields.Float('Duration', digits=(10, 4), help="The estimated completion time for this slide")
    # Categories
    is_category = fields.Boolean('Is a category', default=False)
    category_id = fields.Many2one('slide.slide', string="Section", compute="_compute_category_id", store=True)
    slide_ids = fields.One2many('slide.slide', "category_id", string="Slides")
    # subscribers
    partner_ids = fields.Many2many('res.partner', 'slide_slide_partner', 'slide_id', 'partner_id',
                                   string='Subscribers', groups='website_slides.group_website_slides_officer', copy=False)
    slide_partner_ids = fields.One2many('slide.slide.partner', 'slide_id', string='Subscribers information', groups='website_slides.group_website_slides_officer', copy=False)
    user_membership_id = fields.Many2one(
        'slide.slide.partner', string="Subscriber information", compute='_compute_user_membership_id', compute_sudo=False,
        help="Subscriber information for the current logged in user")
    # Quiz related fields
    question_ids = fields.One2many("slide.question", "slide_id", string="Questions")
    questions_count = fields.Integer(string="Numbers of Questions", compute='_compute_questions_count')
    quiz_first_attempt_reward = fields.Integer("Reward: first attempt", default=10)
    quiz_second_attempt_reward = fields.Integer("Reward: second attempt", default=7)
    quiz_third_attempt_reward = fields.Integer("Reward: third attempt", default=5,)
    quiz_fourth_attempt_reward = fields.Integer("Reward: every attempt after the third try", default=2)
    # content
    slide_type = fields.Selection([
        ('infographic', 'Infographic'),
        ('webpage', 'Web Page'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('quiz', "Quiz")],
        string='Type', required=True,
        default='document')
    source_type = fields.Selection([
        ('local_file', 'Local File'),
        ('external', 'External (Google Drive)')],
        default='local_file', required=True)
    datas = fields.Binary('Content', attachment=True)
    link_ids = fields.One2many('slide.slide.link', 'slide_id', string="External URL for this slide")
    slide_resource_ids = fields.One2many('slide.slide.resource', 'slide_id', string="Additional Resource for this slide")
    slide_resource_downloadable = fields.Boolean('Allow Download', default=True, help="Allow the user to download the content of the slide.")
    html_content = fields.Html("HTML Content", help="Custom HTML content for slides of type 'Web Page'.", translate=True, sanitize_form=False)
    # content - images
    image_data = fields.Binary('Image Content', related='datas', readonly=False,
        help="Used to filter file input to images only")
    # content - documents
    document_type = fields.Selection([
        ('pdf', 'PDF'),
        ('sheet', 'Sheet (Excel, Google Sheet, ...)'),
        ('doc', 'Document (Word, Google Doc, ...)'),
        ('slides', 'Slides (PowerPoint, Google Slides, ...)'),
        ('image', 'Image'),
        ('video', 'Video')],
        string="Document Type",
        help="Subtype of slides of type document, mostly used for external content and determined based on the mime_type.")
    document_url = fields.Char('Document URL', help="URL of the document (we currently only support Google Drive as source)")
    document_google_drive_id = fields.Char('Document Google Drive ID', compute='_compute_google_drive_id')
    document_data_pdf = fields.Binary('PDF Content', related='datas', readonly=False,
        help="Used to filter file input to PDF only")
    # content - videos
    video_url = fields.Char('Video URL', help="URL of the video (we support YouTube, Google Drive and Vimeo as sources)")
    video_source_type = fields.Selection([
        ('youtube', 'YouTube'),
        ('google_drive', 'Google Drive'),
        ('vimeo', 'Vimeo')],
        string='Video Source', compute="_compute_video_source_type")
    video_youtube_id = fields.Char('Video YouTube ID', compute='_compute_video_youtube_id')
    video_google_drive_id = fields.Char('Video Google Drive ID', compute='_compute_google_drive_id')
    video_vimeo_id = fields.Char('Video Vimeo ID', compute='_compute_video_vimeo_id')
    # website
    website_id = fields.Many2one(related='channel_id.website_id', readonly=True)
    date_published = fields.Datetime('Publish Date', readonly=True, tracking=1)
    likes = fields.Integer('Likes', compute='_compute_user_info', store=True, compute_sudo=False)
    dislikes = fields.Integer('Dislikes', compute='_compute_user_info', store=True, compute_sudo=False)
    user_vote = fields.Integer('User vote', compute='_compute_user_info', compute_sudo=False)
    embed_code = fields.Html('Embed Code', readonly=True, compute='_compute_embed_code', sanitize=False)
    # views
    embedcount_ids = fields.One2many('slide.embed', 'slide_id', string="Embed Count")
    slide_views = fields.Integer('# of Website Views', store=True, compute="_compute_slide_views")
    public_views = fields.Integer('# of Public Views', copy=False)
    total_views = fields.Integer("Views", default="0", compute='_compute_total', store=True)
    # comments
    comments_count = fields.Integer('Number of comments', compute="_compute_comments_count")
    # channel
    channel_type = fields.Selection(related="channel_id.channel_type", string="Channel type")
    channel_allow_comment = fields.Boolean(related="channel_id.allow_comment", string="Allows comment")
    # Statistics in case the slide is a category
    nbr_document = fields.Integer("Number of Documents", compute='_compute_slides_statistics', store=True)
    nbr_video = fields.Integer("Number of Videos", compute='_compute_slides_statistics', store=True)
    nbr_infographic = fields.Integer("Number of Infographics", compute='_compute_slides_statistics', store=True)
    nbr_webpage = fields.Integer("Number of Webpages", compute='_compute_slides_statistics', store=True)
    nbr_quiz = fields.Integer("Number of Quizs", compute="_compute_slides_statistics", store=True)
    total_slides = fields.Integer(compute='_compute_slides_statistics', store=True)

    _sql_constraints = [
        ('exclusion_html_content_and_document_url', "CHECK(html_content IS NULL OR document_url IS NULL)", "A slide is either filled with a document url or HTML content. Not both.")
    ]

    @api.depends('date_published', 'is_published')
    def _compute_is_new_slide(self):
        for slide in self:
            slide.is_new_slide = slide.date_published > fields.Datetime.now() - relativedelta(days=7) if slide.is_published else False

    @api.depends('channel_id.slide_ids.is_category', 'channel_id.slide_ids.sequence')
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

        for cid, slides in channel_slides.items():
            current_category = self.env['slide.slide']
            slide_list = list(slides)
            slide_list.sort(key=lambda s: (s.sequence, not s.is_category))
            for slide in slide_list:
                if slide.is_category:
                    current_category = slide
                elif slide.category_id != current_category:
                    slide.category_id = current_category.id

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
    @api.depends_context('uid')
    def _compute_user_info(self):
        default_stats = {'likes': 0, 'dislikes': 0, 'user_vote': False}

        if not self.ids:
            self.update(default_stats)
            return

        slide_data = dict.fromkeys(self.ids, default_stats)
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', self.ids)
        ])
        for slide_partner in slide_partners:
            if slide_partner.vote == 1:
                slide_data[slide_partner.slide_id.id]['likes'] += 1
                if slide_partner.partner_id == self.env.user.partner_id:
                    slide_data[slide_partner.slide_id.id]['user_vote'] = 1
            elif slide_partner.vote == -1:
                slide_data[slide_partner.slide_id.id]['dislikes'] += 1
                if slide_partner.partner_id == self.env.user.partner_id:
                    slide_data[slide_partner.slide_id.id]['user_vote'] = -1
        for slide in self:
            slide.update(slide_data[slide.id])

    @api.depends('slide_partner_ids.slide_id')
    def _compute_slide_views(self):
        # TODO awa: tried compute_sudo, for some reason it doesn't work in here...
        read_group_res = self.env['slide.slide.partner'].sudo().read_group(
            [('slide_id', 'in', self.ids)],
            ['slide_id'],
            groupby=['slide_id']
        )
        mapped_data = dict((res['slide_id'][0], res['slide_id_count']) for res in read_group_res)
        for slide in self:
            slide.slide_views = mapped_data.get(slide.id, 0)

    @api.depends('slide_ids.sequence', 'slide_ids.slide_type', 'slide_ids.is_published', 'slide_ids.is_category')
    def _compute_slides_statistics(self):
        # Do not use dict.fromkeys(self.ids, dict()) otherwise it will use the same dictionnary for all keys.
        # Therefore, when updating the dict of one key, it updates the dict of all keys.
        keys = ['nbr_%s' % slide_type for slide_type in self.env['slide.slide']._fields['slide_type'].get_values(self.env)]
        default_vals = dict((key, 0) for key in keys + ['total_slides'])

        res = self.env['slide.slide'].read_group(
            [('is_published', '=', True), ('category_id', 'in', self.ids), ('is_category', '=', False)],
            ['category_id', 'slide_type'], ['category_id', 'slide_type'],
            lazy=False)

        type_stats = self._compute_slides_statistics_type(res)

        for record in self:
            record.update(type_stats.get(record._origin.id, default_vals))

    def _compute_slides_statistics_type(self, read_group_res):
        """ Compute statistics based on all existing slide types """
        slide_types = self.env['slide.slide']._fields['slide_type'].get_values(self.env)
        keys = ['nbr_%s' % slide_type for slide_type in slide_types]
        result = dict((cid, dict((key, 0) for key in keys + ['total_slides'])) for cid in self.ids)
        for res_group in read_group_res:
            cid = res_group['category_id'][0]
            slide_type = res_group.get('slide_type')
            if slide_type:
                slide_type_count = res_group.get('__count', 0)
                result[cid]['nbr_%s' % slide_type] = slide_type_count
                result[cid]['total_slides'] += slide_type_count
        return result

    @api.depends('slide_partner_ids.partner_id')
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

    @api.depends('slide_type', 'document_google_drive_id', 'video_source_type', 'video_youtube_id', 'video_google_drive_id')
    def _compute_embed_code(self):
        base_url = request and request.httprequest.url_root or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if base_url[-1] == '/':
            base_url = base_url[:-1]

        for slide in self:
            embed_code = False
            if slide.slide_type == 'video':
                if slide.video_source_type == 'youtube':
                    query_params = urls.url_parse(slide.video_url).query
                    query_params = query_params + '&theme=light' if query_params else 'theme=light'
                    embed_code = '<iframe src="//www.youtube-nocookie.com/embed/%s?%s" allowFullScreen="true" frameborder="0"></iframe>' % (slide.video_youtube_id, query_params)
                elif slide.video_source_type == 'google_drive':
                    embed_code = '<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0"></iframe>' % (slide.video_google_drive_id)
                elif slide.video_source_type == 'vimeo':
                    embed_code = """
                        <iframe src="https://player.vimeo.com/video/%s?badge=0&amp;autopause=0&amp;player_id=0"
                            frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen
                            title="sample video several minutes.mp4"></iframe>""" % (slide.video_vimeo_id)
            elif slide.slide_type in ['infographic', 'document'] and slide.source_type == 'external' and slide.document_google_drive_id:
                embed_code = '<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0"></iframe>' % (slide.document_google_drive_id)
            elif slide.slide_type == 'document' and slide.source_type == 'local_file':
                slide_url = base_url + url_for('/slides/embed/%s?page=1' % slide.id)
                embed_code = '<iframe src="%s" class="o_wslides_iframe_viewer" allowFullScreen="true" height="%s" width="%s" frameborder="0"></iframe>' % (slide_url, 315, 420)

            slide.embed_code = embed_code

    @api.depends('video_url')
    def _compute_video_source_type(self):
        for slide in self:
            video_source_type = False
            youtube_match = re.match(self.YOUTUBE_VIDEO_ID_REGEX, slide.video_url) if slide.video_url else False
            if youtube_match:
                if youtube_match and len(youtube_match.groups()) == 2 and len(youtube_match.group(2)) == 11:
                    video_source_type = 'youtube'
            if slide.video_url and not video_source_type and re.match(self.GOOGLE_DRIVE_DOCUMENT_ID_REGEX, slide.video_url):
                video_source_type = 'google_drive'
            vimeo_match = re.search(self.VIMEO_VIDEO_ID_REGEX, slide.video_url) if slide.video_url else False
            if not video_source_type and vimeo_match and len(vimeo_match.groups()) == 3:
                video_source_type = 'vimeo'

            slide.video_source_type = video_source_type

    @api.depends('video_url', 'video_source_type')
    def _compute_video_youtube_id(self):
        for slide in self:
            if slide.video_url and slide.video_source_type == 'youtube':
                match = re.match(self.YOUTUBE_VIDEO_ID_REGEX, slide.video_url)
                if match and len(match.groups()) == 2 and len(match.group(2)) == 11:
                    slide.video_youtube_id = match.group(2)
                else:
                    slide.video_youtube_id = False
            else:
                slide.video_youtube_id = False

    @api.depends('video_url', 'video_source_type')
    def _compute_video_vimeo_id(self):
        for slide in self:
            if slide.video_url and slide.video_source_type == 'vimeo':
                match = re.search(self.VIMEO_VIDEO_ID_REGEX, slide.video_url)
                if match and len(match.groups()) == 3:
                    slide.video_vimeo_id = match.group(3)
            else:
                slide.video_vimeo_id = False

    @api.depends('slide_type', 'document_url', 'video_url', 'video_source_type')
    def _compute_google_drive_id(self):
        """ Extracts the Google Drive ID from either the video_url or the document_url based on
        the slide type.
        The method is the same so we compute both fields in a single method. """

        for slide in self:
            google_drive_url = False
            if slide.slide_type == 'video' and slide.video_url and slide.video_source_type == 'google_drive':
                google_drive_url = slide.video_url
            elif slide.slide_type in ['document', 'infographic'] and slide.document_url:
                google_drive_url = slide.document_url

            google_drive_id = False
            if google_drive_url:
                match = re.match(self.GOOGLE_DRIVE_DOCUMENT_ID_REGEX, google_drive_url)
                if match and len(match.groups()) == 2:
                    google_drive_id = match.group(2)

            if google_drive_id and slide.slide_type == 'video':
                slide.document_google_drive_id = False
                slide.video_google_drive_id = google_drive_id
            elif google_drive_id and slide.slide_type in ['document', 'infographic']:
                slide.document_google_drive_id = google_drive_id
                slide.video_google_drive_id = False
            else:
                slide.document_google_drive_id = False
                slide.video_google_drive_id = False

    @api.onchange('document_url', 'video_url')
    def _on_change_url(self):
        """ Keeping a 'onchange' because we want this behavior for the frontend.
        Changing the document / video external URL will populate some metadata on the form view.
        The slide metadata are also fetched in create / write overrides to ensure consistency. """

        self.ensure_one()
        if self.document_url or self.video_url:
            slide_metadata = self._fetch_external_metadata()
            if slide_metadata:
                self.update(slide_metadata)

    @api.onchange('document_data_pdf')
    def _on_change_document_data_pdf(self):
        if self.slide_type == 'document' and self.source_type == 'local_file' and self.document_data_pdf:
            completion_time = self._get_completion_time_pdf(base64.b64decode(self.document_data_pdf))
            if completion_time:
                self.completion_time = completion_time

    @api.onchange('image_data')
    def _on_change_image_data(self):
        if self.slide_type == 'infographic' and self.source_type == 'local_file' and self.image_data:
            self.image_1920 = self.image_data

    @api.depends('name', 'channel_id.website_id.domain')
    def _compute_website_url(self):
        # TDE FIXME: clena this link.tracker strange stuff
        super(Slide, self)._compute_website_url()
        for slide in self:
            if slide.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                base_url = slide.channel_id.get_base_url()
                # link_tracker is not in dependencies, so use it to shorten url only if installed.
                if self.env.registry.get('link.tracker'):
                    url = self.env['link.tracker'].sudo().create({
                        'url': '%s/slides/slide/%s' % (base_url, slug(slide)),
                        'title': slide.name,
                    }).short_url
                else:
                    url = '%s/slides/slide/%s' % (base_url, slug(slide))
                slide.website_url = url

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

    @api.model
    def create(self, values):
        # Do not publish slide if user has not publisher rights
        channel = self.env['slide.channel'].browse(values['channel_id'])
        if not channel.can_publish:
            # 'website_published' is handled by mixin
            values['date_published'] = False

        if values.get('slide_type') == 'infographic' and not values.get('image_1920') and values.get('image_data'):
            values['image_1920'] = values['image_data']
        if values.get('is_category'):
            values['is_preview'] = True
            values['is_published'] = True
        if values.get('is_published') and not values.get('date_published'):
            values['date_published'] = datetime.datetime.now()
        if values.get('url') and not values.get('document_id'):
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.items():
                values.setdefault(key, value)

        slide = super(Slide, self).create(values)

        # avoid fetching external metadata when installing the module (i.e. for demo data)
        # we also support a context key if you don't want to fetch the metadata when creating a slide
        if (values.get('document_url') or values.get('video_url')) \
           and not self.env.context.get('install_mode', False) \
           and self.env.context.get('website_slides_fetch_metadata', True):
            slide_metadata = slide._fetch_external_metadata()
            if slide_metadata:
                # only update keys that are not set in the incoming values
                slide.update({key: value for key, value in slide_metadata.items() if key not in values})

        if slide.is_published and not slide.is_category:
            slide._post_publication()
        return slide

    def write(self, values):
        if values.get('url') and values['url'] != self.url:
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.items():
                values.setdefault(key, value)
        if values.get('is_category'):
            values['is_preview'] = True
            values['is_published'] = True

        res = super(Slide, self).write(values)
        if values.get('is_published'):
            self.date_published = datetime.datetime.now()
            self._post_publication()

        # avoid fetching external metadata when installing the module (i.e. for demo data)
        # we also support a context key if you don't want to fetch the metadata when modifying a slide
        if (values.get('document_url') or values.get('video_url')) \
           and not self.env.context.get('install_mode', False) \
           and self.env.context.get('website_slides_fetch_metadata', True):
            slide_metadata = self._fetch_external_metadata()
            if slide_metadata:
                # only update keys that are not set in the incoming values
                self.update({key: value for key, value in slide_metadata.items() if key not in values})

        if 'is_published' in values or 'active' in values:
            # if the slide is published/unpublished, recompute the completion for the partners
            self.slide_partner_ids._set_completed_callback()

        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """Sets the sequence to zero so that it always lands at the beginning
        of the newly selected course as an uncategorized slide"""
        rec = super(Slide, self).copy(default)
        rec.sequence = 0
        return rec

    @api.ondelete(at_uninstall=False)
    def _unlink_except_already_taken(self):
        if self.question_ids and self.channel_id.channel_partner_ids:
            raise UserError(_("People already took this quiz. To keep course progression it should not be deleted."))

    def unlink(self):
        for category in self.filtered(lambda slide: slide.is_category):
            category.channel_id._move_category_slides(category, False)
        super(Slide, self).unlink()

    def toggle_active(self):
        # archiving/unarchiving a channel does it on its slides, too
        to_archive = self.filtered(lambda slide: slide.active)
        res = super(Slide, self).toggle_active()
        if to_archive:
            to_archive.filtered(lambda slide: not slide.is_category).is_published = False
        return res

    # ---------------------------------------------------------
    # Mail/Rating
    # ---------------------------------------------------------

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        self.ensure_one()
        if message_type == 'comment' and not self.channel_id.can_comment:  # user comments have a restriction on karma
            raise AccessError(_('Not enough karma to comment'))
        return super(Slide, self).message_post(message_type=message_type, **kwargs)

    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to website if it is published. """
        self.ensure_one()
        if self.website_published:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s' % self.website_url,
                'target': 'self',
                'target_type': 'public',
                'res_id': self.id,
            }
        return super(Slide, self).get_access_action(access_uid)

    def _notify_get_groups(self, msg_vals=None):
        """ Add access button to everyone if the document is active. """
        groups = super(Slide, self)._notify_get_groups(msg_vals=msg_vals)

        if self.website_published:
            for group_name, group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def _post_publication(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for slide in self.filtered(lambda slide: slide.website_published and slide.channel_id.publish_template_id):
            publish_template = slide.channel_id.publish_template_id
            html_body = publish_template.with_context(base_url=base_url)._render_field('body_html', slide.ids)[slide.id]
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
        # TDE FIXME: template to check
        mail_ids = []
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            template = record.channel_id.share_template_id.with_context(
                user=self.env.user,
                email=email,
                base_url=base_url,
                fullscreen=fullscreen
            )
            email_values = {'email_to': email}
            if self.env.user.has_group('base.group_portal'):
                template = template.sudo()
                email_values['email_from'] = self.env.company.catchall_formatted or self.env.company.email_formatted

            mail_ids.append(template.send_mail(record.id, notif_layout='mail.mail_notification_light', email_values=email_values))
        return mail_ids

    def action_like(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        return self._action_vote(upvote=True)

    def action_dislike(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
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
        channel = slide_id.channel_id
        karma_to_add = 0

        for slide_partner in slide_partners:
            if upvote:
                new_vote = 0 if slide_partner.vote == -1 else 1
                if slide_partner.vote != 1:
                    karma_to_add += channel.karma_gen_slide_vote
            else:
                new_vote = 0 if slide_partner.vote == 1 else -1
                if slide_partner.vote != -1:
                    karma_to_add -= channel.karma_gen_slide_vote
            slide_partner.vote = new_vote

        for new_slide in new_slides:
            new_vote = 1 if upvote else -1
            new_slide.write({
                'slide_partner_ids': [(0, 0, {'vote': new_vote, 'partner_id': self.env.user.partner_id.id})]
            })
            karma_to_add += new_slide.channel_id.karma_gen_slide_vote * (1 if upvote else -1)

        if karma_to_add:
            self.env.user.add_karma(karma_to_add)

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
            sql.increment_field_skiplock(existing_sudo, 'quiz_attempts_count')
            SlidePartnerSudo.invalidate_cache(fnames=['quiz_attempts_count'], ids=existing_sudo.ids)

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        return SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'quiz_attempts_count': 1 if quiz_attempts_inc else 0,
            'vote': 0} for new_slide in new_slides])

    def action_set_completed(self):
        if any(not slide.channel_id.is_member for slide in self):
            raise UserError(_('You cannot mark a slide as completed if you are not among its members.'))

        return self._action_set_completed(self.env.user.partner_id)

    def _action_set_completed(self, target_partner):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        existing_sudo.write({'completed': True})

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'vote': 0,
            'completed': True} for new_slide in new_slides])

        return True

    def _action_set_quiz_done(self):
        if any(not slide.channel_id.is_member for slide in self):
            raise UserError(_('You cannot mark a slide quiz as completed if you are not among its members.'))

        points = 0
        for slide in self:
            user_membership_sudo = slide.user_membership_id.sudo()
            if not user_membership_sudo or user_membership_sudo.completed or not user_membership_sudo.quiz_attempts_count:
                continue

            gains = [slide.quiz_first_attempt_reward,
                     slide.quiz_second_attempt_reward,
                     slide.quiz_third_attempt_reward,
                     slide.quiz_fourth_attempt_reward]
            points += gains[user_membership_sudo.quiz_attempts_count - 1] if user_membership_sudo.quiz_attempts_count <= len(gains) else gains[-1]

        return self.env.user.sudo().add_karma(points)

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

    def _fetch_external_metadata(self, fetch_image=True):
        self.ensure_one()

        slide_metadata = {}
        if self.slide_type == 'video' and self.video_source_type == 'youtube':
            slide_metadata = self._fetch_youtube_metadata(fetch_image)
        elif self.slide_type == 'video' and self.video_source_type == 'google_drive':
            slide_metadata = self._fetch_google_drive_metadata(fetch_image)
        elif self.slide_type == 'video' and self.video_source_type == 'vimeo':
            slide_metadata = self._fetch_vimeo_metadata(fetch_image)
        elif self.slide_type in ['document', 'infographic'] and self.source_type == 'external':
            # external documents & google drive videos share the same method currently
            slide_metadata = self._fetch_google_drive_metadata(fetch_image)

        return slide_metadata

    def _fetch_youtube_metadata(self, fetch_image=True, raise_if_error=False):
        """ Fetches video metadata from the YouTube API.

        Returns a dict containing video metadata with the following keys (matching slide.slide fields):
        - 'name' matching the video title
        - 'description' matching the video description
        - 'image_1920' binary data of the video thumbnail
          OR 'image_url' containing an external link to the thumbnail when 'fetch_image' param is False
        - 'completion_time' matching the video duration
          The received duration is under a special format (e.g: PT1M21S15, meaning 1h 21m 15s).

        :param fetch_image: if False, will return 'image_url' instead of binary data
          Typically used when displaying a slide preview to the end user.
        :param raise_if_error: is True, will raise a UserError in case metadata cannot be retrieved """

        self.ensure_one()
        key = self.env['website'].get_current_website().website_slide_google_app_key
        error_message = False
        try:
            response = requests.get(
                'https://www.googleapis.com/youtube/v3/videos',
                timeout=3,
                params={
                    'id': self.video_youtube_id,
                    'key': key,
                    'part': 'snippet,contentDetails',
                    'fields': 'items(id,snippet,contentDetails)'
                }
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_message = e.response.content
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)

        if not error_message:
            response = response.json()
            if response.get('error'):
                error_message = response.get('error', {}).get('errors', [{}])[0].get('reason')

            if not response.get('items'):
                error_message = _('Please enter a valid YouTube video URL')

        if error_message:
            if raise_if_error:
                raise UserError(_('Could not fetch YouTube metadata: %s', error_message))
            else:
                _logger.warning('Could not fetch YouTube metadata: %s', error_message)
                return {}

        slide_metadata = {}
        youtube_values = response.get('items')[0]
        youtube_duration = youtube_values.get('contentDetails', {}).get('duration')
        if youtube_duration:
            parsed_duration = re.search(r'^PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$', youtube_duration)
            slide_metadata['completion_time'] = (int(parsed_duration.group(1) or 0)) + \
                                        (int(parsed_duration.group(2) or 0) / 60) + \
                                        (int(parsed_duration.group(3) or 0) / 3600)

        if youtube_values.get('snippet'):
            snippet = youtube_values['snippet']
            slide_metadata.update({
                'name': snippet['title'],
                'description': snippet['description'],
            })

            thumbnail_url = snippet['thumbnails']['high']['url']
            if fetch_image:
                slide_metadata['image_1920'] = base64.b64encode(
                    requests.get(thumbnail_url, timeout=3).content
                )
            else:
                slide_metadata['image_url'] = thumbnail_url

        return slide_metadata

    def _fetch_google_drive_metadata(self, fetch_image, raise_if_error=False):
        """ Fetches document / video metadata from the Google Drive API.

        Returns a dict containing metadata with the following keys (matching slide.slide fields):
        - 'name' matching the external file title
        - 'image_1920' binary data of the file thumbnail
          OR 'image_url' containing an external link to the thumbnail when 'fetch_image' param is False
        - 'completion_time' which is computed for 2 types of files:
          - pdf files where we download the content and then use slide.slide#_get_completion_time_pdf()
          - videos where we use the 'videoMediaMetadata' to extract the 'durationMillis'

        :param fetch_image: if False, will return 'image_url' instead of binary data
          Typically used when displaying a slide preview to the end user.
        :param raise_if_error: is True, will raise a UserError in case metadata cannot be retrieved """

        params = {}
        params['projection'] = 'BASIC'
        if 'google.drive.config' in self.env:
            access_token = False
            try:
                access_token = self.env['google.drive.config'].get_access_token()
            except RedirectWarning as e:
                pass  # ignore and use the 'key' fallback
            except UserError as e:
                pass  # ignore and use the 'key' fallback

            if access_token:
                params['access_token'] = access_token

        if not params.get('access_token'):
            params['key'] = self.env['website'].get_current_website().website_slide_google_app_key

        google_drive_id = self.document_google_drive_id or self.video_google_drive_id
        error_message = False
        try:
            response = requests.get(
                'https://www.googleapis.com/drive/v2/files/%s' % google_drive_id,
                timeout=3,
                params=params
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_message = e.response.content
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)

        if not error_message:
            response = response.json()
            if response.get('error'):
                error_message = response.get('error', {}).get('errors', [{}])[0].get('reason')

        if error_message:
            if raise_if_error:
                raise UserError(_('Could not fetch Google Drive metadata: %s', error_message))
            else:
                _logger.warning('Could not fetch Google Drive metadata: %s', error_message)
                return {}

        google_drive_values = response
        slide_metadata = {
            'name': google_drive_values.get('title')
        }

        if google_drive_values.get('thumbnailLink'):
            # small trick, we remove '=s220' to get a higher definition
            thumbnail_url = google_drive_values['thumbnailLink'].replace('=s220', '')
            if fetch_image:
                slide_metadata['image_1920'] = base64.b64encode(
                    requests.get(thumbnail_url, timeout=3).content
                )
            else:
                slide_metadata['image_url'] = thumbnail_url

        if self.slide_type == 'document':
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
                slide_metadata['document_type'] = 'pdf'
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
                slide_metadata['document_type'] = 'sheet'
            elif mime_type in doc_mimetypes:
                slide_metadata['document_type'] = 'doc'
            elif mime_type in slides_mimetypes:
                slide_metadata['document_type'] = 'slides'
            elif mime_type and mime_type.startswith('image/'):
                # image and videos should be input using another "slide_type" but let's be nice and
                # assign them a matching document_type
                slide_metadata['document_type'] = 'image'
            elif mime_type and mime_type.startswith('video/'):
                slide_metadata['document_type'] = 'video'

        elif self.slide_type == 'video':
            completion_time = float(
                google_drive_values.get('videoMediaMetadata', {}).get('durationMillis', 0)
                ) / (60 * 60 * 1000)  # millis to hours conversion
            if completion_time:
                slide_metadata['completion_time'] = completion_time

        return slide_metadata

    def _fetch_vimeo_metadata(self, fetch_image=True, raise_if_error=False):
        """ Fetches video metadata from the Vimeo API.
        See https://developer.vimeo.com/api/oembed/showcases for more information.

        Returns a dict containing video metadata with the following keys (matching slide.slide fields):
        - 'name' matching the video title
        - 'description' matching the video description
        - 'image_1920' binary data of the video thumbnail
          OR 'image_url' containing an external link to the thumbnail when 'fetch_image' param is False
        - 'completion_time' matching the video duration

        :param fetch_image: if False, will return 'image_url' instead of binary data
          Typically used when displaying a slide preview to the end user.
        :param raise_if_error: is True, will raise a UserError in case metadata cannot be retrieved """

        self.ensure_one()
        error_message = False
        try:
            response = requests.get(
                f'https://vimeo.com/api/oembed.json?url=http%3A//vimeo.com/{self.video_vimeo_id}',
                timeout=3
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            error_message = e.response.content
        except requests.exceptions.ConnectionError as e:
            error_message = str(e)

        if not error_message:
            response = response.json()
            if response.get('error'):
                error_message = response.get('error', {}).get('errors', [{}])[0].get('reason')

            if not response:
                error_message = _('Please enter a valid Vimeo video URL')

        if error_message:
            if raise_if_error:
                raise UserError(_('Could not fetch Vimeo metadata: %s', error_message))
            else:
                _logger.warning('Could not fetch Vimeo metadata: %s', error_message)
                return {}

        vimeo_values = response
        slide_metadata = {}

        if vimeo_values.get('title'):
            slide_metadata['name'] = vimeo_values.get('title')

        if vimeo_values.get('description'):
            slide_metadata['description'] = vimeo_values.get('description')

        if vimeo_values.get('duration'):
            # seconds to hours conversion
            slide_metadata['completion_time'] = vimeo_values.get('duration') / (60 * 60)

        thumbnail_url = vimeo_values.get('thumbnail_url')
        if thumbnail_url:
            if fetch_image:
                slide_metadata['image_1920'] = base64.b64encode(
                    requests.get(thumbnail_url, timeout=3).content
                )
            else:
                slide_metadata['image_url'] = thumbnail_url

        return slide_metadata

    def _default_website_meta(self):
        res = super(Slide, self)._default_website_meta()
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.description
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = self.env['website'].image_url(self, 'image_1024')
        res['default_meta_description'] = self.description
        return res

    # ---------------------------------------------------------
    # Data / Misc
    # ---------------------------------------------------------

    def get_backend_menu_id(self):
        return self.env.ref('website_slides.website_slides_menu_root').id

    @api.model
    def _get_completion_time_pdf(self, data):
        """ For PDFs, we assume that it takes 5 minutes to read a page. """
        if data.startswith(b'%PDF-'):
            try:
                pdf = PyPDF2.PdfFileReader(io.BytesIO(data), overwriteWarnings=False)
                return (5 * len(pdf.pages)) / 60
            except Exception:
                pass  # as this is a nice to have, fail silently

        return False
