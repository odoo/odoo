# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_forum.models.forum_forum import MOST_USED_TAGS_COUNT
from odoo.addons.website_forum.tests.common import TestForumCommon


class TestForumTag(TestForumCommon):
    def setUp(self):
        super().setUp()
        # Reset tags
        forums = self.forum | self.base_forum
        self.env['forum.tag'].search([]).unlink()
        self.env['forum.tag'].create(
            [{'forum_id': forum_id.id, 'name': f'Test Tag {tag_idx}'} for forum_id in forums for tag_idx in range(1, 8)]
        )

    def test_tags_counts_most_used(self):
        posts_per_tag = [(tag_id, post_count) for tag_id, post_count in zip(self.base_forum.tag_ids, range(2, 9))]
        vals_list = [
            {'forum_id': self.base_forum.id, 'name': 'A post', 'content': 'A content', 'tag_ids': [tag_id.id]}
            for tag_id, post_count in posts_per_tag
            for __ in range(post_count)
        ]
        self.env['forum.post'].create(vals_list)
        self.env['forum.tag'].flush_model()

        self.assertListEqual(
            self.base_forum.tag_most_used_ids.ids,
            [tag_id.id for tag_id, _ in reversed(posts_per_tag[-MOST_USED_TAGS_COUNT:])],
        )
        self.assertEqual(self.base_forum.tag_unused_ids, self.env['forum.tag'])

    def test_tags_counts_unused(self):
        used_tag = self.forum.tag_ids[5]
        self.env['forum.post'].create(
            [
                {'forum_id': tag_id.forum_id.id, 'tag_ids': [tag_id.id], 'name': 'A post', 'content': 'A content'}
                for tag_id in (used_tag | self.base_forum.tag_ids)
            ]
        )
        self.env['forum.tag'].flush_model()

        # trigger batch compute
        __ = (self.forum | self.base_forum).tag_most_used_ids

        self.assertEqual(self.forum.tag_most_used_ids, used_tag)
        self.assertEqual(self.forum.tag_unused_ids, self.forum.tag_ids - used_tag)

        self.assertEqual(self.base_forum.tag_most_used_ids, self.base_forum.tag_ids[:MOST_USED_TAGS_COUNT])
        self.assertEqual(self.base_forum.tag_unused_ids, self.env['forum.tag'])
