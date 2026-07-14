# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.website_forum.tests.common import TestForumCommon


class TestForumTag(TestForumCommon):
    def _check_tags_post_counts(self, tags, expected_counts):
        self.assertEqual(tags.mapped('posts_count'), expected_counts)

    def test_tag_posts_count(self):
        self._activate_tags_for_counts()
        test_tags = self.tags[:2]
        self._check_tags_post_counts(test_tags, [0, 0])
        post_tag_1 = self.env['forum.post'].create(
            [{'name': 'Posting about tag 1', 'forum_id': self.forum.id, 'tag_ids': [Command.set([test_tags[0].id])]}]
        )
        self._check_tags_post_counts(test_tags, [1, 0])
        post_tags = self.env['forum.post'].create(
            [{'name': 'Posting with both tags now', 'forum_id': self.forum.id, 'tag_ids': [Command.set(test_tags.ids)]}]
        )
        self._check_tags_post_counts(test_tags, [2, 1])
        post_tag_1.active = False
        self._check_tags_post_counts(test_tags, [1, 1])
        post_tags.close(None)
        self._check_tags_post_counts(test_tags, [0, 0])
