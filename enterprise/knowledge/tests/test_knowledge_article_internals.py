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

        first_playground_article = playground_articles[0]
        self.assertFalse(first_playground_article.is_user_favorite)

        first_playground_article.write({'favorite_ids': [(0, 0, {'user_id': self.env.uid})]})
        self.assertEqual(playground_articles.mapped('is_user_favorite'), [True, False, False])
        self.assertEqual(playground_articles.mapped('user_favorite_sequence'), [1, -1, -1])
        favorites = self.env['knowledge.article.favorite'].sudo().search([('user_id', '=', self.env.uid)])
        self.assertEqual(favorites.article_id, first_playground_article)
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

    @users('admin')  # test as admin as this is a technical sync done as sudo
    def test_favorites_active_sync(self):
        """ Make sure the 'is_article_active' is synchronized with the article 'active' field. """

        article_favorites = self.env['knowledge.article.favorite'].create([{
            'user_id': user_id,
            'article_id': self.article_workspace.id,
        } for user_id in (self.user_employee | self.user_employee2).ids])

        self.assertEqual(len(article_favorites), 2)
        self.assertTrue(article_favorites[0].is_article_active)
        self.assertTrue(article_favorites[1].is_article_active)

        self.article_workspace.action_archive()
        self.assertFalse(article_favorites[0].is_article_active)
        self.assertFalse(article_favorites[1].is_article_active)

        self.article_workspace.action_unarchive()
        self.assertTrue(article_favorites[0].is_article_active)
        self.assertTrue(article_favorites[1].is_article_active)

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
            self.assertFalse(article.html_field_history)

            self.patch(self.env.cr, 'now', lambda: _reference_dt + timedelta(days=1))

            # fields that does not change content
            with freeze_time(_reference_dt + timedelta(days=1)):
                article.with_user(self.user_employee2).write({
                    'name': 'NoContentEdition'
                })
            self.assertEqual(article.last_edition_uid, self.env.user)
            self.assertEqual(article.last_edition_date, _reference_dt)
            self.assertFalse(article.html_field_history,
                             'Body did not change: no history should have been created')

            # fields that change content
            body_changes_count = 0
            with freeze_time(_reference_dt + timedelta(days=1)):
                body_value = body_values[(index + 1) if index < (len(body_values)-1) else 0]
                article.with_user(self.user_employee2).write({'body': body_value})
                body_changes_count += 1 if body_value != body and (bool(body_value) or bool(body)) else 0
                # the with_user() below is necessary for the test to succeed,
                # and that's kind of a bad smell...
                article.with_user(self.user_employee2).flush_model()
            self.assertEqual(article.last_edition_uid, self.user_employee2)
            self.assertEqual(article.last_edition_date, _reference_dt + timedelta(days=1))
            if body_changes_count:
                self.assertEqual(len(article.html_field_history["body"]), body_changes_count)
            else:
                self.assertFalse(article.html_field_history)


@tagged('knowledge_internals')
class TestKnowledgeArticleInternals(KnowledgeCommonWData):
    """ Testing model/ORM overrides """

    def test_display_name(self):
        """ Test our custom display_name / name_search / name_create. """

        KnowledgeArticle = self.env['knowledge.article']
        icon_placeholder = KnowledgeArticle._get_no_icon_placeholder()

        KnowledgeArticle.search([]).unlink()  # remove other articles to ease testing
        [article_no_icon, article_icon] = KnowledgeArticle.create([{
            'name': 'Article Without Icon',
        }, {
            'icon': '🚀',
            'name': 'Article With Icon'
        }])

        self.assertEqual(
            article_no_icon.display_name,
            '%s Article Without Icon' % icon_placeholder
        )

        self.assertEqual(
            article_icon.display_name,
            '🚀 Article With Icon'
        )

        # test the 'ilike' operator
        for search_input, expected_articles in zip(
            ['Article With',
             '🚀 Article With',
             '%s Article With' % icon_placeholder,
             '⭐ Test'],
            [article_icon + article_no_icon,
             article_icon,
             article_no_icon,
             KnowledgeArticle]
        ):
            self.assertEqual(
                KnowledgeArticle.name_search(name=search_input, operator='ilike'),
                [(rec.id, rec.display_name) for rec in expected_articles],
                "Not matching for input '%s'" % search_input,
            )

        # test the '=' operator
        for search_input, expected_articles in zip(
            ['Article Without Icon',
             '%s Article Without Icon' % icon_placeholder,
             'Article With Icon',
             '🚀 Article With Icon',
             '🚀 Article With',
             '⭐ Test'],
            [article_no_icon,
             article_no_icon,
             article_icon,
             article_icon,
             KnowledgeArticle,
             KnowledgeArticle]
        ):
            self.assertEqual(
                KnowledgeArticle.name_search(name=search_input, operator='='),
                [(rec.id, rec.display_name) for rec in expected_articles],
                "Not matching for input '%s'" % search_input,
            )

        # now test the name_create custom implementation
        for create_input, (expected_name, expected_icon) in zip(
            ['a',
             'Article Without Icon',
             '%s Article With Icon' % icon_placeholder,
             '🚀 Article With Icon'],
            [('a', False),
             ('Article Without Icon', False),
             ('Article With Icon', icon_placeholder),
             ('Article With Icon', '🚀')]
        ):
            # result of name_create is a display_name
            new_article = KnowledgeArticle.browse(KnowledgeArticle.name_create(create_input)[0])
            self.assertEqual(new_article.name, expected_name)
            self.assertEqual(new_article.icon, expected_icon)


@tagged('knowledge_internals')
class TestKnowledgeArticleUtilities(KnowledgeCommonWData):
    """ Test data oriented utilities and tools for articles. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['knowledge.article'].create({
            'name': 'Child Workspace Item',
            'is_article_item': True,
            'parent_id': cls.article_workspace.id
        })

    @users('employee')
    def test_article_get_valid_parent_options(self):
        child_writable_article = self.workspace_children[1].with_env(self.env)
        res = child_writable_article.get_valid_parent_options(search_term="")
        self.assertEqual(
            sorted(item['id'] for item in res),
            sorted(
                (self.article_workspace + self.workspace_children[0] + self.article_shared + self.shared_children).ids
            ),
            'Should contain: brother, parent and other accessible articles (shared section)'
        )

        root_writable_article = self.article_workspace.with_env(self.env)
        res = root_writable_article.get_valid_parent_options(search_term="")
        self.assertEqual(
            sorted(item['id'] for item in res),
            sorted(
                (self.article_shared + self.shared_children).ids
            ),
            'Should contain: none of descendants, so only other accessible articles (shared section)'
        )

        root_writable_article = self.article_workspace.with_env(self.env)
        res = root_writable_article.get_valid_parent_options(search_term="child")
        self.assertEqual(
            sorted(item['id'] for item in res),
            sorted(
                (self.shared_children).ids
            ),
            'Should contain: none of descendants, so only other accessible articles (shared section), filtered by search term'
        )

        self.assertEqual(
            child_writable_article.get_valid_parent_options(search_term='Item'),
            [],
            'Should contain: nothing as the searched article is an Article Item'
        )

    @users('employee')
    def test_article_get_ancestor_ids(self):
        # Using ids from method docstring for easy matching.
        # Order doesn't matter for this line
        article_2, article_6 = self.env['knowledge.article'].create([
            {'name': 'Article 2'},
            {'name': 'Article 6'}]
        )
        article_4 = self.env['knowledge.article'].create({'name': 'Article 4', 'parent_id': article_2.id})
        article_8 = self.env['knowledge.article'].create({'name': 'Article 8', 'parent_id': article_4.id})
        article_11 = self.env['knowledge.article'].create({'name': 'Article 11', 'parent_id': article_6.id})

        # Use lists to assert correct order (_get_ancestor_ids returns an OrderedSet)
        self.assertEqual(list(article_8._get_ancestor_ids()), [article_4.id, article_2.id])
        self.assertEqual(list((article_8 | article_4)._get_ancestor_ids()), [article_4.id, article_2.id])
        self.assertEqual(list((article_8 | article_11)._get_ancestor_ids()), [article_4.id, article_2.id, article_6.id])


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
        # articles are not ordered by sequence.
        # Make explicit check that first created has sequence 0, second has 1, etc.
        self.assertEqual(self.workspace_children[0].sequence, 0)
        self.assertEqual(self.workspace_children[1].sequence, 1)

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
