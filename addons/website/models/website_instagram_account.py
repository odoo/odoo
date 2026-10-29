import logging
import time

import requests
from requests import RequestException

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WebsiteInstagramAccount(models.Model):
    _name = 'website.instagram.account'
    _description = "Instagram Account"

    name = fields.Char("Username", required=True, readonly=True)
    instagram_id = fields.Char("Instagram ID", required=True, readonly=True)
    access_token = fields.Char(required=True, groups=fields.NO_ACCESS)

    _instagram_id_unique = models.Constraint(
        'UNIQUE(instagram_id)',
        "This Instagram account is already connected.",
    )

    @api.model
    def connect(self, access_token):
        """ Connect the Instagram account of the given access token, or update
        its token if it is already connected.

        :return: the id of the account, or False if Instagram rejects the
            access token.
        """
        self.check_access('create')
        feed = self._fetch_feed(access_token, int(time.time() // 3600))
        if 'id' not in feed:
            return False
        account = self.search([('instagram_id', '=', feed['id'])])
        values = {'name': feed['username'], 'access_token': access_token}
        if account:
            account.sudo().write(values)
        else:
            account = self.sudo().create({**values, 'instagram_id': feed['id']})
        return account.id

    def _get_feed(self, limit):
        """ Return the `username` and `profile_picture_url` of the account, and
        its latest `posts`.
        """
        # Instagram media URLs are signed and expire: only reuse the fetched
        # feed during the current hour.
        feed = self._fetch_feed(self.sudo().access_token, int(time.time() // 3600))
        return {**feed, 'posts': feed['posts'][:limit]}

    @api.model
    @api.ormcache('access_token', 'hour')
    def _fetch_feed(self, access_token, hour):
        try:
            # PY006: both requested URLs are hard-coded and have a timeout. They
            # are only requested when the hourly cache is empty, not in a loop.
            response = requests.get('https://graph.instagram.com/me', params={
                'access_token': access_token,
                'fields': 'username,profile_picture_url',
            }, timeout=5)
            response.raise_for_status()
            profile = response.json()
            response = requests.get('https://graph.instagram.com/me/media', params={
                'access_token': access_token,
                'fields': 'caption,comments_count,like_count,media_type,media_url,permalink,thumbnail_url',
                'limit': 16,  # The snippet options allow to display up to 16 posts.
            }, timeout=5)
            response.raise_for_status()
            media = response.json()
        except RequestException as e:
            # Do not log the exception: its message contains the access token.
            _logger.warning(
                "Instagram feed could not be fetched: %s",
                "Instagram is unreachable." if e.response is None else e.response.text,
            )
            return {'posts': ()}
        return {
            'id': profile['id'],
            'username': profile['username'],
            'profile_picture_url': profile['profile_picture_url'],
            'posts': tuple(
                # The `media_url` of a video is the video itself.
                {**post, 'image_url': post['thumbnail_url'] if post['media_type'] == 'VIDEO' else post['media_url']}
                for post in media['data']
            ),
        }
