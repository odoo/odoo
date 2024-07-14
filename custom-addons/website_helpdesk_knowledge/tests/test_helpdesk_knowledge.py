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
