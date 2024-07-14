# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from odoo import models, fields
from werkzeug.urls import url_join


class SocialLivePostInstagram(models.Model):
    _inherit = 'social.live.post'

    instagram_post_id = fields.Char('Instagram Post ID', readonly=True)

    def _refresh_statistics(self):
        super(SocialLivePostInstagram, self)._refresh_statistics()
        accounts = self.env['social.account'].search([('media_type', '=', 'instagram')])

        for account in accounts:
            posts_endpoint = url_join(
                self.env['social.media']._INSTAGRAM_ENDPOINT,
                f'{account.instagram_account_id}/media')

            response = requests.get(posts_endpoint,
                params={
                    'access_token': account.instagram_access_token,
                    'fields': 'id,comments_count,like_count'
                },
                timeout=5
            ).json()

            if 'data' not in response:
                self.account_id._action_disconnect_accounts(response)
                return False

            instagram_post_ids = [post.get('id') for post in response['data']]
            existing_live_posts = self.env['social.live.post'].sudo().search([
                ('instagram_post_id', 'in', instagram_post_ids)
            ])

            existing_live_posts_by_instagram_post_id = {
                live_post.instagram_post_id: live_post for live_post in existing_live_posts
            }

            for post in response['data']:
                existing_live_post = existing_live_posts_by_instagram_post_id.get(post.get('id'))
                if existing_live_post:
                    existing_live_post.write({
                        'engagement': post.get('comments_count', 0) + post.get('like_count', 0)
                    })

    def _post(self):
        instagram_live_posts = self._filter_by_media_types(['instagram'])
        super(SocialLivePostInstagram, (self - instagram_live_posts))._post()

        for live_post in instagram_live_posts:
            live_post._post_instagram()

    def _post_instagram(self):
        """ Posting on Instagram is done in 2 separate successive steps.

        First create what they call the 'media container', that basically means upload the image and
        the associated message using a first HTTP call.

        Then mark this 'container' as published using the ID returned by the first call.
        Without this second step, the content is not visible on the Instagram account.

        More information & examples:
        - https://developers.facebook.com/docs/instagram-api/reference/ig-user/media
        - https://developers.facebook.com/docs/instagram-api/reference/ig-user/media_publish """

        self.ensure_one()
        account = self.account_id
        post = self.post_id

        base_url = self.get_base_url()

        media_result = requests.post(
            url_join(
                self.env['social.media']._INSTAGRAM_ENDPOINT,
                "/%s/media" % account.instagram_account_id
            ),
            data={
                'caption': self.message,
                'access_token': account.instagram_access_token,
                'image_url': url_join(
                    base_url,
                    f'/social_instagram/{post.instagram_access_token}/get_image'
                )
            },
            timeout=10
        )

        if media_result.status_code != 200 or not media_result.json().get('id'):
            self.write({
                'state': 'failed',
                'failure_reason': json.loads(media_result.text or '{}').get('error', {}).get('message', '')
            })
            return

        publish_result = requests.post(
            url_join(
                self.env['social.media']._INSTAGRAM_ENDPOINT,
                "/%s/media_publish" % account.instagram_account_id
            ),
            data={
                'access_token': account.instagram_access_token,
                'creation_id': media_result.json()['id'],
            },
            timeout=5
        )

        if (publish_result.status_code == 200):
            self.instagram_post_id = publish_result.json().get('id', False)
            values = {
                'state': 'posted',
                'failure_reason': False
            }
        else:
            values = {
                'state': 'failed',
                'failure_reason': json.loads(publish_result.text or '{}').get('error', {}).get('message', '')
            }

        self.write(values)
