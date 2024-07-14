# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
import dateutil.parser
import requests

from odoo import models, fields, api
from werkzeug.urls import url_join


class SocialStreamFacebook(models.Model):
    _inherit = 'social.stream'

    def _apply_default_name(self):
        facebook_streams = self.filtered(lambda s: s.media_id.media_type == 'facebook')
        super(SocialStreamFacebook, (self - facebook_streams))._apply_default_name()

        for stream in facebook_streams:
            stream.write({'name': '%s: %s' % (stream.stream_type_id.name, stream.account_id.name)})

    def _fetch_stream_data(self):
        if self.media_id.media_type != 'facebook':
            return super(SocialStreamFacebook, self)._fetch_stream_data()

        if self.stream_type_id.stream_type == 'facebook_page_posts':
            return self._fetch_page_posts('published_posts')
        elif self.stream_type_id.stream_type == 'facebook_page_mentions':
            return self._fetch_page_posts('tagged')

    def _fetch_page_posts(self, endpoint_name):
        self.ensure_one()

        facebook_fields = [
            'id',
            'message',
            'from',
            'shares',
            'likes.limit(1).summary(true)',
            'comments.limit(10).summary(true){message,from,like_count}',
            'attachments',
            'created_time',
            'message_tags'
        ]
        if endpoint_name == 'published_posts':
            facebook_fields.append('insights.metric(post_impressions)')

        posts_endpoint_url = url_join(self.env['social.media']._FACEBOOK_ENDPOINT_VERSIONED, "%s/%s" % (self.account_id.facebook_account_id, endpoint_name))
        result = requests.get(posts_endpoint_url,
            params={
                'access_token': self.account_id.facebook_access_token,
                'fields': ','.join(facebook_fields)
            },
            timeout=5
        )

        result_posts = result.json().get('data')
        if not result_posts:
            self.account_id._action_disconnect_accounts(result.json())
            return False

        facebook_post_ids = [post.get('id') for post in result_posts]
        existing_posts = self.env['social.stream.post'].search([
            ('stream_id', '=', self.id),
            ('facebook_post_id', 'in', facebook_post_ids)
        ])
        existing_posts_by_facebook_post_id = {
            post.facebook_post_id: post for post in existing_posts
        }

        posts_to_create = []
        for post in result_posts:
            values = {
                'stream_id': self.id,
                'message': self._format_facebook_message(post.get('message'), post.get('message_tags')),
                'author_name': post.get('from', {}).get('name', ''),
                'facebook_author_id': post.get('from', {}).get('id'),
                'published_date': dateutil.parser.parse(post.get('created_time'), ignoretz=True),
                'facebook_shares_count': post.get('shares', {}).get('count'),
                'facebook_likes_count': post.get('likes', {}).get('summary', {}).get('total_count'),
                'facebook_user_likes': post.get('likes', {}).get('summary', {}).get('has_liked'),
                'facebook_comments_count': post.get('comments', {}).get('summary', {}).get('total_count'),
                'facebook_reach': post.get('insights', {}).get('data', [{}])[0].get('values', [{}])[0].get('value'),
                'facebook_post_id': post.get('id'),
                'facebook_is_event_post': post.get('attachments', {}).get('data', [{}])[0].get('type') == 'event',
            }

            attachments = self._extract_facebook_attachments(post)
            existing_post = existing_posts_by_facebook_post_id.get(post.get('id'))
            if existing_post:
                if attachments.get('stream_post_image_ids'):
                    values['stream_post_image_ids'] = [(5, 0, 0)] + attachments['stream_post_image_ids']
                existing_post.sudo().write(values)
            else:
                if attachments or values['message']:
                    # do not create post without content
                    values.update(attachments)
                    posts_to_create.append(values)

        stream_posts = self.env['social.stream.post'].sudo().create(posts_to_create)
        return any(stream_post.stream_id.create_uid.id == self.env.uid for stream_post in stream_posts)

    @api.model
    def _extract_facebook_attachments(self, post):
        result = {}

        for attachment in post.get('attachments', {}).get('data', []):
            if attachment.get('type') == 'share':
                result.update({
                    'link_title': attachment.get('title'),
                    'link_description': attachment.get('description'),
                    'link_url': attachment.get('url'),
                })

                if attachment.get('media'):
                    result.update({
                        'link_image_url': attachment.get('media').get('image').get('src')
                    })
            elif attachment.get('type') == 'album':
                images = []
                images_urls = []
                for sub_image in attachment.get('subattachments', {}).get('data', []):
                    image_url = sub_image.get('media').get('image').get('src')
                    images.append({
                        'image_url': image_url
                    })
                    images_urls.append(image_url)

                if images:
                    result.update({
                        'stream_post_image_ids': [(0, 0, attachment) for attachment in images],
                    })
            elif attachment.get('type') in ['photo', 'animated_image_video']:
                # TODO improvement later: handle videos in Feed view to correctly display FB GIFs?
                image_src = attachment.get('media', {}).get('image', {}).get('src')
                if image_src:
                    result.update({'stream_post_image_ids': [(0, 0, {'image_url': image_src})]})

            elif attachment.get('type') == 'event':
                # events creation post are handle like link and image in the frontend
                result.update({
                    'link_title': attachment.get('title'),
                    'link_description': attachment.get('description'),
                    'link_url': attachment.get('target', {}).get('url', ''),
                })

                image_src = attachment.get('media', {}).get('image', {}).get('src')
                if image_src:
                    result.update({'stream_post_image_ids': [(0, 0, {'image_url': image_src})]})

        return result

    @api.model
    def _format_facebook_message(self, message, tags):
        """
        This allows to create links to the referenced Facebook pages

        example:
            "Hello Odoo :)" -> "Hello @[542132] Odoo :)"
            "Hello Odoo Social :)" -> "Hello @[542132] Odoo-Social :)"
            "Hello Odoo - Social :)" -> "Hello @[542132] Odoo-Social :)"

        details:
            "Hello @[42] faketag Odoo - Social :)" -> "Hello @ [42] faketag @[542132] Odoo-Social :)""
            -> With associated tag: {name: "Odoo - Social", offset: 20, length: 13}

            We take the message until the tag offset: "Hello @[42] faketag "
            and remove the fake tag in the process "Hello @ [42] faketag "
            Then we insert the forged tag "@[542132] Odoo-Social"
            Then take the rest of the message, starting at index tag offset + length, since we inserted the forged tag instead

        :param message: str message
        :param tags: list of tags in the message as received through Facebook endpoint
            - id: ID of the page/user/group tagged
            - name: name of the page/user/group tagged
            - offset: position of the tag in the text
            - length: length of the tag in the text
        """
        if not message:
            return message

        def remove_forged_tags(message):
            """
            Remove False positive in the message
                (e.g: if someone write "@[42] test" without tagging someone)
            """
            return re.sub(r'\B@\[', '@ [', message)

        # Remove Facebook hashtags that have are considered as tags with ID but are not managed by this method
        tags = [tag for tag in tags or [] if not tag.get('name', '').startswith('#')]

        message_index = 0
        message_with_tags = ''
        for tag in tags or []:
            no_space_name = re.sub(r'\s+', '-', re.sub(r'\s*-\s*', '-', tag['name']))
            forged_tag = '@[%s] %s' % (tag['id'], no_space_name)
            message_with_tags += remove_forged_tags(message[message_index:tag['offset']]) + forged_tag
            message_index = tag['offset'] + tag['length']

        message_with_tags += remove_forged_tags(message[message_index:])

        return message_with_tags
