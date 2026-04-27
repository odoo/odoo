# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html

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
        cls.attachment = cls.env['ir.attachment'].create({
            'name': 'pixel',
            'datas': 'R0lGODlhAQABAIAAAP///wAAACwAAAAAAQABAAACAkQBADs=',
            'res_model': 'knowledge.cover',
            'res_id': 0
        })
        cls.cover = cls.env['knowledge.cover'].create({
            'attachment_id': cls.attachment.id
        })

    def test_knowledge_load_more(self):
        """ The goal of this tour is to test the behavior of the 'load more' feature.
        Sub-trees of the articles are loaded max 50 by 50.
        The parent articles are hand-picked with specific index because it allows testing
        that we force the display of the parents of the active article. """

        root_article = self.env['knowledge.article'].create({
            'name': 'Root Article 0',
            'website_published': True,
            'category': 'workspace',
        })

        children_articles = self.env['knowledge.article'].create([{
            'name': 'Child Article %i' % index,
            'parent_id': root_article.id,
            'website_published': True,
        } for index in range(254)])

        self.env['knowledge.article'].create([{
            'name': 'Grand-Child Article %i' % index,
            'parent_id': children_articles[203].id,
            'website_published': True,
        } for index in range(344)])

        self.start_tour('/knowledge/article/%s' % root_article.id, 'website_knowledge_load_more_tour')

    def test_knowledge_meta_tags(self):
        """ Check that the meta tags set on the article's frontend page showcase the article content.
            The description meta tag should be a small extract from the article and should exclude
            special blocs such as the table of content, the files, the embedded views, the videos, etc."""

        article = self.env['knowledge.article'].create({
            'icon': '💬',
            'name': 'Odoo Experience',
            'body': '''
                <h1>What is Odoo Experience?</h1>
                <div data-embedded="tableOfContent">Hello</div>
                <p>Odoo Experience is our largest event, taking place once a year.</p>
                <p>It brings together all members of the Odoo sphere, including partners, customers and open source software fans.</p>
            ''',
            'cover_image_id': self.cover.id,
            'website_published': True,
        })

        # Check that the special blocs are excluded from the summary
        self.assertEqual(
            article.summary,
            'What is Odoo Experience? Odoo Experience is our largest event, taking place once a year. It brings t...')

        res = self.url_open(f'/knowledge/article/{article.id}')
        root_html = html.fromstring(res.content)

        # Check the meta tag of the article frontend page:

        # Standard meta tags:
        self.assertEqual(
            root_html.xpath('/html/head/meta[@name="description"]/@content'),
            ['What is Odoo Experience? Odoo Experience is our largest event, taking place once a year. It brings t...'])

        # OpenGraph meta tags:
        self.assertEqual(
            root_html.xpath('/html/head/meta[@property="og:type"]/@content'),
            ['article'])
        self.assertEqual(
            root_html.xpath('/html/head/meta[@property="og:title"]/@content'),
            ['💬 Odoo Experience'])
        self.assertEqual(
            root_html.xpath('/html/head/meta[@property="og:description"]/@content'),
            ['What is Odoo Experience? Odoo Experience is our largest event, taking place once a year. It brings t...'])
        self.assertEqual(
            root_html.xpath('/html/head/meta[@property="og:image"]/@content'),
            [article.get_base_url() + article.cover_image_url])

        # X meta tags:
        self.assertEqual(
            root_html.xpath('/html/head/meta[@name="twitter:title"]/@content'),
            ['💬 Odoo Experience'])
        self.assertEqual(
            root_html.xpath('/html/head/meta[@name="twitter:description"]/@content'),
            ['What is Odoo Experience? Odoo Experience is our largest event, taking place once a year. It brings t...'])
        self.assertEqual(
            root_html.xpath('/html/head/meta[@name="twitter:card"]/@content'),
            ['summary_large_image'])
        self.assertEqual(
            root_html.xpath('/html/head/meta[@name="twitter:image"]/@content'),
            [article.get_base_url() + article.cover_image_url])

    def test_knowledge_search_flow_public(self):
        """This tour will check that the search bar tree rendering is properly updated"""

        # Create articles to populate published articles tree
        #
        # - My Article
        #       - Child Article
        # - Sibling Article

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
            'cover_image_id': self.cover.id,
        }, {
            'name': 'Sibling Article',
            'internal_permission': 'write',
            'website_published': True,
        }])

        self.start_tour('/knowledge/article/%s' % my_article.id, 'website_knowledge_public_search_tour')
