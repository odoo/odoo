# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.knowledge.tests.common import KnowledgeCommon
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('knowledge_sequence')
class TestKnowledgeArticleSequence(KnowledgeCommon):
    """ Test sequencing and auto-resequence of articles. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with mute_logger('odoo.models.unlink'):
            cls.env['knowledge.article'].search([]).unlink()

        # HIERARCHY
        # - Existing 1    seq=1
        # - Existing 2    seq=3
        # - Article 1     seq=4
        #   - Article 1.1
        #   - Article 1.2
        #     - Article 1.2.1
        #   - Article 1.3
        # - Article 2     seq=5

        # define starting sequence for root articles
        cls.article_root_noise = cls.env['knowledge.article'].create([
            {'internal_permission': 'write',
             'name': 'Existing1',
             'sequence': 1,
            },
            {'internal_permission': 'write',
             'name': 'Existing2',
             'sequence': 3,
            }
        ])
        cls.article_private = cls._create_private_article(cls, 'Article1', target_user=cls.user_employee)
        cls.article_children = cls.env['knowledge.article'].create([
            {'name': 'Article1.1',
             'parent_id': cls.article_private.id,
            },
            {'name': 'Article1.2',
             'parent_id': cls.article_private.id,
            },
        ])
        cls.article_children += cls.env['knowledge.article'].create([
            {'name': 'Article1.2.1',
             'parent_id': cls.article_children[1].id,
            },
        ])
        cls.article_children += cls.env['knowledge.article'].create([
            {'name': 'Article1.3',
             'parent_id': cls.article_private.id,
            }
        ])
        cls.article_private2 = cls._create_private_article(cls, 'Article2', target_user=cls.user_employee)

        # flush everything to ease resequencing and date-based computation
        cls.env.flush_all()

    @users('employee')
    def test_initial_tree(self):
        # parents
        article_private = self.article_private.with_env(self.env)
        article_children = self.article_children.with_env(self.env)
        article_private2 = self.article_private2.with_env(self.env)

        self.assertFalse(article_private.parent_id)
        self.assertEqual((article_children[0:2] + article_children[3:]).parent_id, article_private)
        self.assertEqual(article_children[2].parent_id, article_children[1])
        self.assertFalse(article_private2.parent_id)
        # ancestors
        self.assertEqual((article_private + article_children).root_article_id, article_private)
        self.assertEqual(article_private2.root_article_id, article_private2)
        # categories
        self.assertEqual(article_private.category, 'private')
        self.assertEqual(set(article_children.mapped('category')), set(['private']))
        self.assertEqual(article_private2.category, 'private')
        # user permission
        self.assertEqual(article_private.user_permission, 'write')
        self.assertEqual(set(article_children.mapped('user_permission')), set(['write']))
        self.assertEqual(article_private2.user_permission, 'write')
        self.assertEqual(article_private.inherited_permission, 'none')
        self.assertEqual(set(article_children.mapped('inherited_permission')), set(['none']))
        self.assertEqual(article_private2.inherited_permission, 'none')
        # sequences
        self.assertSortedSequence(article_private + article_private2)
        self.assertSortedSequence(article_children[0:2] + article_children[3])

    @users('employee')
    def test_resequence_with_move(self):
        """Checking the sequence of the articles"""
        article_private = self.article_private.with_env(self.env)
        article_children = self.article_children.with_env(self.env)
        article_private2 = self.article_private2.with_env(self.env)

        # move last child "Article 1.3" before "Article 1.2"
        last_child = article_children[3]
        last_child.move_to(parent_id=article_private.id, before_article_id=article_children[1].id)
        # expected
        # - Article 1
        #     - Article 1.1
        #     - Article 1.3
        #     - Article 1.2
        #         - Article 1.2.1
        # - Article 6
        self.assertFalse(article_private.parent_id)
        self.assertEqual((article_children[0:2] + article_children[3:]).parent_id, article_private)
        self.assertEqual(article_children[2].parent_id, article_children[1])
        self.assertFalse(article_private2.parent_id)
        self.assertSortedSequence(article_private + article_private2)
        self.assertSortedSequence(article_children[0] + article_children[3] + article_children[1])

        # move "Article 1.2.1" in first position under "Article 1"
        article_children[2].move_to(parent_id=article_private.id, before_article_id=article_children[0].id)
        # expected
        # - Article 1
        #     - Article 1.2.1
        #     - Article 1.1
        #     - Article 1.3
        #     - Article 1.2
        # - Article 6
        self.assertFalse(article_private.parent_id)
        self.assertEqual(article_children.parent_id, article_private)
        self.assertFalse(article_private2.parent_id)
        self.assertSortedSequence(article_private + article_private2)
        self.assertSortedSequence(article_children[2] + article_children[0] + article_children[3] + article_children[1])

        # move "Article 1.1" in last position under "Article 1"
        article_children[0].move_to(parent_id=article_private.id, before_article_id=False)
        # expected
        # - Article 1
        #     - Article 1.2.1
        #     - Article 1.3
        #     - Article 1.2
        #     - Article 1.1
        # - Article 6
        self.assertFalse(article_private.parent_id)
        self.assertEqual(article_children.parent_id, article_private)
        self.assertFalse(article_private2.parent_id)
        self.assertSortedSequence(article_private + article_private2)
        self.assertSortedSequence(article_children[2] + article_children[3] + article_children[1] + article_children[0])

    @users('employee')
    def test_resequence_with_move_noparent(self):
        """ Test move resetting parent_id should also compute sequence """
        article_private = self.article_private.with_env(self.env)
        article_private_child = self.article_children[0].with_env(self.env)
        article_private2 = self.article_private2.with_env(self.env)
        article_root_noise = self.article_root_noise.with_env(self.env)

        self.assertEqual(article_private_child.sequence, 0)
        article_private_child.move_to(category='private')
        self.assertEqual(article_private_child.sequence, 6)
        self.assertSortedSequence(article_root_noise + article_private + article_private2 + article_private_child)
        article_private_child.move_to(before_article_id=self.article_root_noise[0].id)
        self.assertEqual(article_private_child.sequence, 1)
        self.assertSortedSequence(article_private_child + article_root_noise + article_private + article_private2)

    @users('employee')
    def test_resequence_with_parent(self):
        """Checking the sequence of the articles"""
        existing_private = self.article_private.with_env(self.env)
        new_private = self._create_private_article('NewPrivate')
        self.assertFalse(new_private.parent_id, 'Sequencing: no parent should be forced')
        self.assertEqual(new_private.sequence, 6, 'Sequencing: should be placed after Article2, end of "no root" list')

        new_private.write({'parent_id': existing_private.id})
        self.assertEqual(new_private.parent_id, existing_private, 'Sequencing: respect parent choice')
        self.assertEqual(new_private.sequence, 3,
                         'Sequencing: without any forced value, should be set last of all children')

    @users('employee')
    def test_resequence_with_move_before_readonly_article(self):
        """Test resequencing the article with move before readonly article"""
        article_root_noise = self.article_root_noise.with_env(self.env)

        #making 1st article readonly
        article_root_noise[0]._set_internal_permission('read')

        self.assertEqual(article_root_noise[0].sequence, 1)
        self.assertEqual(article_root_noise[1].sequence, 3)
        self.assertSortedSequence(article_root_noise[0] + article_root_noise[1])

        article_root_noise[1].move_to(before_article_id=article_root_noise[0].id)

        self.assertEqual(article_root_noise[0].sequence, 2)
        self.assertEqual(article_root_noise[1].sequence, 1)
        self.assertSortedSequence(article_root_noise[1] + article_root_noise[0])
