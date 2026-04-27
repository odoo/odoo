# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


class SocialPostYoutube(models.Model):
    _inherit = 'social.post'

    youtube_video = fields.Char('YouTube Video',
        help="Simply holds the filename of the video as the video itself is uploaded directly to YouTube")
    youtube_video_id = fields.Char('YouTube Video Id',
        help="Contains the ID of the video as returned by the YouTube API")
    youtube_video_category_id = fields.Char('YouTube Category Id',
        help="Contains the ID of the video category as returned by the YouTube API")
    youtube_access_token = fields.Char('YouTube Access Token',
        compute='_compute_youtube_access_token')
    youtube_title = fields.Char('YouTube Video Title')
    youtube_description = fields.Text('YouTube Video Description')
    youtube_preview = fields.Html('YouTube Preview', compute='_compute_youtube_preview')
    youtube_accounts_count = fields.Integer('Selected YouTube Accounts',
        compute='_compute_youtube_accounts_count')
    youtube_accounts_other_count = fields.Integer('Selected Other Accounts',
        compute='_compute_youtube_accounts_count')
    youtube_video_privacy = fields.Selection([('public', 'Public'), ('unlisted', 'Unlisted'), ('private', 'Private')],
        string='Video Privacy', default='public',
        help='Once posted, set the video as Public/Private/Unlisted')
    youtube_video_url = fields.Char('YouTube Video Url', compute="_compute_youtube_video_url")
    youtube_thumbnail_url = fields.Char('YouTube Thumbnail Url', compute="_compute_youtube_thumbnail_url")

    @api.constrains('message', 'image_ids')
    def _check_has_message_or_image(self):
        """ When posting only on YouTube, the 'message' and 'image_ids' field can (and should) be empty. """
        youtube_posts_only = self.filtered(
            lambda post: all(media.media_type == 'youtube' for media in post.media_ids))
        super(SocialPostYoutube, self -
              youtube_posts_only)._check_has_message_or_image()


    @api.depends('youtube_video_id')
    def _compute_stream_posts_count(self):
        super(SocialPostYoutube, self)._compute_stream_posts_count()

    @api.depends('account_ids.media_type', 'account_ids.youtube_access_token')
    def _compute_youtube_access_token(self):
        for post in self:
            youtube_account = post.account_ids.filtered(lambda account: account.media_type == 'youtube')
            if len(youtube_account) == 1:
                youtube_account._refresh_youtube_token()
                post.youtube_access_token = youtube_account.youtube_access_token
            else:
                post.youtube_access_token = False

    @api.depends('youtube_title', 'youtube_description', 'youtube_video_id', 'scheduled_date', 'youtube_accounts_count')
    def _compute_youtube_preview(self):
        for post in self:
            if not (post.youtube_accounts_count == 1 and post.youtube_title):
                post.youtube_preview = False
                continue
            post.youtube_preview = self.env['ir.qweb']._render('social_youtube.youtube_preview', {
                'youtube_title': post.youtube_title or _('Video'),
                'youtube_description': post.youtube_description,
                'youtube_video_id': post.youtube_video_id,
                'published_date': post.scheduled_date if post.scheduled_date else fields.Datetime.now(),
                'post_link': "https://www.youtube.com/watch?v=%s" % post.youtube_video_id if post.youtube_video_id else '',
            })

    @api.depends('account_ids.media_type')
    def _compute_youtube_accounts_count(self):
        for post in self:
            post.youtube_accounts_count = len(post.account_ids.filtered(
                lambda account: account.media_type == 'youtube'))
            post.youtube_accounts_other_count = len(post.account_ids) - post.youtube_accounts_count

    @api.depends('youtube_video_id')
    def _compute_youtube_thumbnail_url(self):
        for post in self:
            post.youtube_thumbnail_url = "http://i3.ytimg.com/vi/%s/hqdefault.jpg" % post.youtube_video_id

    @api.depends('youtube_video_id')
    def _compute_youtube_video_url(self):
        for post in self:
            post.youtube_video_url = "https://www.youtube.com/watch?v=%s" % post.youtube_video_id

    def _check_post_access(self):
        super(SocialPostYoutube, self)._check_post_access()

        for social_post in self:
            if social_post.youtube_accounts_count > 1:
                raise UserError(_("Please select a single YouTube account at a time."))
            if not social_post.youtube_video_id and 'youtube' in social_post.media_ids.mapped('media_type'):
                raise UserError(_("You have to upload a video when posting on YouTube."))
            if social_post.youtube_title:
                if ">" in social_post.youtube_title or "<" in social_post.youtube_title:
                    raise ValidationError(_("Title should not contain > or < symbol."))
                elif len(social_post.youtube_title) > 100:
                    raise ValidationError(_("Title cannot exceed 100 characters."))
            if social_post.youtube_description:
                if ">" in social_post.youtube_description or "<" in social_post.youtube_description:
                    raise ValidationError(_("Description should not contain > or < symbol."))
                elif len(social_post.youtube_description) > 5000:
                    raise ValidationError(_("Description cannot exceed 5000 characters."))

    @api.model_create_multi
    def create(self, vals_list):
        """The names of the UTM sources are generated based on the content of _rec_name.

        But for Youtube, the message field is not required, so we should use the title
        of the video instead.
        """
        for values in vals_list:
            if not values.get('message') and not values.get('name') and values.get('youtube_title'):
                values['name'] = self.env['utm.source']._generate_name(self, values.get('youtube_title'))
        return super().create(vals_list)

    def _get_stream_post_domain(self):
        domain = super(SocialPostYoutube, self)._get_stream_post_domain()
        youtube_video_ids = [youtube_video_id for youtube_video_id in self.mapped('youtube_video_id') if youtube_video_id]
        if youtube_video_ids:
            return expression.OR([domain, [('youtube_video_id', 'in', youtube_video_ids)]])
        else:
            return domain

    @api.model
    def _prepare_post_content(self, message, media_type, **kw):
        message = super(SocialPostYoutube, self)._prepare_post_content(message, media_type, **kw)
        if media_type != 'youtube' and kw.get('youtube_video_id'):
            message += f'\n\nhttps://youtube.com/watch?v={kw.get("youtube_video_id")}'
        return message

    @api.model
    def _get_post_message_modifying_fields(self):
        return super(SocialPostYoutube, self)._get_post_message_modifying_fields() + ['youtube_video_id']
