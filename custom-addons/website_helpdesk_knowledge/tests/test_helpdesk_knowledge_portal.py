# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.helpdesk.tests.test_helpdesk_portal import TestHelpdeskPortal

@tagged('-at_install', 'post_install')
class TestHelpdeskKnowledgePortalTour(TestHelpdeskPortal):

    def test_helpdesk_knowledge_portal_tour(self):
        website = self.env.ref('website.default_website')
        help_team = self.env['helpdesk.team'].search([('website_id', '=', website.id)], limit=1)
        Article = self.env['knowledge.article']
        Article.search([]).unlink()
        help_article, dummy = Article.create([{
            'name': 'Helpdesk Article',
            'is_published': True,
            'body': 'help',
        }, {
            'name': 'Other Article',
            'is_published': True,
            'body': 'other',
        }])
        dummy = Article.create({
            'name': 'Child Article',
            'is_published': True,
            'parent_id': help_article.id,
        })
        self.assertTrue(bool(help_team), "Check helpdesk team is found.")
        help_team.write({
            'use_website_helpdesk_knowledge': True,
            'website_article_id': help_article.id,
        })
        self.assertTrue(help_team.use_website_helpdesk_form)

        self.env.user = self.env.ref('base.public_user')
        self.start_tour('/', 'access_helpdesk_article_portal_tour')
