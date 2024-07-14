# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DemoSocialStreamPost(models.Model):
    """ Mostly contains methods that return 'mock' data for the comments feature. """

    _inherit = 'social.stream.post'

    # ========================================================
    # COMMENTS / LIKES
    # ========================================================

    # FACEBOOK

    def _facebook_comment_fetch(self, next_records_token=False, count=20):
        return {
            'comments': self._get_demo_comments(),
            'summary': {'total_count': 2}
        }

    def _facebook_comment_post(self, endpoint_url, message, existing_attachment_id=None, attachment=None):
        """ Returns a fake comment containing the passed 'message' """
        return self._get_new_comment_demo(message)

    def _facebook_like(self, object_id, like):
        """ Overridden to bypass third-party API calls. """
        return

    # INSTAGRAM

    def _instagram_comment_add(self, message, object_id, comment_type="comment"):
        return self._get_new_comment_demo(message)

    def _instagram_comment_fetch(self, next_records_token=False, count=20):
        return {
            'comments': self._get_demo_comments(),
        }

    # LINKEDIN

    def _linkedin_comment_add(self, message, comment_urn=None):
        """ Returns a fake comment containing the passed 'message' """
        return {
            'id': 'urn:li:comment:(urn:li:activity:12547,452542)',
            'formatted_created_time': '10/02/2019',
            'likes': {'summary': {'total_count': 0}},
            'from': {
                'name': 'Mitchell Admin',
                'profile_image_url_https': '/web/image/res.users/2/avatar_128',
                'authorUrn': 'urn:li:organization:2414183',
            },
            'message': message
        }

    def _linkedin_comment_delete(self, comment_urn):
        pass

    def _linkedin_comment_fetch(self, comment_urn=None, offset=0, count=20):
        if comment_urn:
            comments = self._get_demo_sub_comments()
        else:
            comments = self._get_demo_comments()

        for comment in comments:
            comment['id'] = 'urn:li:comment:(urn:li:activity:12547,452542)'

            if 'comments' in comment:
                comment['comments']['data'] = {
                    'length': len(comment['comments']['data']),
                    'parentUrn': comment['id'],
                }

        return {
            'comments': comments,
            'summary': {'total_count': 2}
        }

    # TWITTER

    def _twitter_comment_add(self, stream, comment_id, message, attachment):
        """ Returns a fake comment containing the passed 'message' """
        comment = self._get_new_comment_demo(message)
        comment['in_reply_to_tweet_id'] = comment_id
        return comment

    def _twitter_comment_fetch(self, page=1):
        return {
            'comments': self._get_demo_comments()
        }

    def _twitter_tweet_like(self, stream, tweet_id, like):
        return True

    def _twitter_do_retweet(self):
        """ In the demo module, we simply increment the retweet counter. """
        self.write({
            'twitter_retweet_count': self.twitter_retweet_count + 1
        })
        return True

    def _twitter_undo_retweet(self):
        """ In the demo module, we simple return `True` to remove a retweet. """
        return True

    def _twitter_tweet_quote(self, message, attachment=None):
        """
        In the demo module, we return `True` if the user wrote a message.
        If no message is provided, a new retweet will be created.
        """
        if not message:
            return self._twitter_do_retweet()
        return True

    # YOUTUBE

    def _youtube_comment_add(self, comment_id, message, is_edit=False):
        return self._get_new_comment_demo(message)

    def _youtube_comment_fetch(self, next_page_token=False, count=20):
        return {
            'comments': self._get_demo_comments()
        }

    def _get_new_comment_demo(self, message):
        return {
            'id': 5,
            'created_time': '2019-02-10 11:11:11',
            'formatted_created_time': '10/02/2019',
            'likes': {'summary': {'total_count': 0}},
            'from': {
                'name': 'Mitchell Admin',
                'profile_image_url_https': '/web/image/res.users/2/avatar_128'
            },
            'message': message
        }

    # ========================================================
    # MISC / UTILITY
    # ========================================================

    def _get_demo_comments(self):
        """ Return some fake comments. """

        res_partner_2 = self.env.ref('social_demo.res_partner_2', raise_if_not_found=False)
        res_partner_3 = self.env.ref('social_demo.res_partner_3', raise_if_not_found=False)
        res_partner_4 = self.env.ref('social_demo.res_partner_4', raise_if_not_found=False)
        res_partner_10 = self.env.ref('social_demo.res_partner_10', raise_if_not_found=False)

        if not all(res_partner for res_partner in [res_partner_2, res_partner_3, res_partner_4, res_partner_10]):
            return []

        return [{
            'id': 1,
            'created_time': '2019-02-10T09:12:30+0000',
            'formatted_created_time': '10/02/2019',
            'likes': {'summary': {'total_count': 53}},
            'from': {
                'name': 'The Jackson Group',
                'profile_image_url_https': '/web/image/res.partner/%s/avatar_128' % res_partner_10.id,
                'id': 'urn:li:organization:2414183',
            },
            'message': 'Great products!',
            'user_likes': True,
            'comments': {'data': self._get_demo_sub_comments()},
        }, {
            'id': 2,
            'created_time': '2019-02-09T08:12:30+0000',
            'formatted_created_time': '09/02/2019',
            'likes': {'summary': {'total_count': 4}},
            'from': {
                'name': 'Deco Addict',
                'profile_image_url_https': '/web/image/res.partner/%s/avatar_128' % res_partner_2.id,
                'id': 'urn:li:organization:2414183',
            },
            'message': 'Can I get in touch with one of your salesman?',
            'user_likes': True
        }]

    def _get_demo_sub_comments(self):
        res_partner_2 = self.env.ref('social_demo.res_partner_2', raise_if_not_found=False)
        res_partner_3 = self.env.ref('social_demo.res_partner_3', raise_if_not_found=False)
        res_partner_4 = self.env.ref('social_demo.res_partner_4', raise_if_not_found=False)
        res_partner_10 = self.env.ref('social_demo.res_partner_10', raise_if_not_found=False)

        if not all(res_partner for res_partner in [res_partner_2, res_partner_3, res_partner_4, res_partner_10]):
            return []

        return [{
            'id': 3,
            'formatted_created_time': '10/02/2019',
            'created_time': '2019-02-10T10:12:30+0000',
            'likes': {'summary': {'total_count': 21}},
            'from': {
                'name': 'Ready Mat',
                'profile_image_url_https': '/web/image/res.partner/%s/avatar_128' % res_partner_4.id,
                'authorUrn': 'urn:li:organization:2414183',
            },
            'message': 'I agree!'
        }, {
            'id': 4,
            'created_time': '2019-02-10T12:12:30+0000',
            'formatted_created_time': '10/02/2019',
            'likes': {'summary': {'total_count': 13}},
            'from': {
                'name': 'Gemini Furniture',
                'profile_image_url_https': '/web/image/res.partner/%s/avatar_128' % res_partner_3.id,
                'authorUrn': 'urn:li:organization:2414183',
            },
            'message': 'Me too ❤️'
        }]
