# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase
from odoo.tests.common import tagged


@tagged('post_install', '-at_install', 'knowledge_public', 'knowledge_tour')
class TestKnowledgePublic(HttpCase):
    """ Test public user search tree rendering. """

    @classmethod
    def setUpClass(cls):
        super(TestKnowledgePublic, cls).setUpClass()
        # remove existing articles to ease tour management
        cls.env['knowledge.article'].with_context(active_test=False).search([]).unlink()

    def test_knowledge_load_more(self):
        """ The goal of this tour is to test the behavior of the 'load more' feature.
        Sub-trees of the articles are loaded max 50 by 50.
        The parent articles are hand-picked with specific index because it allows testing
        that we force the display of the parents of the active article. """

        root_articles = self.env['knowledge.article'].create([{
            'name': 'Root Article %i' % index,
            'website_published': True,
            'category': 'workspace',
        } for index in range(153)])

        children_articles = self.env['knowledge.article'].create([{
            'name': 'Child Article %i' % index,
            'parent_id': root_articles[103].id,
            'website_published': True,
        } for index in range(254)])

        self.env['knowledge.article'].create([{
            'name': 'Grand-Child Article %i' % index,
            'parent_id': children_articles[203].id,
            'website_published': True,
        } for index in range(344)])

        self.start_tour('/knowledge/article/%s' % root_articles[0].id, 'website_knowledge_load_more_tour')

    def test_knowledge_search_flow_public(self):
        """This tour will check that the search bar tree rendering is properly updated"""

        # Create articles to populate published articles tree
        #
        # - My Article
        #       - Child Article
        # - Sibling Article

        # Create a cover for my article
        pixel = 'R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs='
        attachment = self.env['ir.attachment'].create({'name': 'pixel', 'datas': pixel, 'res_model': 'knowledge.cover', 'res_id': 0})
        cover = self.env['knowledge.cover'].create({'attachment_id': attachment.id})

        [my_article, _sibling] = self.env['knowledge.article'].create([{
            'name': 'My Article',
            'parent_id': False,
            'internal_permission': 'write',
            'website_published': True,
            'child_ids': [(0, 0, {
                'name': 'Child Article',
                'internal_permission': 'write',
                'website_published': True,
            })],
            'cover_image_id': cover.id,
        }, {
            'name': 'Sibling Article',
            'internal_permission': 'write',
            'website_published': True,
        }])

        self.start_tour('/knowledge/article/%s' % my_article.id, 'website_knowledge_public_search_tour')
