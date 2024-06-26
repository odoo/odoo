# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from werkzeug import urls

from odoo import http
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_forum.controllers.website_forum import WebsiteForum
from odoo.addons.website_forum.tests.common import KARMA, TestForumCommon
from odoo.tests import HttpCase


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
            'welcome_message': 'Welcome',
        } for idx, website in enumerate(
            (cls.base_website, cls.base_website, cls.base_website, cls.website_2, cls.website_2))])
        cls.forum_1, cls.forum_2, cls.forum_3, cls.forum_1_website_2, cls.forum_2_website_2 = cls.forums
        cls.controller = WebsiteForum()

    def _get_my_other_forums(self, forum):
        """ Get user other forums limited to the forums of the test (self.forums). """
        return self.forums & self.controller._prepare_user_values(forum=forum).get('my_other_forums')

    def forum_post(self, user, forum, tags=None):
        return self.env['forum.post'].with_user(user).create({
            'content': 'A post ...',
            'forum_id': forum.id,
            'name': 'Post...',
            'tag_ids': tags and tags.mapped('id'),
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

    def _extract_link_and_form_urls(self, url, post_data=None):
        """ Extract URLs from links and form action of the html fetched from the URL along with the final URL. """
        if post_data is not None:
            post_data = {**post_data, 'csrf_token': http.Request.csrf_token(self)}
        response = self.url_open(url, post_data, allow_redirects=True)
        self.assertEqual(response.status_code, 200, f'Get {url} must succeed')
        html = response.text
        urls = {match[0] or match[1]
                  for match in re.findall(r'<a[^>]*\shref="([^"]+)"|<form[^>]*\saction="([^"]+)"', html)}
        urls.add(response.url)  # Add the URL of the page as well
        return urls

    @staticmethod
    def _get_not_starting_with(urls, prefixes):
        """ Returns all the given urls not starting by prefixes. """
        return {url
                for url in urls
                if not any(url.startswith(prefix) for prefix in prefixes)}

    def test_embed_forum(self):
        """ Test embedded forum confinement.

        Concretely, we check that all embed links/actions target the embedded forum
        and that all links/actions of the non-embedded forum targets the non-embedded forum.
        """
        self.forum.karma_ask = 0
        tag_important = self.env['forum.tag'].create({
            'forum_id': self.forum_1.id,
            'name': 'important',
        })
        post = self.forum_post(self.user_admin, self.forum_1, tag_important)
        post_no_answer = self.forum_post(self.user_admin, self.forum_1, tag_important)
        post_answer = self.forum_post(self.user_admin, self.forum_1, tag_important)
        post.child_ids = post_answer
        # Embedded forum can only have links to itself or external sites (ex.: for sharing).
        authorized_prefixes = ['/forum/embed', '#', '?', 'http']

        # Not logged
        not_logged_urls = [
            f'{self.forum_1.id}',
            f'{self.forum_1.id}/{post.id}',
            f'{self.forum_1.id}/page/1',
            f'{self.forum_1.id}/tag/{tag_important.id}/questions',
            f'{self.forum_1.id}/tag/{tag_important.id}/questions/page/1',
            f'{self.forum_1.id}/tag',
            f'{self.forum_1.id}/tag/i',
            f'{self.forum_1.id}/question/{post.id}',
            f'{self.forum_1.id}/{post.id}',
            f'{self.forum_1.id}?search=Test&order=name+asc&filters=all&sorting=last_activity_date+desc',
            f'{self.forum_1.id}?filters=unsolved&search=&sorting=last_activity_date+desc',
            f'{self.forum_1.id}?filters=solved&search=&sorting=last_activity_date+desc',
        ]
        for url_part in not_logged_urls:
            url = f'/forum/embed/{url_part}'
            links = self._extract_link_and_form_urls(url)
            self.assertTrue(links, f"{url}: there is at least one URL")
            # Login links are authorized as long as they redirect to the embedded forum
            login_links = {link for link in links if link.startswith('/web/login')}
            for login_link in login_links:
                query_params = urls.url_parse(login_link).decode_query()
                self.assertTrue({
                    key for key, value in query_params.items()
                    if key == 'redirect' and value.startswith('/forum/embed')
                }, f"{url}: all login URLs redirect to the embedded forum")
            links = links.difference(login_links)
            # Other links must starts with /forum/embed or be 100% relative
            self.assertFalse(
                self._get_not_starting_with(links, authorized_prefixes),
                f"{url}: the form and links URL must be 100% relative or starts with /forum/embed")
            # Non embedded forum must not contain embed URLs
            self.assertFalse(
                any(link for link in self._extract_link_and_form_urls(f'/forum/{url_part}')
                    if link.startswith('/forum/embed')),
                f"{url}: non embed forum doesn't contains embed URL."
            )

        # Logged
        self.authenticate('admin', 'admin')
        post_to_delete = self.forum_post(self.user_admin, self.forum_1, tag_important)
        comment = post.with_context(mail_create_nosubscribe=True).message_post(
            body='comment', message_type='comment', subtype_xmlid='mail.mt_comment')
        logged_urls = [
            *([(up, None) for up in not_logged_urls]),
            (f'{self.forum_1.id}/post/{post.id}/edit', None),
            (f'{self.forum_1.id}/question/{post.id}/edit_answer', None),
            (f'{self.forum_1.id}/ask', None),
            (f'{self.forum_1.id}/new', {'post_name': 'Test', 'content': '<p>test post</p>'}),
            (f'{self.forum_1.id}/{post_no_answer.id}/reply', {'content': '<p>test answer</p>'}),
            (f'{self.forum_1.id}/post/{post.id}/save', {'post_name': 'Test', 'content': '<p>test mod</p>'}),
            (f'{self.forum_1.id}/question/{post.id}/ask_for_close', {}),
            (f'{self.forum_1.id}/question/{post.id}/close', {'post_id': post.id}),
            (f'{self.forum_1.id}/question/{post.id}/reopen', {}),
            (f'{self.forum_1.id}/post/{post.id}/comment', {'post_id': post.id, 'comment': 'comment'}),
            (f'{self.forum_1.id}/post/{post.id}/comment/{comment.id}/convert_to_answer', {}),
        ]
        for url_part, post_data in [
            *logged_urls,
            (f'{self.forum_1.id}/question/{post_to_delete.id}/delete', {}),
        ]:
            url = f'/forum/embed/{url_part}'
            self.assertEqual(
                self._get_not_starting_with(self._extract_link_and_form_urls(url, post_data), authorized_prefixes),
                {'/web'},  # backend
                f"{url}: the form and links URL must be 100% relative or starts with /forum/embed (except /web)")
        # Recreate/unlink some objects to redo the action on the non-embedded version
        post_no_answer.child_ids.unlink()  # to reply again
        post_to_delete = self.forum_post(self.user_admin, self.forum_1, tag_important)
        comment = post.with_context(mail_create_nosubscribe=True).message_post(
            body='comment', message_type='comment', subtype_xmlid='mail.mt_comment')
        # Non embedded forum must not contain embed URLs
        for url_part, post_data in [
            *logged_urls,
            (f'{self.forum_1.id}/question/{post_to_delete.id}/delete', {}),
            (f'{self.forum_1.id}/post/{post.id}/comment/{comment.id}/convert_to_answer', {}),
        ]:
            url = f'/forum/{url_part}'
            self.assertFalse(
                any(link for link in self._extract_link_and_form_urls(url, post_data)
                    if link.startswith('/forum/embed')),
                f"{url}: non embed forum doesn't contains embed URL."
            )
