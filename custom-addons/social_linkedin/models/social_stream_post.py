# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import requests
from urllib.parse import quote
from datetime import datetime
from werkzeug.urls import url_join

from odoo import _, models, fields


class SocialStreamPostLinkedIn(models.Model):
    _inherit = 'social.stream.post'

    linkedin_post_urn = fields.Char('LinkedIn post URN')
    linkedin_author_urn = fields.Char('LinkedIn author URN')
    linkedin_author_id = fields.Char('LinkedIn author ID', compute='_compute_linkedin_author_urn')
    linkedin_author_vanity_name = fields.Char('LinkedIn Vanity Name', help='Vanity name, used to generate a link to the author')
    linkedin_author_image_url = fields.Char('LinkedIn author image URL')

    linkedin_comments_count = fields.Integer('LinkedIn Comments')
    linkedin_likes_count = fields.Integer('LinkedIn Likes')

    def _compute_linkedin_author_urn(self):
        for post in self:
            if post.linkedin_author_urn:
                post.linkedin_author_id = post.linkedin_author_urn.split(':')[-1]
            else:
                post.linkedin_author_id = False

    def _compute_author_link(self):
        linkedin_posts = self._filter_by_media_types(['linkedin'])
        super(SocialStreamPostLinkedIn, (self - linkedin_posts))._compute_author_link()

        for post in linkedin_posts:
            if post.linkedin_author_urn:
                post.author_link = 'https://linkedin.com/company/%s' % post.linkedin_author_id
            else:
                post.author_link = False

    def _compute_post_link(self):
        linkedin_posts = self._filter_by_media_types(['linkedin'])
        super(SocialStreamPostLinkedIn, (self - linkedin_posts))._compute_post_link()

        for post in linkedin_posts:
            if post.linkedin_post_urn:
                post.post_link = 'https://www.linkedin.com/feed/update/%s' % post.linkedin_post_urn
            else:
                post.post_link = False

    def _compute_is_author(self):
        linkedin_posts = self._filter_by_media_types(['linkedin'])
        super(SocialStreamPostLinkedIn, (self - linkedin_posts))._compute_is_author()

        for post in linkedin_posts:
            post.is_author = post.linkedin_author_urn == post.account_id.linkedin_account_urn

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    def _linkedin_comment_add(self, message, comment_urn=None):
        data = {
            'actor': self.account_id.linkedin_account_urn,
            'message': {
                'text': message,
            },
            'object': self.linkedin_post_urn,
        }

        if comment_urn:
            # we reply yo an existing comment
            data['parentComment'] = comment_urn

        response = self.account_id._linkedin_request(
            'socialActions/%s/comments' % quote(self.linkedin_post_urn),
            method="POST",
            json=data,
        ).json()

        if 'created' not in response:
            self.sudo().account_id._action_disconnect_accounts(response)
            return {}

        response['from'] = {  # fill with our own information to save an API call
            'id': self.account_id.linkedin_account_urn,
            'name': self.account_id.name,
            'authorUrn': self.account_id.linkedin_account_urn,
            'picture': f"/web/image?model=social.account&id={self.account_id.id}&field=image",
            'isOrganization': True,
        }
        return self._linkedin_format_comment(response)

    def _linkedin_comment_delete(self, comment_urn):
        comment_id = re.search(r'urn:li:comment:\(urn:li:activity:\w+,(\w+)\)', comment_urn).group(1)

        response = self.account_id._linkedin_request(
            'socialActions/%s/comments/%s' % (quote(self.linkedin_post_urn), quote(comment_id)),
            method='DELETE',
            params={'actor': self.account_id.linkedin_account_urn},
        )

        if response.status_code != 204:
            self.sudo().account_id._action_disconnect_accounts(response.json())

    def _linkedin_comment_fetch(self, comment_urn=None, offset=0, count=20):
        """Retrieve comments on a LinkedIn element.

        :param element_urn: URN of the element (UGC Post or Comment) on which we want to retrieve comments
            If no specified, retrieve comments on the current post
        :param offset: Used to scroll over the comments, position of the first retrieved comment
        :param count: Number of comments returned
        """
        element_urn = comment_urn or self.linkedin_post_urn

        response = self.account_id._linkedin_request(
            'socialActions/%s/comments' % quote(element_urn),
            params={
                'start': offset,
                'count': count,
            },
        ).json()
        if 'elements' not in response:
            self.sudo().account_id._action_disconnect_accounts(response)

        comments = response.get('elements', [])

        persons_ids = {comment.get('actor') for comment in comments if comment.get('actor')}
        organizations_ids = {author.split(":")[-1] for author in persons_ids if author.startswith("urn:li:organization:")}
        persons = {author.split(":")[-1] for author in persons_ids if author.startswith("urn:li:person:")}
        images_ids = []

        formatted_authors = {}

        # get the author information if it's an organization
        if organizations_ids:
            response = self.account_id._linkedin_request(
                'organizations',
                object_ids=organizations_ids,
                fields=('id', 'name', 'localizedName', 'vanityName', 'logoV2:(original)'),
            ).json()
            for organization_id, organization in response.get('results', {}).items():
                organization_urn = f"urn:li:organization:{organization_id}"
                image_id = organization.get('logoV2', {}).get('original', '').split(':')[-1]
                images_ids.append(image_id)
                formatted_authors[organization_urn] = {
                    'id': organization_urn,
                    'name': organization.get('localizedName'),
                    'authorUrn': organization_urn,
                    'picture': image_id,
                    'vanityName': organization.get('vanityName'),
                    'isOrganization': True,
                }

        # get the author information if it's normal user
        if persons:
            # On the 3 December 2023, /people is still not in the rest API...
            # As the LinkedIn support suggested, we need to use the old endpoint...
            response = requests.get(
                "https://api.linkedin.com/v2/people?ids=List(%s)" % ",".join("(id:%s)" % p for p in persons),
                headers=self.account_id._linkedin_bearer_headers(),
                timeout=5).json()

            for person_id, person_values in response.get('results', {}).items():
                person_id = person_id.split(':')[-1][:-1]  # LinkedIn return weird format
                person_urn = f"urn:li:person:{person_id}"
                image_id = person_values.get('profilePicture', {}).get('displayImage', '').split(':')[-1]
                images_ids.append(image_id)
                formatted_authors[person_urn] = {
                    'id': person_urn,
                    'name': self.stream_id._format_linkedin_name(person_values),
                    'authorUrn': person_urn,
                    'picture': image_id,
                    'vanityName': person_values.get('vanityName'),
                    'isOrganization': False,
                }

        if images_ids:
            image_ids_to_url = self.account_id._linkedin_request_images(images_ids)
            for author in formatted_authors.values():
                author['picture'] = image_ids_to_url.get(author['picture'])

        default_author = {'id': '', 'authorUrn': '', 'name': _('Unknown')}
        for comment in comments:
            comment['from'] = formatted_authors.get(comment.get('actor'), default_author)

        comments = [self._linkedin_format_comment(comment) for comment in comments]
        if 'comment' in element_urn:
            # replies on comments should be sorted chronologically
            comments = comments[::-1]

        return {
            'postAuthorImage': self.linkedin_author_image_url,
            'currentUserUrn': self.account_id.linkedin_account_urn,
            'accountId': self.account_id.id,
            'comments': comments,
            'offset': offset + count,
            'summary': {'total_count': response.get('paging', {}).get('total', 0)},
        }

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    def _linkedin_format_comment(self, json_data):
        """Formats a comment returned by the LinkedIn API to a dict that will be interpreted by our frontend."""
        created_time = json_data.get('created', {}).get('time', 0)
        data = {
            'id': json_data.get('commentUrn'),
            'from': json_data.get('from'),
            'message': json_data.get('message', {}).get('text', ''),
            'created_time': created_time,
            'formatted_created_time': self.env['social.stream.post']._format_published_date(
                datetime.fromtimestamp(created_time / 1000)),
            'likes': {
                'summary': {
                    'total_count': json_data.get('likesSummary', {}).get('totalLikes', 0),
                    'can_like': False,
                    'has_liked': json_data.get('likesSummary', {}).get('likedByCurrentUser', 0),
                }
            },
            'comments': {
                'data': {
                    'length': json_data.get('commentsSummary', {}).get('totalFirstLevelComments', 0),
                    'parentUrn': json_data.get('commentUrn'),
                },
            },
        }

        image_content = next(
            (content for content in json_data.get('content', [])
             if content.get('type') == 'IMAGE'),
            None,
        )
        if image_content:
            # Sometimes we can't access the image (e.g. if it's still being process)
            # so we have a placeholder image if the download URL is not yet available
            data['attachment'] = {
                'type': 'photo',
                'media': {'image': {'src': image_content.get('url', '/web/static/img/placeholder.png')}},
            }

        return data

    def _fetch_matching_post(self):
        self.ensure_one()

        if self.account_id.media_type == 'linkedin' and self.linkedin_post_urn:
            return self.env['social.live.post'].search(
                [('linkedin_post_id', '=', self.linkedin_post_urn)], limit=1
            ).post_id
        else:
            return super(SocialStreamPostLinkedIn, self)._fetch_matching_post()
