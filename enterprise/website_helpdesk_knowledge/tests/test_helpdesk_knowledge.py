# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError

from odoo.tests import tagged, HttpCase
from odoo.addons.helpdesk.tests.common import HelpdeskCommon

@tagged('-at_install', 'post_install')
class TestHelpdeskKnowledgeTour(HttpCase, HelpdeskCommon):

    def test_helpdesk_knowledge_article_constrains(self):
        Article = self.env['knowledge.article']
        Article.search([]).unlink()
        help_article, other_article = Article.create([{
            'name': 'Helpdesk Article',
            'is_published': True,
            'body': 'help',
        }, {
            'name': 'Other Article',
            'is_published': True,
            'body': 'other',
        }])
        self.test_team.write({
            'use_website_helpdesk_knowledge': True,
            'website_article_id': help_article.id,
        })
        with self.assertRaises(ValidationError):
            help_article.write({
                'is_published': False,
            })
        with self.assertRaises(ValidationError):
            help_article.write({
                'parent_id': other_article.id,
            })
        with self.assertRaises(ValidationError):
            help_article.write({
                'active': False,
            })

    def test_latest_articles(self):
        # We first create 7 different articles for our knowledge centre
        knowledge_articles = self.env['knowledge.article'].create([{
            'name': f'This is article number {article_record}',
            'is_published': True,
            'body': f'Believe it or not, this is the body of article number {article_record}',
        } for article_record in range(1, 8)])

        # Then we need to create some users which will favorite the knowledge articles (28 users because we need one for each favorite)
        forum_users = self.env['res.users'].create([{
            'name': f"Theodore the {index}'th",
            'login': f'usr{index}',
            'email': f'user{index}@example.com',
        } for index in range(0, 28)])

        # Finally it's time to create the favorite records for each of the knowledge articles
        forum_user_ids = forum_users.ids
        self.env['knowledge.article.favorite'].create([{
            'article_id': article_value.id,
            'user_id': forum_user_ids.pop(),
        } for index, article_value in enumerate(knowledge_articles) for _ in range(index+1)])

        self.test_team.write({
            'use_website_helpdesk_knowledge': True,
        })

        self.assertEqual(self.test_team.website_latest_articles, knowledge_articles[6:1:-1], 'The latest articles should be the ones with the most favourites, in this case the last 5 from last to first')

    def test_helpdesk_knowledge_article_only_list_linked_articles(self):
        """
        Test Case:
        ==========
        - have multiple published articles
        - check that only the linked article  or its children are proposed as "latest article" for the team
        """
        Article = self.env['knowledge.article']
        Article.search([]).unlink()
        help_article, _unused = Article.create([{
            'name': 'Helpdesk Article',
            'is_published': True,
            'body': 'help',
        }, {
            'name': 'Other Article',
            'is_published': True,
            'body': 'other',
        }])
        child_article = Article.create({
            'name': 'Child Article',
            'is_published': True,
            'parent_id': help_article.id,
        })
        self.test_team.write({
            'use_website_helpdesk_knowledge': True,
            'website_article_id': help_article.id,
        })
        self.assertEqual(self.test_team.website_latest_articles, help_article + child_article)
