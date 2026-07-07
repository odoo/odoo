# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_forum.controllers.website_forum import WebsiteForum
from odoo.addons.website_forum.tests.common import KARMA, TestForumCommon
from odoo.exceptions import AccessError
from odoo.tests.common import HttpCase
from odoo.tools import mute_logger


class TestForumController(TestForumCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._activate_multi_website()
        cls.minimum_karma_allowing_to_post = KARMA['ask']
        cls.forums = cls.env['forum.forum'].create([{
            'name': f'Forum {idx + 2}',
            'karma_ask': cls.minimum_karma_allowing_to_post,
            'website_id': website.id,
        } for idx, website in enumerate(
            (cls.base_website, cls.base_website, cls.base_website, cls.website_2, cls.website_2))])
        cls.forum_1, cls.forum_2, cls.forum_3, cls.forum_1_website_2, cls.forum_2_website_2 = cls.forums
        cls.controller = WebsiteForum()

    def _get_my_other_forums(self, forum):
        """ Get user other forums limited to the forums of the test (self.forums). """
        return self.forums & self.controller._prepare_user_values(forum=forum).get('my_other_forums')

    def forum_post(self, user, forum):
        return self.env['forum.post'].with_user(user).create({
            'content': 'A post ...',
            'forum_id': forum.id,
            'name': 'Post...',
        })

    def test_prepare_user_values_my_other_forum(self):
        """ Test user other forums values (my_other_forums) in various contexts. """
        employee_2_forum_2_post = self.forum_post(self.user_employee_2, self.forum_2)
        employee_2_website_2_forum_2_post = self.forum_post(self.user_employee_2, self.forum_2_website_2)
        for user in (self.user_admin, self.user_employee, self.user_portal, self.user_public):
            with self.with_user(user.login), MockRequest(self.env, website=self.base_website):
                self.assertFalse(self._get_my_other_forums(self.forum_1))
                self.assertFalse(self._get_my_other_forums(None))
                self.assertFalse(self._get_my_other_forums(True))
                if user != self.user_public:
                    self.env.user.karma = self.minimum_karma_allowing_to_post
                    # Like a post on forum 2 and verify that forum 2 is now in "my other forum"
                    employee_2_forum_2_post.favourite_ids += self.env.user
                    self.assertEqual(self._get_my_other_forums(self.forum_1), self.forum_2)
                    self.assertFalse(self._get_my_other_forums(self.forum_2))
                    # Check similarly with posting and also checking that we don't see forum of website 2
                    self.forum_post(self.env.user, self.forum_3)
                    self.forum_post(self.env.user, self.forum_1_website_2)
                    self.assertEqual(self._get_my_other_forums(self.forum_1), self.forum_2 + self.forum_3)
                    self.assertEqual(self._get_my_other_forums(self.forum_2), self.forum_3)
                    self.assertEqual(self._get_my_other_forums(self.forum_3), self.forum_2)
            with self.with_user(user.login), MockRequest(self.env, website=self.website_2):
                self.assertFalse(self._get_my_other_forums(None))
                self.assertFalse(self._get_my_other_forums(True))
                if user != self.user_public:
                    self.assertFalse(self._get_my_other_forums(self.forum_1_website_2))
                    self.assertEqual(self._get_my_other_forums(self.forum_2_website_2), self.forum_1_website_2)
                    employee_2_website_2_forum_2_post.favourite_ids += self.env.user
                    self.assertEqual(self._get_my_other_forums(self.forum_1_website_2), self.forum_2_website_2)

    @mute_logger('odoo.http')
    def test_post_comment_without_subscribed_partner_read_rights(self):
        """ Test restricted portal user comments properly notify subscribers. """
        self.user_employee.karma = KARMA['com_all']
        self.user_portal.karma = 0
        with self.assertRaises(AccessError):
            self.user_employee.partner_id.with_user(self.user_portal).check_access('read')

        forum_slug = self.env['ir.http']._slug(self.base_forum)
        forum_post = self.forum_post(self.user_employee, self.base_forum)
        forum_post.sudo().message_subscribe(self.user_employee.partner_id.ids)
        forum_answer = self.env['forum.post'].with_user(self.user_employee).create({
            'name': 'This is an answer',
            'forum_id': self.base_forum.id,
            'parent_id': forum_post.id,
        })
        forum_answer_slug = self.env['ir.http']._slug(forum_answer)

        self.authenticate(self.user_portal.login, self.user_portal.login)
        data = {
            'post_id': forum_answer.id,
            'comment': 'Answer comment by the portal user',
            'csrf_token': http.Request.csrf_token(self),
        }
        res = self.url_open(
            f'/forum/{forum_slug}/post/{forum_answer_slug}/comment',
            data=data,
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 403)

        self.user_portal.karma = KARMA['com_own']
        res = self.url_open(
            f'/forum/{forum_slug}/post/{forum_answer_slug}/comment',
            data=data,
            allow_redirects=False,
        )
        self.assertEqual(res.status_code, 303)
