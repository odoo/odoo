# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.knowledge.tests.common import KnowledgeCommonWData, KnowledgeArticlePermissionsCase
from odoo.tests.common import tagged, users, warmup
from odoo.tools import mute_logger


@tagged('knowledge_performance', 'post_install', '-at_install')
class KnowledgePerformanceCase(KnowledgeCommonWData):

    def setUp(self):
        super().setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)

    @users('admin')
    @warmup
    def test_article_copy_batch(self):
        """ Test performance of batch-copying articles, which implies notably
        a descendants checks which might be costly.

        Done as admin as only admin has access to Duplicate button currently."""
        with self.assertQueryCount(admin=59):
            workspace_children = self.workspace_children.with_env(self.env)
            shared = self.article_shared.with_env(self.env)
            _duplicates = (workspace_children + shared).copy_batch()
            self.assertEqual(len(_duplicates), 3)

    @users('employee')
    @warmup
    def test_article_creation_single_shared_grandchild(self):
        """ Test with 2 levels of hierarchy in a private/shared environment """
        with self.assertQueryCount(employee=25):
            _article = self.env['knowledge.article'].create({
                'body': '<p>Hello</p>',
                'name': 'Article in shared',
                'parent_id': self.shared_children[0].id,
            })

        self.assertEqual(_article.category, 'shared')

    @users('employee')
    @warmup
    def test_article_creation_single_workspace(self):
        with self.assertQueryCount(employee=22):
            _article = self.env['knowledge.article'].create({
                'body': '<p>Hello</p>',
                'name': 'Article in workspace',
                'parent_id': self.article_workspace.id,
            })

        self.assertEqual(_article.category, 'workspace')

    @users('employee')
    @warmup
    def test_article_creation_multi_roots(self):
        with self.assertQueryCount(employee=24):
            _article = self.env['knowledge.article'].create([
                {'body': '<p>Hello</p>',
                 'internal_permission': 'write',
                 'name': f'Article {index} in workspace',
                }
                for index in range(10)
            ])

    @users('employee')
    @warmup
    def test_article_creation_multi_shared_grandchild(self):
        with self.assertQueryCount(employee=52):
            _article = self.env['knowledge.article'].create([
                {'body': '<p>Hello</p>',
                 'name': f'Article {index} in workspace',
                 'parent_id': self.shared_children[0].id,
                }
                for index in range(10)
            ])

    @users('employee')
    @warmup
    def test_article_favorite(self):
        with self.assertQueryCount(employee=16):
            shared_article = self.shared_children[0].with_env(self.env)
            shared_article.action_toggle_favorite()

    @users('employee')
    @warmup
    def test_article_get_valid_parent_options(self):
        with self.assertQueryCount(employee=9):
            child_writable_article = self.workspace_children[1].with_env(self.env)
            # don't check actual results, those are tested in ``TestKnowledgeArticleUtilities`` class
            _res = child_writable_article.get_valid_parent_options(search_term="")

    @users('employee')
    @warmup
    def test_article_home_page(self):
        with self.assertQueryCount(employee=15):
            self.env['knowledge.article'].action_home_page()

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    @users('employee')
    @warmup
    def test_article_invite_members(self):
        with self.assertQueryCount(employee=86):
            shared_article = self.shared_children[0].with_env(self.env)
            partners = (self.customer + self.partner_employee_manager + self.partner_employee2).with_env(self.env)
            shared_article.invite_members(partners, 'write')

    @users('employee')
    @warmup
    def test_article_move_to(self):
        before_id = self.workspace_children[0].id
        with self.assertQueryCount(employee=29):  # knowledge: 28
            writable_article = self.workspace_children[1].with_env(self.env)
            writable_article.move_to(parent_id=writable_article.parent_id.id, before_article_id=before_id)

    @users('employee')
    @warmup
    def test_get_user_sorted_articles(self):
        with self.assertQueryCount(employee=9):
            self.env['knowledge.article'].get_user_sorted_articles('')

@tagged('knowledge_performance', 'post_install', '-at_install')
class KnowledgePerformancePermissionCase(KnowledgeArticlePermissionsCase):

    @users('employee')
    @warmup
    def test_user_has_parent_path_access(self):
        """We are testing the performance to access the field user_has_parent_path_access in different situations.
        The arborescence tested here is the one contained inside Readable Root.
        """
        self.assertFalse(self.article_read_contents_children.user_has_access)

        self.article_read_contents_children.sudo()._add_members(self.env.user.partner_id, 'read')
        self.assertTrue(self.article_read_contents_children.with_user(self.env.user).user_has_access)

        # Testing the number of queries depending on the number of ancestors => parent_path
        # Conclusion: No evolution with a higher number of ancestors
        # article_headers[1] => ('TTRPG')
        with self.assertQueryCount(employee=2):
            self.article_headers[1].with_user(self.env.user).user_has_access_parent_path

        # article_read_contents_children => (Child of 'Secret')
        with self.assertQueryCount(employee=2):
            self.article_read_contents_children.with_user(self.env.user).user_has_access_parent_path
        # article_read_desync => (Child of 'Mansion of Terror')
        with self.assertQueryCount(employee=5):
            self.article_read_desync[0].with_user(self.env.user).user_has_access_parent_path

        # Testing evolution in query number depending on the number of tested records
        # Conclusion: Proportional evolution
        # article_read_contents[0] => ('OpenCthulhu')
        with self.assertQueryCount(employee=3):
            self.article_read_contents[0].with_user(self.env.user).user_has_access_parent_path

        # article_read_contents[1:3] => ('Open Paranoïa'), ('Proprietary RPGs')
        with self.assertQueryCount(employee=3):
            for article in self.article_read_contents[1:3]:
                article.with_user(self.env.user).user_has_access_parent_path


@tagged('knowledge_performance', 'post_install', '-at_install')
class KnowledgePerformanceSidebarCase(KnowledgeCommonWData):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.wkspace_grand_children = cls.env['knowledge.article'].create([{
            'name': 'Workspace Grand-Child',
            'parent_id': cls.workspace_children[0].id,
        }] * 2)

    @users('employee')
    @warmup
    def test_article_tree_panel(self):
        with self.assertQueryCount(employee=23):
            self.wkspace_grand_children[0].with_user(self.env.user.id).get_sidebar_articles([self.article_shared.id])

    @users('employee')
    @warmup
    def test_article_tree_panel_w_favorites(self):
        self.env['knowledge.article.favorite'].create([{
            'user_id': self.env.user.id,
            'article_id': article_id
        } for article_id in (self.workspace_children | self.wkspace_grand_children).ids])

        with self.assertQueryCount(employee=20):
            self.wkspace_grand_children[0].with_user(self.env.user.id).get_sidebar_articles([self.article_shared.id])
