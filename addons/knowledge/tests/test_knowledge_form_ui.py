# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests.common import tagged, HttpCase


@tagged('post_install', '-at_install', 'knowledge', 'knowledge_tour')
class TestKnowledgeUI(HttpCase):
    @classmethod
    def setUpClass(cls):
        super(TestKnowledgeUI, cls).setUpClass()
        # remove existing articles to ease tour management
        cls.env['knowledge.article'].search([]).unlink()

    def test_knowledge_main_flow(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        # as the knowledge.article#_resequence method is based on write date
        # force the write_date to be correctly computed
        # otherwise it always returns the same value as we are in a single transaction
        self.patch(self.env.cr, 'now', fields.Datetime.now)

        self.start_tour('/web', 'knowledge_main_flow_tour', login='admin', step_delay=100)

        # check our articles were correctly created
        # with appropriate default values (section / internal_permission)
        private_article = self.env['knowledge.article'].search([('name', '=', 'My Private Article')])
        self.assertTrue(bool(private_article))
        self.assertEqual(private_article.category, 'private')
        self.assertEqual(private_article.internal_permission, 'none')

        workspace_article = self.env['knowledge.article'].search([('name', '=', 'My Workspace Article')])
        self.assertTrue(bool(workspace_article))
        self.assertEqual(workspace_article.category, 'workspace')
        self.assertEqual(workspace_article.internal_permission, 'write')

        children_workspace_articles = workspace_article.child_ids.sorted('sequence')
        self.assertEqual(len(children_workspace_articles), 2)

        child_article_1 = children_workspace_articles.filtered(
            lambda article: article.name == 'Child Article 1')
        child_article_2 = children_workspace_articles.filtered(
            lambda article: article.name == 'Child Article 2')

        # as we re-ordered children, article 2 should come first
        self.assertEqual(children_workspace_articles[0], child_article_2)
        self.assertEqual(children_workspace_articles[1], child_article_1)

        # workspace article should have one partner invited on it
        invited_member = workspace_article.article_member_ids
        self.assertEqual(len(invited_member), 1)
        invited_partner = invited_member.partner_id
        self.assertEqual(len(invited_partner), 1)
        self.assertEqual(invited_partner.name, 'micheline@knowledge.com')
        self.assertEqual(invited_partner.email, 'micheline@knowledge.com')
        # check that the partner received an invitation link
        invitation_message = self.env['mail.message'].search([
            ('partner_ids', 'in', invited_partner.id)
        ])
        self.assertEqual(len(invitation_message), 1)
        self.assertIn(
            workspace_article._get_invite_url(invited_partner),
            invitation_message.body
        )

        # as we re-ordered our favorites, private article should come first
        article_favorites = self.env['knowledge.article.favorite'].search([])
        self.assertEqual(len(article_favorites), 2)
        self.assertEqual(article_favorites[0].article_id, private_article)
        self.assertEqual(article_favorites[1].article_id, workspace_article)

    def test_knowledge_pick_emoji(self):
        """This tour will check that the emojis of the form view are properly updated
           when the user picks an emoji from an emoji picker."""
        self.start_tour('/web', 'knowledge_pick_emoji_tour', login='admin', step_delay=100)
