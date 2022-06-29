# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo import exceptions
from odoo.addons.knowledge.tests.common import KnowledgeCommonWData
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('knowledge_internals')
class TestKnowledgeArticleFields(KnowledgeCommonWData):
    """ Test fields and their management. """

    @users('employee')
    def test_favorites(self):
        """ Testing the API for toggling favorites. """
        playground_articles = (self.article_workspace + self.workspace_children).with_env(self.env)
        self.assertEqual(playground_articles.mapped('is_user_favorite'), [False, False, False])

        playground_articles[0].write({'favorite_ids': [(0, 0, {'user_id': self.env.uid})]})
        self.assertEqual(playground_articles.mapped('is_user_favorite'), [True, False, False])
        self.assertEqual(playground_articles.mapped('user_favorite_sequence'), [1, -1, -1])
        favorites = self.env['knowledge.article.favorite'].sudo().search([('user_id', '=', self.env.uid)])
        self.assertEqual(favorites.article_id, playground_articles[0])
        self.assertEqual(favorites.sequence, 1)

        playground_articles[1].action_toggle_favorite()
        self.assertEqual(playground_articles.mapped('is_user_favorite'), [True, True, False])
        self.assertEqual(playground_articles.mapped('user_favorite_sequence'), [1, 2, -1])
        favorites = self.env['knowledge.article.favorite'].sudo().search([('user_id', '=', self.env.uid)])
        self.assertEqual(favorites.article_id, playground_articles[0:2])
        self.assertEqual(favorites.mapped('sequence'), [1, 2])

        playground_articles[2].with_user(self.user_employee2).action_toggle_favorite()
        favorites = self.env['knowledge.article.favorite'].sudo().search([('user_id', '=', self.user_employee2.id)])
        self.assertEqual(favorites.article_id, playground_articles[2])
        self.assertEqual(favorites.sequence, 1, 'Favorite: should not be impacted by other people sequence')

    @users('employee')
    def test_fields_edition(self):
        _reference_dt = datetime(2022, 5, 31, 10, 0, 0)
        body_values = [False, '', '<p><br /></p>', '<p>MyBody</p>']

        for index, body in enumerate(body_values):
            self.patch(self.env.cr, 'now', lambda: _reference_dt)
            with freeze_time(_reference_dt):
                article = self.env['knowledge.article'].create({
                    'body': body,
                    'internal_permission': 'write',
                    'name': 'MyArticle,'
                })
            self.assertEqual(article.last_edition_uid, self.env.user)
            self.assertEqual(article.last_edition_date, _reference_dt)

            self.patch(self.env.cr, 'now', lambda: _reference_dt + timedelta(days=1))

            # fields that does not change content
            with freeze_time(_reference_dt + timedelta(days=1)):
                article.with_user(self.user_employee2).write({
                    'name': 'NoContentEdition'
                })
            self.assertEqual(article.last_edition_uid, self.env.user)
            self.assertEqual(article.last_edition_date, _reference_dt)

            # fields that change content
            with freeze_time(_reference_dt + timedelta(days=1)):
                article.with_user(self.user_employee2).write({
                    'body': body_values[(index + 1) if index < (len(body_values)-1) else 0]
                })
                # the with_user() below is necessary for the test to succeed,
                # and that's kind of a bad smell...
                article.with_user(self.user_employee2).flush_model()
            self.assertEqual(article.last_edition_uid, self.user_employee2)
            self.assertEqual(article.last_edition_date, _reference_dt + timedelta(days=1))


@tagged('knowledge_internals', 'knowledge_management')
class TestKnowledgeCommonWDataInitialValue(KnowledgeCommonWData):
    """ Test initial values or our test data once so that other tests do not have
    to do it. """

    def test_initial_values(self):
        """ Ensure all tests have the same basis (global values computed as root) """
        # root
        article_workspace = self.article_workspace
        self.assertTrue(article_workspace.category, 'workspace')
        self.assertEqual(article_workspace.sequence, 999)
        article_shared = self.article_shared
        self.assertTrue(article_shared.category, 'shared')
        self.assertTrue(article_shared.sequence, 998)

        # workspace children
        workspace_children = article_workspace.child_ids
        self.assertEqual(
            workspace_children.mapped('inherited_permission'),
            ['write', 'write']
        )
        self.assertEqual(workspace_children.inherited_permission_parent_id, article_workspace)
        self.assertEqual(
            workspace_children.mapped('internal_permission'),
            [False, False]
        )
        self.assertEqual(workspace_children.root_article_id, article_workspace)
        self.assertEqual(workspace_children.mapped('sequence'), [0, 1])

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_initial_values_as_employee(self):
        """ Ensure all tests have the same basis (user specific computed as
        employee for acl-dependent tests) """
        article_workspace = self.article_workspace.with_env(self.env)
        self.assertTrue(article_workspace.user_has_access)
        self.assertTrue(article_workspace.user_has_write_access)

        article_shared = self.article_shared.with_env(self.env)
        self.assertTrue(article_shared.user_has_access)
        self.assertFalse(article_shared.user_has_write_access)

        article_private = self.article_private_manager.with_env(self.env)
        with self.assertRaises(exceptions.AccessError):
            self.assertFalse(article_private.body)
