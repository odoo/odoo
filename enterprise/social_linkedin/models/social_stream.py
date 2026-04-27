# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from urllib.parse import urlparse
import re

from odoo import models, _
from odoo.exceptions import UserError


class SocialStreamLinkedIn(models.Model):
    _inherit = 'social.stream'

    def _apply_default_name(self):
        linkedin_streams = self.filtered(lambda s: s.media_id.media_type == 'linkedin')
        super(SocialStreamLinkedIn, (self - linkedin_streams))._apply_default_name()

        for stream in linkedin_streams:
            stream.write({'name': '%s: %s' % (stream.stream_type_id.name, stream.account_id.name)})

    def _fetch_stream_data(self):
        """Fetch stream data, return True if new data.

        We need to perform 2 HTTP requests. One to retrieve all the posts of
        the organization page and the other, in batch, to retrieve the
        statistics of all posts (there are 2 different endpoints)."""
        self.ensure_one()
        if self.media_id.media_type != 'linkedin':
            return super(SocialStreamLinkedIn, self)._fetch_stream_data()

        # retrieve post information
        if self.stream_type_id.stream_type != 'linkedin_company_post':
            raise UserError(_('Wrong stream type for "%s"', self.name))

        posts_response = self.account_id._linkedin_request(
            "posts",
            params={
                'q': 'author',
                'count': 100,
                'author': self.account_id.linkedin_account_urn,
            },
            fields=('id', 'createdAt', 'author', 'content', 'commentary')
        )
        if posts_response.status_code != 200 or 'elements' not in posts_response.json():
            self.sudo().account_id._action_disconnect_accounts(posts_response.json())
            return False

        stream_post_data = posts_response.json()['elements']

        self._prepare_linkedin_stream_post_images(stream_post_data)

        linkedin_post_data = {
            stream_post_data.get('id'): self._prepare_linkedin_stream_post_values(stream_post_data)
            for stream_post_data in stream_post_data
        }

        # retrieve post statistics
        stats_response = self.account_id._linkedin_request(
            'socialActions',
            params={'count': 100},
            object_ids=linkedin_post_data,
        ).json()

        if 'results' in stats_response:
            for post_urn, post_data in stats_response['results'].items():
                linkedin_post_data[post_urn].update({
                    'linkedin_comments_count': post_data.get('commentsSummary', {}).get('totalFirstLevelComments', 0),
                    'linkedin_likes_count': post_data.get('likesSummary', {}).get('totalLikes', 0),
                })

        # create/update post values
        existing_post_urns = {
            stream_post.linkedin_post_urn: stream_post
            for stream_post in self.env['social.stream.post'].search([
                ('stream_id', '=', self.id),
                ('linkedin_post_urn', 'in', list(linkedin_post_data.keys()))])
        }

        post_to_create = []
        for post_urn in linkedin_post_data:
            if post_urn in existing_post_urns:
                existing_post_urns[post_urn].sudo().write(linkedin_post_data[post_urn])
            else:
                post_to_create.append(linkedin_post_data[post_urn])

        if post_to_create:
            self.env['social.stream.post'].sudo().create(post_to_create)

        return bool(post_to_create)

    def _format_linkedin_name(self, json_data):
        if 'localizedName' in json_data:
            return json_data['localizedName']
        if 'localizedLastName' in json_data and 'localizedFirstName' in json_data:
            return f'{json_data["localizedLastName"]} {json_data["localizedFirstName"]}'
        return _('Unknown')

    def _media_urn_to_url(self, media_type, media_urns):
        if not media_urns:
            return {}
        response = self.account_id._linkedin_request(
            endpoint=media_type,
            object_ids=media_urns,
        )
        return {
            media: media_values["downloadUrl"]
            for media, media_values in response.json().get('results', {}).items()
            if media_values.get("downloadUrl")
        } if response.ok else {}

    def _prepare_linkedin_stream_post_images(self, posts_data):
        """Fetch the images and videos URLs and insert their URL in posts_data."""
        all_image_urns = set()
        all_video_urns = set()
        for post in posts_data:
            # multi-images post
            images = post.get('content', {}).get('multiImage', {}).get('images', [])
            all_image_urns |= {image['id'] for image in images}
            # single image post
            if media_urn := post.get('content', {}).get('media', {}).get('id'):
                # make sure it's an image or a video
                if 'image' in media_urn:
                    all_image_urns.add(media_urn)
                elif 'video' in media_urn:
                    all_video_urns.add(media_urn)
            # article thumbnail
            if thumbnail_urn := post.get('content', {}).get('article', {}).get('thumbnail'):
                all_image_urns.add(thumbnail_urn)

        url_by_urn = {
            **self._media_urn_to_url('images', all_image_urns),
            **self._media_urn_to_url('videos', all_video_urns),
        }

        # Insert images and videos in the result like the LinkedIn projection should do...
        for post in posts_data:
            # multi-images post
            images = post.get('content', {}).get('multiImage', {}).get('images', [])
            for image in images:
                image["downloadUrl"] = url_by_urn.get(image.get("id"), '')

            # single image or video post
            if media_urn := post.get("content", {}).get("media", {}).get("id"):
                if 'image' in media_urn:
                    post["content"]["media"]["downloadUrl"] = url_by_urn.get(media_urn, '')
                elif 'video' in media_urn:
                    post['commentary'] = f'{post.get("commentary", "")}\n{url_by_urn.get(media_urn, "")}'.strip()

            # article thumbnail
            if thumbnail_urn := post.get("content", {}).get("article", {}).get("thumbnail"):
                post["content"]["article"]["~thumbnail"] = {"downloadUrl": url_by_urn.get(thumbnail_urn, "")}

    def _prepare_linkedin_stream_post_values(self, post_data):
        article = post_data.get('content', {}).get('article', {})
        author_image = f"/web/image?model=social.account&id={self.account_id.id}&field=image"
        return {
            'stream_id': self.id,
            'author_name': self.account_id.name,
            'published_date': datetime.fromtimestamp(post_data.get('createdAt', 0) / 1000),
            'linkedin_post_urn': post_data.get('id'),
            'linkedin_author_urn': post_data.get('author'),
            'linkedin_author_image_url': author_image,
            'message': self._format_from_linkedin_little_text(post_data.get('commentary', '')),
            'stream_post_image_ids': [(5, 0)] + [(0, 0, image_value) for image_value in self._extract_linkedin_image(post_data)],
            **self._extract_linkedin_article(article),
        }

    def _extract_linkedin_image(self, post_data):
        # single image post
        single_image = post_data.get('content', {}).get('media', {}).get('downloadUrl')
        if single_image:
            return [{'image_url': self._enforce_url_scheme(single_image)}]

        # multi-images post
        if images := post_data.get('content', {}).get('multiImage', {}).get('images', []):
            return [
                {'image_url': self._enforce_url_scheme(image.get('downloadUrl'))}
                for image in images if image.get('downloadUrl')
            ]

        # article with thumbnail
        if thumbnail_url := post_data.get('content', {}).get('article', {}).get('~thumbnail', {}).get('downloadUrl'):
            return [{'image_url': self._enforce_url_scheme(thumbnail_url)}]

        return []

    def _extract_linkedin_article(self, article):
        if not article:
            return {}

        return {
            'link_title': article.get('title', '') or article.get('source', ''),
            'link_description': article.get('description', ''),
            'link_url': self._enforce_url_scheme(article.get('source'))
        }

    def _enforce_url_scheme(self, url):
        """Some URLs doesn't starts by "https://". But if we use those bad URLs
        in a HTML link, it will redirect the user the actual website.
        That's why we need to fix those URLs.
        e.g.:
            <a href="www.bad_url.com"/>
        """
        if not url or urlparse(url).scheme:
            return url

        return 'https://%s' % url

    def _format_from_linkedin_little_text(self, input_string):
        """
        Replaces escaped versions of the characters `(){}<>[]_` with their original characters,
        """
        pattern = "\\\\([\\(\\)\\<\\>\\{\\}\\[\\]\\_\\|\\*\\~\\#\\@])"
        output_string = re.sub(pattern, lambda match: match.group(1), input_string)
        return output_string
