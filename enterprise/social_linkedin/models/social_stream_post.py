# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
from urllib.parse import quote, unquote
from datetime import datetime
from werkzeug.urls import url_join

from odoo import _, models, fields

from odoo.exceptions import UserError
from odoo.addons.social_linkedin.utils import urn_to_id, id_to_urn

_logger = logging.getLogger(__name__)


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
            post.linkedin_author_id = urn_to_id(post.linkedin_author_urn)

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
    # POST EDITION
    # ========================================================

    def _linkedin_edit_post(self, new_message):
        """Make a API call to update the post message."""
        self.ensure_one()
        self.check_access("write")

        response = self.account_id._linkedin_request(
            f"posts/{quote(self.linkedin_post_urn)}",
            json={"patch": {"$set": {"commentary": new_message}}},
            headers={"X-RestLi-Method": "PARTIAL_UPDATE"},
        )
        if not response.ok:
            raise UserError(_("Couldn't update the post: “%s”.", response.text))

        self.message = new_message

    def _linkedin_delete_post(self):
        """Make a API call to delete the post."""
        self.ensure_one()
        self.check_access("unlink")

        response = self.account_id._linkedin_request(
            f"posts/{quote(self.linkedin_post_urn)}", method="DELETE")

        if not response.ok:
            raise UserError(_("Couldn't delete the post: “%s”.", response.text))

        self.unlink()

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    def _linkedin_like_comment(self, comment_urn, like):
        """Like or remove the like on the given comment."""
        self.ensure_one()
        if like:
            response = self.account_id._linkedin_request(
                'reactions',
                params={'actor': self.account_id.linkedin_account_urn},
                json={
                    "root": comment_urn,
                    "reactionType": "LIKE",
                },
            )
        else:
            like_urn = f"(actor:{quote(self.account_id.linkedin_account_urn)},entity:{quote(comment_urn)})"
            response = self.account_id._linkedin_request(f'reactions/{like_urn}', method='DELETE')

        if not response.ok:
            _logger.error('Error during comment like / dislike %r', response.text)
            raise UserError(_('Could not like / dislike this comment.'))

    def _linkedin_comment_add(self, message, comment_urn=None, attachment=None):
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

        if attachment:
            # we upload an image with our comment
            image_urn = self.account_id._linkedin_upload_image(attachment)
            data['content'] = [{'entity': {'image': image_urn}}]

        response = self.account_id._linkedin_request(
            f'socialActions/{quote(self.linkedin_post_urn)}/comments',
            json=data,
        )

        if not response.ok or 'created' not in response.json():
            self.sudo().account_id._action_disconnect_accounts(response)
            raise UserError(_(
                "Failed to post the comment: “%(error_description)s”",
                error_description=response.text))

        result = response.json()
        result['from'] = {  # fill with our own information to save an API call
            'id': self.account_id.linkedin_account_urn,
            'name': self.account_id.name,
            'authorUrn': self.account_id.linkedin_account_urn,
            'picture': f"/web/image?model=social.account&id={self.account_id.id}&field=image",
            'isOrganization': True,
        }
        if attachment:
            urls = self.account_id._linkedin_request_images([urn_to_id(image_urn)])
            result['content'][0]['url'] = next(iter(urls.values()), None)

        return self._linkedin_format_comment(result)

    def _linkedin_comment_delete(self, comment_urn):
        response = self.account_id._linkedin_request(
            'socialActions/%s/comments/%s' % (quote(self.linkedin_post_urn), quote(urn_to_id(comment_urn))),
            method='DELETE',
            params={'actor': self.account_id.linkedin_account_urn},
        )

        if not response.ok:
            _logger.error('Error during comment deletion %r', response.text)
            self.sudo().account_id._action_disconnect_accounts(response.json())

    def _linkedin_comment_edit(self, message, comment_urn):
        response = self.account_id._linkedin_request(
            f'socialActions/{quote(self.linkedin_post_urn)}/comments/{quote(urn_to_id(comment_urn))}',
            json={'patch': {'message': {'$set': {'text': message}}}},
            params={'actor': self.account_id.linkedin_account_urn}
        ).json()

        if 'created' not in response:
            self.sudo().account_id._action_disconnect_accounts(response)
            return {}

        return {'message': response.get('message', {}).get('text', '')}

    def _linkedin_comment_fetch(self, comment_urn=None, offset=0, count=20):
        """Retrieve comments on a LinkedIn element.

        :param element_urn: URN of the element (UGC Post or Comment) on which we want to retrieve comments
            If no specified, retrieve comments on the current post
        :param offset: Used to scroll over the comments, position of the first retrieved comment
        :param count: Number of comments returned
        """
        element_urn = comment_urn or self.linkedin_post_urn

        response = self.account_id._linkedin_request(
            f'socialActions/{quote(element_urn)}/comments',
            params={'start': offset, 'count': count},
        )
        response_json = response.json()
        if 'elements' not in response_json:
            self.sudo().account_id._action_disconnect_accounts(response_json)
        if not response.ok:
            raise UserError(
                _(
                    'Failed to retrieve the post. It might have been deleted or you may not have permission to view it.'
                )
            )

        comments = response_json.get('elements', [])

        persons_ids = {comment.get('actor') for comment in comments if comment.get('actor')}
        organizations_ids = {urn_to_id(author) for author in persons_ids if author.startswith("urn:li:organization:")}
        persons = {urn_to_id(author) for author in persons_ids if author.startswith("urn:li:person:")}
        images_ids = [
            urn_to_id(content.get('entity', {}).get('image'))
            for comment in comments
            for content in comment.get('content', [])
            if content.get('type') == 'IMAGE'
        ]

        formatted_authors = {}

        # get the author information if it's an organization
        if organizations_ids:
            response_json = self.account_id._linkedin_request(
                'organizations',
                object_ids=organizations_ids,
                fields=('id', 'name', 'localizedName', 'vanityName', 'logoV2:(original)'),
            ).json()
            for organization_id, organization in response_json.get('results', {}).items():
                organization_urn = f"urn:li:organization:{organization_id}"
                image_id = urn_to_id(organization.get('logoV2', {}).get('original'))
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
            response_json = requests.get(
                "https://api.linkedin.com/v2/people?ids=List(%s)" % ",".join("(id:%s)" % p for p in persons),
                headers=self.account_id._linkedin_bearer_headers(),
                timeout=5).json()

            for person_id, person_values in response_json.get('results', {}).items():
                person_urn = id_to_urn(person_values['id'], "li:person")
                image_id = urn_to_id(person_values.get('profilePicture', {}).get('displayImage'))
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

            for comment in comments:
                # add the URL in the comment if the API didn't return it
                for content in comment.get('content', []):
                    if content.get('type') == 'IMAGE' and not content.get('url'):
                        content['url'] = image_ids_to_url.get(urn_to_id(content.get('entity', {}).get('image')))

        default_author = {'id': '', 'authorUrn': '', 'name': _('Unknown')}
        for comment in comments:
            comment['from'] = formatted_authors.get(comment.get('actor'), default_author)

        comments = [self._linkedin_format_comment(comment) for comment in comments]
        if 'comment' in element_urn:
            # replies on comments should be sorted chronologically
            comments = comments[::-1]

        liked_per_comment_urn = self._linkedin_comments_user_liked(comments)

        for comment in comments:
            comment_urn = comment["id"].replace('urn:li:activity', 'activity')
            comment["user_likes"] = liked_per_comment_urn.get(comment_urn, False)

        return {
            'postAuthorImage': self.linkedin_author_image_url,
            'currentUserUrn': self.account_id.linkedin_account_urn,
            'accountId': self.account_id.id,
            'comments': comments,
            'offset': offset + count,
            'summary': {'total_count': response_json.get('paging', {}).get('total', 0)},
        }

    def _linkedin_comments_user_liked(self, comments):
        """Determine for each comment, if the current company page liked it or not.

        The key "likedByCurrentUser" is already returned when we fetch all comments,
        but it's true if the current user liked the comment, not if the
        current *page* liked it, so we can not use this field.
        """
        self.ensure_one()
        if not comments:
            return {}

        # comment URN passed in URL is in different format
        # than the comment URN returned by the API...
        comment_urns = [
            comment["id"].replace('urn:li:activity', 'activity')
            for comment in comments
        ]

        response = self.account_id._linkedin_request(
            'reactions',
            complex_object_ids=[
                {"actor": self.account_id.linkedin_account_urn, "entity": comment_urn}
                for comment_urn in comment_urns
            ],
        )

        if not response.ok:
            _logger.error('Error during likes fetch %r', response.text)
            return {}

        response = response.json()

        return {
            # (actor:urn:li:organization:123,entity:urn:li:comment:(activity:456,789))
            # -> urn:li:comment:(activity:456,789)
            unquote(like_urn).split('entity:')[-1][:-1]: True
            for like_urn, values in response.get("results", {}).items()
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
