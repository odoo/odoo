# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
import json

from odoo import api, models, fields
from odoo.tools.misc import format_date, _format_time_ago


class SocialStreamPost(models.Model):
    """ A 'stream' post, as opposed to a regular social.post, references a post that
    actually exists on a social.media external database (a Facebook post, a Tweet, ...).

    Stream posts are created by fetching data from the related social media third party API.
    They should not be directly created/modified.

    social.stream.posts are used to fill the 'Feed' view that allows users to follow the social.media activity
    based on their interest (a Facebook Page, a Twitter hashtag, ...).
    They are directly created by their related social.stream. """

    _name = 'social.stream.post'
    _description = 'Social Stream Post'
    _order = 'published_date desc'

    message = fields.Text("Message")
    author_name = fields.Char('Author Name',
        help="The post author name based on third party information (ex: 'John Doe').")
    author_link = fields.Char('Author Link', compute='_compute_author_link',
        help="Author link to the external social.media (ex: link to the X Account).")
    post_link = fields.Char('Post Link', compute='_compute_post_link',
        help="Post link to the external social.media (ex: link to the actual Facebook Post).")
    stream_id = fields.Many2one('social.stream', string="Social Stream", ondelete="cascade")
    media_type = fields.Selection(related='stream_id.media_id.media_type', string="Related Social Media")
    published_date = fields.Datetime('Published date', help="The post published date based on third party information.")
    formatted_published_date = fields.Char('Formatted Published Date', compute='_compute_formatted_published_date')
    account_id = fields.Many2one(related='stream_id.account_id', string='Related social Account')
    company_id = fields.Many2one('res.company', 'Company', related='account_id.company_id')
    is_author = fields.Boolean('Is Author', compute='_compute_is_author')

    stream_post_image_ids = fields.One2many('social.stream.post.image', 'stream_post_id', string="Stream Post Images",
        help="Images that were shared with this post.")
    # JSON array capturing the URLs of the images to make it easy to display them in the kanban view
    stream_post_image_urls = fields.Text("Stream Post Images URLs",
        compute='_compute_stream_post_image_urls')

    # Some social.medias (ex: Facebook) provide information on the link shared with the post.
    # We store those infomation to render a nice block on the kanban view with the title, image and description.
    link_title = fields.Text("Link Title")
    link_description = fields.Text("Link Description")
    link_image_url = fields.Char("Link Image URL")
    link_url = fields.Char("Link URL")

    def _compute_stream_post_image_urls(self):
        """ See field 'help' for more information. """
        for stream_post in self:
            stream_post.stream_post_image_urls = json.dumps([image.image_url for image in stream_post.stream_post_image_ids])

    def _compute_author_link(self):
        """ Every social module should override this method and handle its own
        records, then call super() on remaining subset. See field 'help' for
        more information. """
        for post in self:
            post.author_link = False

    def _compute_post_link(self):
        """ Every social module should override this method and handle its own
        records, then call super() on remaining subset. See field 'help' for
        more information. """
        for post in self:
            post.post_link = False

    @api.depends('published_date')
    def _compute_formatted_published_date(self):
        for post in self:
            post.formatted_published_date = self._format_published_date(post.published_date) if post.published_date else False

    def _compute_is_author(self):
        self.is_author = False

    def _filter_by_media_types(self, media_types):
        return self.filtered(lambda post: post.media_type in media_types)

    @api.model
    def _format_published_date(self, published_date):
        """ Formats to '5 minutes' instead of date if not older than 12 hours. """
        if (datetime.now() - published_date) < timedelta(hours=12):
            return _format_time_ago(self.env, (datetime.now() - published_date), add_direction=False)
        else:
            return format_date(self.env, published_date)

    def _fetch_matching_post(self):
        """ This method is meant to be overridden by underlying social implementations.
        It returns the social.post linked to this social.stream.post if any, by matching
        the social media specific ID of the social.stream.post to its social.live.post counterpart.

        This can't be easily built dinamically since all social media implementations have their own
        specific IDs, that we don't want to mix. """

        self.ensure_one()
        return self.env['social.post']
