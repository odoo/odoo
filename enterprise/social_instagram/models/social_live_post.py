# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import requests

from dateutil.relativedelta import relativedelta
from odoo import _, models, fields
from werkzeug.urls import url_join


class SocialLivePostInstagram(models.Model):
    _inherit = 'social.live.post'

    instagram_post_id = fields.Char('Instagram Post ID', readonly=True)

    def _compute_live_post_link(self):
        instagram_live_posts = self._filter_by_media_types(['instagram']).filtered(lambda post: post.state == 'posted')
        super(SocialLivePostInstagram, (self - instagram_live_posts))._compute_live_post_link()

        for post in instagram_live_posts:
            post.live_post_link = f'https://www.instagram.com/{post.account_id.social_account_handle}'

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
        """
        Handles the process of posting images to Instagram, supporting both single and multiple (carousel) posts.

        Steps for Posting Image(s):
        1. Create Media Container(s):
            - Upload image(s) and associated data using an initial HTTP request to create media container(s).

        2. Create Carousel Container (if multiple images):
            - For carousel posts, group the individual media containers into a single carousel container using an additional HTTP request.

        3. Publish the Container:
            - Mark the media or carousel container as published using the ID returned from the previous request(s).

        This process is asynchronous: if a container is not immediately 'FINISHED', we store
        the pending ID(s) and retry via cron.

        More information & examples:
        - https://developers.facebook.com/docs/instagram-api/reference/ig-user/media
        - https://developers.facebook.com/docs/instagram-api/reference/ig-user/media_publish
        """

        self.ensure_one()
        account = self.account_id
        post = self.post_id

        base_url = self.get_base_url()
        endpoint = self.env['social.media']._INSTAGRAM_ENDPOINT
        media_url = url_join(endpoint, f"/{account.instagram_account_id}/media")
        media_publish_url = url_join(endpoint, f"/{account.instagram_account_id}/media_publish")

        session = requests.Session()
        container_id = False

        if self.instagram_post_id and self.instagram_post_id.startswith('containerID-'):
            container_id = self.instagram_post_id.split('containerID-', 1)[1]

        if not container_id:
            media_container_ids = []
            # Step 1: Create Media Container(s)
            for image in self.image_ids:
                data = {
                    'access_token': account.instagram_access_token,
                    'image_url': url_join(
                        base_url,
                        f'/social_instagram/{post.instagram_access_token}/get_image/{image.id}'
                    )
                }

                if len(self.image_ids) == 1:
                    data['caption'] = self.message
                else:
                    data['is_carousel_item'] = True

                media_response = session.post(media_url, data, timeout=10)
                if not media_response.ok or not media_response.json().get('id'):
                    self._instagram_log_error(media_response)
                    return

                media_container_ids.append(media_response.json().get('id'))

            if len(media_container_ids) > 1:
                # Step 2: Create Carousel Container
                media_response = session.post(
                    media_url,
                    json={
                        'caption': self.message,
                        'access_token': account.instagram_access_token,
                        'media_type': 'CAROUSEL',
                        'children': media_container_ids
                    },
                    timeout=10,
                )
                if not media_response.ok or not media_response.json().get('id'):
                    self._instagram_log_error(media_response)
                    return
                container_id = media_response.json()['id']
            else:
                container_id = media_container_ids[0]

        # Check status of the final container (single or carousel)
        status_response = session.get(f"{endpoint}/{container_id}", params={
            'access_token': account.instagram_access_token,
            'fields': 'status_code'
        }, timeout=3)

        if not status_response.ok:
            self._instagram_log_error(status_response)
            return

        status_data = status_response.json()
        status_code = status_data.get('status_code')

        if status_code == 'ERROR':
            self.write({
                'state': 'failed',
                'failure_reason': self.env._("The media container failed to process.")
            })
            return
        elif status_code == 'EXPIRED':
            self.write({
                'state': 'failed',
                'failure_reason': self.env._("The media container expired.")
            })
            return
        elif status_code == 'PUBLISHED':
            status_response = session.get(f"{endpoint}/{container_id}", params={
                'access_token': account.instagram_access_token,
                'fields': 'ig_id'
            }, timeout=3)
            status_data = status_response.json()
            self.write({
                'state': 'posted',
                'failure_reason': False,
                'instagram_post_id': status_data.get('ig_id') or status_data.get('id')
            })
            return
        elif status_code != 'FINISHED':
            self.write({
                'state': 'posting',
                'instagram_post_id': f'containerID-{container_id}'
            })
            cron = self.env.ref('social.ir_cron_post_scheduled')
            cron._trigger(at=fields.Datetime.now() + relativedelta(minutes=1))
            return

        # Step 3: Publish the Container
        publish_response = session.post(
            media_publish_url,
            data={
                'access_token': account.instagram_access_token,
                'creation_id': container_id,
            },
            timeout=10,
        )

        if not publish_response.ok or not publish_response.json().get('id'):
            self._instagram_log_error(publish_response)
            return

        self.write({
            'state': 'posted',
            'failure_reason': False,
            'instagram_post_id': publish_response.json()['id']
        })

    def _instagram_log_error(self, response):
        """Parse the Instagram response and log the appropriate error."""
        self.ensure_one()
        error = json.loads(response.text or '{}').get('error', {})
        error_message = error.get('message', '')
        if error.get('code') == 9004:
            error_message = "\n".join((
                _("Your media didn't go through. This is usually caused by one of the following:"),
                _("- Check your file: Ensure it isn't corrupted and is from 320 to 1440 pixels wide, 8MB maximum, aspect ratio between 4:5 and 1.91:1."),
                _("- Check your connection: Your server may be offline or temporarily unreachable."),
                _("- Check permissions: Your site's robots.txt might be blocking Instagram from accessing the media folder (make sure /social_instagram is not blocked)."),
            ))

        self.write({
            'state': 'failed',
            'failure_reason': error_message,
        })
