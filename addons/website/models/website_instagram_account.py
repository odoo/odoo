import logging
import time
from datetime import timedelta

import requests
from requests import RequestException

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Long-lived access tokens expire 60 days after being generated or refreshed.
ACCESS_TOKEN_VALIDITY = timedelta(days=60)
# Access tokens are refreshed a week before they expire, so that a failed
# refresh can be retried daily until then.
ACCESS_TOKEN_REFRESH_MARGIN = timedelta(weeks=1)


def _get_error_message(error):
    return "Instagram is unreachable." if error.response is None else error.response.text


class WebsiteInstagramAccount(models.Model):
    _name = 'website.instagram.account'
    _description = "Instagram Account"

    name = fields.Char("Username", required=True, readonly=True)
    instagram_id = fields.Char("Instagram ID", required=True, readonly=True)
    access_token = fields.Char(required=True, groups=fields.NO_ACCESS)
    access_token_expiration = fields.Datetime("Access Token Expiration", required=True, readonly=True)

    _instagram_id_unique = models.Constraint(
        'UNIQUE(instagram_id)',
        "This Instagram account is already connected.",
    )

    @api.model
    def connect(self, access_token):
        """ Connect the Instagram account of the given access token, or update
        its token if it is already connected.

        :return: the id of the account, or False if Instagram rejects the
            access token or is unreachable.
        """
        self.check_access('create')
        try:
            # Do not use the hourly cache: a failed check would stay cached,
            # and trying again during the hour would fail too.
            feed = self._fetch_feed(access_token)
        except RequestException as e:
            _logger.warning("Instagram account could not be connected: %s", _get_error_message(e))
            return False
        account = self.search([('instagram_id', '=', feed['instagram_id'])])
        values = {
            'name': feed['username'],
            'access_token': access_token,
            # Instagram does not tell when the token expires: assume it was
            # generated just before being connected.
            'access_token_expiration': fields.Datetime.now() + ACCESS_TOKEN_VALIDITY,
        }
        if account:
            account.sudo().write(values)
        else:
            account = self.sudo().create({**values, 'instagram_id': feed['instagram_id']})
        self._schedule_access_tokens_refresh()
        return account.id

    def _get_feed(self, limit):
        """ Return the `username` and `profile_picture_url` of the account, and
        its latest `posts`.
        """
        # Expired access tokens cannot be used anymore: do not request
        # Instagram until the account is connected again.
        if self.access_token_expiration < fields.Datetime.now():
            return {'posts': ()}
        # Instagram media URLs are signed and expire: only reuse the fetched
        # feed during the current hour.
        feed = self._get_cached_feed(self.access_token, int(time.time() // 3600))
        return {**feed, 'posts': feed['posts'][:limit]}

    @api.ormcache('access_token', 'hour')
    def _get_cached_feed(self, access_token, hour):
        try:
            return self._fetch_feed(access_token)
        except RequestException as e:
            _logger.warning(
                "Feed of Instagram account %s could not be fetched: %s",
                self.name, _get_error_message(e),
            )
            return {'posts': ()}

    @api.model
    def _fetch_feed(self, access_token):
        """ Request the profile and the latest posts of the account of the given
        access token.

        :raise RequestException: if Instagram rejects the access token or is
            unreachable.
        """
        response = requests.get('https://graph.instagram.com/me', params={
            'access_token': access_token,
            'fields': 'username,profile_picture_url',
        }, timeout=5)
        response.raise_for_status()
        profile = response.json()
        response = requests.get('https://graph.instagram.com/me/media', params={
            'access_token': access_token,
            'fields': 'caption,comments_count,like_count,media_type,media_url,permalink,thumbnail_url',
            'limit': 16,
        }, timeout=5)
        response.raise_for_status()
        media = response.json()
        return {
            'instagram_id': profile['id'],
            'username': profile['username'],
            'profile_picture_url': profile.get('profile_picture_url'),
            'posts': tuple(
                {**post, 'image_url': image_url}
                for post in media['data']
                if (image_url := post.get('thumbnail_url') if post['media_type'] == 'VIDEO' else post.get('media_url'))
            ),
        }

    def _cron_refresh_access_tokens(self):
        """ Refresh the access tokens that expire within a week, so that they
        never expire. A failed refresh is retried daily until the token
        expires. Expired tokens cannot be refreshed: their account must be
        connected again.
        """
        now = fields.Datetime.now()
        accounts = self.search([
            ('access_token_expiration', '>', now),
            ('access_token_expiration', '<=', now + ACCESS_TOKEN_REFRESH_MARGIN),
        ])
        cron = self.env['ir.cron']
        cron._commit_progress(remaining=len(accounts))
        for account in accounts:
            try:
                response = requests.get('https://graph.instagram.com/refresh_access_token', params={
                    'grant_type': 'ig_refresh_token',
                    'access_token': account.access_token,
                }, timeout=5)
                response.raise_for_status()
                token = response.json()
                account.write({
                    'access_token': token['access_token'],
                    'access_token_expiration': now + timedelta(seconds=token['expires_in']),
                })
                _logger.info(
                    "Access token of Instagram account %s refreshed. It expires in %i days.",
                    account.name, token['expires_in'] // 86400,
                )
            except RequestException as e:
                _logger.warning(
                    "Access token of Instagram account %s could not be refreshed: %s",
                    account.name, _get_error_message(e),
                )
            # Save each new token right away: the previous one may be revoked.
            if not cron._commit_progress(1):
                break
        self._schedule_access_tokens_refresh()

    @api.model
    def _schedule_access_tokens_refresh(self):
        """ Run the refresh cron when the next access token is to be refreshed,
        or tomorrow if its refresh failed. The cron does not run while no valid
        access token is connected.
        """
        now = fields.Datetime.now()
        account = self.search([('access_token_expiration', '>', now)], order='access_token_expiration', limit=1)
        if account:
            self.env.ref('website.website_instagram_account_refresh_access_tokens')._trigger(
                max(account.access_token_expiration - ACCESS_TOKEN_REFRESH_MARGIN, now + timedelta(days=1)),
            )
