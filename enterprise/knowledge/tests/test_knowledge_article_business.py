# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from datetime import datetime, timedelta
from lxml import html
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.knowledge.tests.common import KnowledgeCommon, KnowledgeCommonWData
from odoo.exceptions import UserError
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('knowledge_internals', 'knowledge_management')
class KnowledgeCommonBusinessCase(KnowledgeCommonWData):

    @classmethod
    def setUpClass(cls):
        """ Add some hierarchy to have mixed rights tests """
        super().setUpClass()

        # - Private         seq=997   private      none    (manager-w+)
        #   - Child1        seq=0     "            "
        # - Shared          seq=998   shared       none    (admin-w+,employee-r+,manager-r+)
        #   - Child1        seq=0     "            "       (employee-w+)
        #   - Child2        seq=0     "            "       (portal-r+)
        #   - Child3        seq=0     "            "       (admin-w+,employee-n-)
        # - Playground      seq=999   workspace    w+
        #   - Child1        seq=0     "            "
        #     - Gd Child1
        #     - Gd Child2
        #       - GdGd Child1
        #   - Child2        seq=1     "            "
        #     - Gd Child1
        #       - GdGd Child2

        cls.shared_children += cls.env['knowledge.article'].sudo().create([
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_admin.id,
                        'permission': 'write',
                       }),
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'none',
                       }),
             ],
             'internal_permission': False,
             'name': 'Shared Child3',
             'parent_id': cls.article_shared.id,
            },
        ])

        # to test descendants computation, add some sub children
        cls.wkspace_grandchildren = cls.env['knowledge.article'].create([
            {'name': 'Grand Children of workspace',
             'parent_id': cls.workspace_children[0].id,
            },
            {'name': 'Grand Children of workspace',
             'parent_id': cls.workspace_children[0].id,
            },
            {'name': 'Grand Children of workspace',
             'parent_id': cls.workspace_children[1].id,
            }
        ])
        cls.wkspace_grandgrandchildren = cls.env['knowledge.article'].create([
            {'name': 'Grand Grand Children of workspace',
             'parent_id': cls.wkspace_grandchildren[1].id,
            },
            {'name': 'Grand Children of workspace',
             'parent_id': cls.wkspace_grandchildren[2].id,
            },
        ])
        cls.env.flush_all()


@tagged('knowledge_internals', 'knowledge_management')
class TestKnowledgeArticleBusiness(KnowledgeCommonBusinessCase):
    """ Test business API and main tools or helpers methods. """

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_create(self):
        """ Testing the helper to create articles with right values. """
        Article = self.env['knowledge.article']
        article = self.article_workspace.with_env(self.env)
        readonly_article = self.article_shared.with_env(self.env)

        _title = 'Fthagn'
        new = Article.article_create(title=_title, parent_id=False, is_private=False)
        self.assertMembers(new, 'write', {self.env.user.partner_id: 'write'}) # With the visibility we add directly the user as member
        self.assertEqual(new.body, f'<h1>{_title}</h1>')
        self.assertEqual(new.category, 'workspace')
        self.assertEqual(new.name, _title)
        self.assertFalse(new.parent_id)
        self.assertEqual(new.sequence, self._base_sequence + 1)

        _title = 'Fthagn, but private'
        private = Article.article_create(title=_title, parent_id=False, is_private=True)
        self.assertMembers(private, 'none', {self.env.user.partner_id: 'write'})
        self.assertEqual(private.category, 'private')
        self.assertFalse(private.parent_id)
        self.assertEqual(private.sequence, self._base_sequence + 2)

        _title = 'Fthagn, but with parent (workspace)'
        child = Article.article_create(title=_title, parent_id=article.id, is_private=False)
        self.assertMembers(child, False, {})
        self.assertEqual(child.category, 'workspace')
        self.assertEqual(child.parent_id, article)
        self.assertEqual(child.sequence, 2, 'Already two children existing')

        _title = 'Fthagn, but with parent (private): forces private'
        child_private = Article.article_create(title=_title, parent_id=private.id, is_private=False)
        self.assertMembers(child_private, False, {})
        self.assertFalse(child_private.article_member_ids)
        self.assertEqual(child_private.category, 'private')
        self.assertEqual(child_private.parent_id, private)
        self.assertEqual(child_private.sequence, 0)

        _title = 'Fthagn, but private under non private: cracboum'
        with self.assertRaises(exceptions.ValidationError):
            Article.article_create(title=_title, parent_id=article.id, is_private=True)

        _title = 'Fthagn, but with parent read only: cracboum'
        with self.assertRaises(exceptions.AccessError):
            Article.article_create(title=_title, parent_id=readonly_article.id, is_private=False)

        # Test fix: cannot create under unwritable parent even if a sequence is set.
        with self.assertRaises(exceptions.AccessError):
            Article.create({
                "name": "I've a sequence, can I bypass security ? Was internal Right ? no more !",
                "parent_id": readonly_article.id,
                "sequence": 10
            })

        private_nonmember = Article.sudo().create({
            'article_member_ids': [
                (0, 0, {'partner_id': self.partner_employee2.id,
                        'permission': 'write',}),
                (0, 0, {'partner_id': self.partner_employee.id,
                        'permission': 'none',}),
            ],
            'internal_permission': 'none',
            'name': 'AdminPrivate',
        })
        # If no body given at create, make it reflect article title.
        self.assertEqual(private_nonmember.body, "<h1>AdminPrivate</h1>")
        _title = 'Fthagn, but with parent private none: cracboum'
        with self.assertRaises(exceptions.AccessError):
            Article.article_create(title=_title, parent_id=private_nonmember.id, is_private=False)

    @users('employee')
    def test_article_get_sidebar_articles(self):
        """ Testing the main access point for the sidebar. """
        playground_root = self.article_workspace.with_env(self.env)
        playground_children = self.workspace_children.with_env(self.env)
        shared_root = self.article_shared.with_env(self.env)
        # all articles are folded, expect only roots and no favorite
        sidebar_articles = self.env['knowledge.article'].get_sidebar_articles()
        self.assertListEqual(sidebar_articles['favorite_ids'], [])
        self.assertListEqual([article['id'] for article in sidebar_articles['articles']], (shared_root + playground_root).ids)
        # add both articles as favorite, favorite_ids should be populated
        (playground_root + shared_root).action_toggle_favorite()
        sidebar_articles = self.env['knowledge.article'].get_sidebar_articles()
        self.assertListEqual(sidebar_articles['favorite_ids'], (playground_root + shared_root).ids)
        # remove access to shared article, favorite_ids should have one element and only playground should be kept
        shared_root.sudo()._add_members(self.partner_employee, 'none', True)
        sidebar_articles = self.env['knowledge.article'].get_sidebar_articles()
        self.assertListEqual(sidebar_articles['favorite_ids'], playground_root.ids)
        self.assertListEqual([article['id'] for article in sidebar_articles['articles']], playground_root.ids)
        # unfold playground, should contain its children
        sidebar_articles = self.env['knowledge.article'].get_sidebar_articles(playground_root.ids)
        self.assertListEqual(sidebar_articles['favorite_ids'], [playground_root.id])
        self.assertListEqual([article['id'] for article in sidebar_articles['articles']], (playground_children + playground_root).ids)

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    @users('employee')
    def test_article_invite_members(self):
        """ Test inviting members API. Create a hierarchy of 3 shared articles
        and check privilege is not granted below invited articles.

        # - Shared          seq=998   shared       none    (admin-w+,employee-r+,manager-r+)
        #   - Child1        seq=0     "            "       (employee-w+)
        #      - Gd Child1            "            "       (manager-w+,employee-r+)
        #        - GdGd Child1        "            "       (employee-w+)
        #      - Gd Child2            "            "       (employee-w+)
        #   - Child2        seq=0     "            "       (portal-r+)
        #   - Child3        seq=0     "            "       (admin-w+,employee-n-)

        """
        direct_child_read, direct_child_write = self.env['knowledge.article'].sudo().create([
            {'article_member_ids': [
                (0, 0, {'partner_id': self.partner_employee_manager.id,
                        'permission': 'write',
                       }),
                (0, 0, {'partner_id': self.partner_employee.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': False,
             'name': 'Shared Readonly Child (should not propagate)',
             'parent_id': self.shared_children[0].id,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': self.partner_employee.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': False,
             'name': 'Shared Writable Child (propagate is ok)',
             'parent_id': self.shared_children[0].id,
            }
        ]).with_env(self.env)
        grand_child = self.env['knowledge.article'].sudo().create({
            'article_member_ids': [
                (0, 0, {'partner_id': self.partner_employee.id,
                        'permission': 'write',
                       }),
            ],
            'internal_permission': 'read',
            'name': 'Shared GrandChild (blocked by readonly parent, should not propagate)',
            'parent_id': direct_child_read.id,
        }).with_env(self.env)

        shared_article = self.shared_children[0].with_env(self.env)
        self.assertMembers(shared_article, False,
                           {self.partner_employee: 'write'})
        self.assertMembers(direct_child_read, False,
                           {self.partner_employee_manager: 'write',
                            self.partner_employee: 'read'})
        self.assertMembers(direct_child_write, False,
                           {self.partner_employee: 'write'})
        self.assertMembers(grand_child, 'read',
                           {self.partner_employee: 'write'})

        # invite a mix of shared and internal people
        partners = (self.customer + self.partner_employee_manager + self.partner_employee2).with_env(self.env)
        with self.mock_mail_gateway():
            shared_article.invite_members(partners, 'write')
        self.assertMembers(shared_article, False,
                           {self.partner_employee: 'write',
                            self.customer: 'write',
                            self.partner_employee_manager: 'write',
                            self.partner_employee2: 'write'},
                           msg='Invite: should add rights for people')
        self.assertMembers(direct_child_read, False,
                           {self.partner_employee: 'read',
                            self.customer: 'none',
                            self.partner_employee_manager: 'write',
                            self.partner_employee2: 'none'},
                           msg='Invite: rights should be stopped for non writable children')
        self.assertMembers(direct_child_write, False,
                           {self.partner_employee: 'write'},
                           msg='Invite: writable child should not be impacted')
        self.assertMembers(grand_child, 'read',
                           {self.partner_employee: 'write'},
                           msg='Invite: descendants should not be impacted')

        # check access is effectively granted
        shared_article.with_user(self.user_employee2).check_access('write')
        shared_article.with_user(self.user_customer).check_access('write')
        direct_child_write.with_user(self.user_employee2).check_access('write')
        direct_child_write.with_user(self.user_customer).check_access('write')
        direct_child_read.browse().with_user(self.user_employee2).check_access('read')
        with self.assertRaises(exceptions.AccessError,
                               msg='Invite: access should have been blocked'):
            direct_child_read.with_user(self.user_employee2).check_access('read')
        grand_child.browse().with_user(self.user_employee2).check_access('read')
        with self.assertRaises(exceptions.AccessError,
                               msg='Invite: access should have been blocked'):
            grand_child.with_user(self.user_employee2).check_access('read')

        # employee2 is downgraded, employee_manager is removed
        with self.mock_mail_gateway():
            shared_article.invite_members(partners[2], 'read')
        with self.mock_mail_gateway():
            shared_article.invite_members(partners[1], 'none')

        self.assertMembers(shared_article, False,
                           {self.partner_employee: 'write',
                            self.customer: 'write',
                            self.partner_employee_manager: 'none',
                            self.partner_employee2: 'read'})

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_article_invite_members_rights(self):
        """ Testing trying to bypass granted privilege: inviting people require
        write access. """
        article_shared = self.article_shared.with_env(self.env)

        partners = (self.customer + self.partner_employee_manager + self.partner_employee2).with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg='Invite: cannot invite with read permission'):
            article_shared.invite_members(partners, 'write')

        with self.assertRaises(exceptions.AccessError,
                               msg='Invite: cannot try to reject people with read permission'):
            article_shared.invite_members(partners, 'none')

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.mail.models.mail_mail')
    @users('employee')
    def test_article_invite_members_non_accessible_children(self):
        """ Test that user cannot give access to non-accessible children article
        when inviting people.

        # Private Parent        private    none     (employee-w+)
        # - Child1              "          write    (employee-no)
        #   - Gd Child1
        # - Child2              "          write    (employee-r+)
        #   - Gd Child1
        # - Child3              "          "        "
        #   - Gd Child1
        """
        private_parent = self.env['knowledge.article'].create([{
            'article_member_ids': [(0, 0, {
                'partner_id': self.partner_employee.id,
                'permission': 'write',
                })
            ],
            'internal_permission': 'none',
            'name': 'Private parent',
            'parent_id': False,
        }])
        child_no_access, child_read_access, child_write_access = self.env['knowledge.article'].sudo().create([
            {'article_member_ids': [(0, 0, {
                'partner_id': self.partner_employee.id,
                'permission': 'none',
                })
             ],
             'internal_permission': 'write',
             'name': 'Shared No Access Child (should not propagate)',
             'parent_id': private_parent.id,
            },
            {'article_member_ids': [(0, 0, {
                'partner_id': self.partner_employee.id,
                'permission': 'read',
                })
             ],
             'internal_permission': 'write',
             'name': 'Shared Read Child (should not propagate)',
             'parent_id': private_parent.id,
            },
            {'internal_permission': False,
             'name': 'Shared Inherited Write Child (should propagate)',
             'parent_id': private_parent.id,
            }
        ]).with_env(self.env)
        grandchild_no_access, grandchild_read_access, grandchild_write_access = self.env['knowledge.article'].sudo().create([
            {'internal_permission': False,
             'name': 'Shared inherit No access GrandChild (should not propagate)',
             'parent_id': child_no_access.id,
            },
            {'internal_permission': False,
             'name': 'Shared inherit read GrandChild (should not propagate)',
             'parent_id': child_read_access.id,
            },
            {'internal_permission': False,
             'name': 'Shared inherit write GrandChild (should propagate)',
             'parent_id': child_write_access.id,
            }
        ]).with_env(self.env)

        partners = self.partner_employee_manager.with_env(self.env)
        with self.mock_mail_gateway():
            private_parent.invite_members(partners, 'read')

        # Manager got read on article
        self.assertMembers(private_parent, 'none', {
            self.partner_employee: 'write',
            self.partner_employee_manager: 'read'
        })

        # CHILDREN
        # Manager got none on child_read_access
        self.assertMembers(child_read_access, 'write', {
            self.partner_employee: 'read',
            self.partner_employee_manager: 'none'
        })

        # Manager got none on child_no_access
        self.assertMembers(child_no_access, 'write', {
            self.partner_employee: 'none',
            self.partner_employee_manager: 'none'
        })

        # Manager got inherited read on child_write_access
        self.assertMembers(child_write_access, False, {})
        self.assertTrue(child_write_access.user_has_write_access)
        self.assertTrue(child_write_access.with_user(self.user_employee_manager).user_has_access)

        # GRAND CHILDREN
        # Manager got inherited none on child_read_access and Employee still have inherited member access
        self.assertMembers(grandchild_read_access, False, {})
        self.assertTrue(grandchild_read_access.user_has_access)
        with self.assertRaises(exceptions.AccessError):
            grandchild_read_access.with_user(self.user_employee_manager).body  # Acls should trigger AccessError

        # Manager got inherited none on child_no_access and Employee still have no access
        self.assertMembers(grandchild_no_access, False, {})
        with self.assertRaises(exceptions.AccessError):
            grandchild_no_access.body # Acls should trigger AccessError
        with self.assertRaises(exceptions.AccessError):
            grandchild_no_access.with_user(self.user_employee_manager).body  # Acls should trigger AccessError

        # Manager got inherited read on grandchild_write_access and Employee still have write access
        self.assertMembers(grandchild_write_access, False, {})
        self.assertTrue(grandchild_write_access.user_has_write_access)
        self.assertTrue(grandchild_write_access.with_user(self.user_employee_manager).user_has_access)

    @users('employee')
    def test_article_toggle_favorite(self):
        """ Testing the API for toggling favorites. """
        playground_articles = (self.article_workspace + self.workspace_children).with_env(self.env)
        self.assertEqual(playground_articles.mapped('is_user_favorite'), [False, False, False])

        playground_articles[0].action_toggle_favorite()
        playground_articles.invalidate_model(['is_user_favorite'])
        self.assertEqual(playground_articles.mapped('is_user_favorite'), [True, False, False])

        # correct uid-based computation
        playground_articles_asmanager = playground_articles.with_user(self.user_employee_manager)
        self.assertEqual(playground_articles_asmanager.mapped('is_user_favorite'), [False, False, False])

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models.unlink')
    @users('employee')
    def test_article_make_private(self):
        """ Testing the API that makes an article 'private'. Making an article
        private generally:
          - sets internal_permission 'none';
          - sets current environment user as only write member;

        A lot of extra post-processing is applied, see ``KnowledgeArticle.
        _move_and_make_private()`` for details.

        Specific setup for this test
        # - Playground                workspace    w+    (customer-r+)
        #   - Child1                  "            "     (customer-r+)
        #     - ReadMemb GrandChild   "            w+    (employee-r+)
        #     - Gd Child1             "            "
        #     - Gd Child2             "            "
        #       - GdGd Child1         "            "
        #   - Child2                  "            "
        #     - Gd Child1             "            "
        #       - GdGd Child          "            "
        #   - ReadMember Child        "            w+    (employee-r+)
        #   - ReadInternal Child      "            r+    (employee2-w+)
        #   - Hidden Child            "            w+    (employee-no)
        """
        article_workspace = self.article_workspace.with_env(self.env)
        workspace_children = self.workspace_children.with_env(self.env)
        wkspace_grandchildren = self.wkspace_grandchildren.with_env(self.env)
        wkspace_grandgrandchildren = self.wkspace_grandgrandchildren.with_env(self.env)

        # add an additional member on 'article_workspace' and one of its children for further checks
        (self.article_workspace + self.workspace_children[0]).write({
            'article_member_ids': [(0, 0, {
                'partner_id': self.customer.id,
                'permission': 'read',
            })]
        })

        # add 4 extra articles for further checks
        # - one to which 'employee' only has 'read' access (as member)
        # - one to which 'employee' only has 'read' access (internal)
        # - one invisible, "employee2" has access to that one in write mode
        # - one to which 'employee' only has 'read' access (as member) as grandchild (descendants testing)
        [wkspace_child_read_member_access,
         wkspace_child_read_internal_access,
         wkspace_child_no_access,
         wkspace_grandchild_read_member_access] = self.env['knowledge.article'].sudo().create([
            {
                'article_member_ids': [(0, 0, {
                    'partner_id': self.partner_employee.id,
                    'permission': 'read',
                })],
                'internal_permission': 'write',
                'name': 'Read Member Child',
                'parent_id': article_workspace.id,
            }, {
                'article_member_ids': [(0, 0, {
                    'partner_id': self.partner_employee2.id,
                    'permission': 'write',
                })],
                'internal_permission': 'read',
                'name': 'Read Internal Child',
                'parent_id': article_workspace.id,
            }, {
                'article_member_ids': [(0, 0, {
                    'partner_id': self.partner_employee.id,
                    'permission': 'none',
                })],
                'internal_permission': 'write',
                'name': 'Hidden Child',
                'parent_id': article_workspace.id,
            }, {
                'article_member_ids': [(0, 0, {
                    'partner_id': self.partner_employee.id,
                    'permission': 'read',
                })],
                'internal_permission': 'write',
                'name': 'Read Member GrandChild',
                'parent_id': workspace_children[0].id,
            }
        ])
        with self.assertRaises(exceptions.AccessError):
            wkspace_child_no_access.with_env(self.env).body
        article_workspace._move_and_make_private()

        # 1. main article was correctly moved to private
        self.assertEqual(article_workspace.category, 'private')
        self.assertEqual(article_workspace.internal_permission, 'none')
        self.assertMembers(
            article_workspace,
            'none',
            {self.partner_employee: 'write'}
        )

        # 2. accessible children were correctly moved to private
        for workspace_descendant, parent_id in zip(
                workspace_children + wkspace_grandchildren + wkspace_grandgrandchildren,
                [article_workspace, article_workspace, workspace_children[0], workspace_children[0],
                 workspace_children[1], wkspace_grandchildren[1], wkspace_grandchildren[2]]
            ):
            self.assertEqual(workspace_descendant.category, 'private')
            self.assertEqual(workspace_descendant.inherited_permission_parent_id, article_workspace)
            self.assertEqual(workspace_descendant.parent_id, parent_id)
            # all specific members should have been wiped, no permission
            self.assertMembers(
                workspace_descendant,
                False,
                {}
            )

        # 3.children that were not writable are moved as a root articles and that
        # members / internal permissions are kept
        self.assertEqual(wkspace_child_read_member_access.category, 'workspace')
        self.assertFalse(wkspace_child_read_member_access.parent_id)
        self.assertMembers(
            wkspace_child_read_member_access,
            'write',
            {self.partner_employee: 'read',
             self.customer: 'read'}
        )
        self.assertEqual(wkspace_child_read_internal_access.category, 'workspace')
        self.assertFalse(wkspace_child_read_internal_access.parent_id)
        self.assertMembers(
            wkspace_child_read_internal_access,
            'read',
            {self.partner_employee2: 'write',
             self.customer: 'read'}
        )
        self.assertEqual(wkspace_child_no_access.category, 'workspace')
        self.assertFalse(wkspace_child_no_access.parent_id)
        self.assertMembers(
            wkspace_child_no_access,
            'write',
            {self.partner_employee: 'none',
             self.customer: 'read'}
        )
        self.assertEqual(wkspace_grandchild_read_member_access.category, 'workspace')
        self.assertFalse(wkspace_grandchild_read_member_access.parent_id)
        self.assertMembers(
            wkspace_grandchild_read_member_access,
            'write',
            {self.partner_employee: 'read',
             self.customer: 'read'}
        )

        # 'Hidden Child' is still not accessible for employee
        with self.assertRaises(exceptions.AccessError):
            wkspace_child_no_access.with_env(self.env).body
        wkspace_child_no_access.with_user(self.user_employee2).body

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models.unlink')
    @users('employee')
    def test_article_make_private_w_desynchronized(self):
        """ Test a special case when making private: we have desynchronized children.
        Children that are de-synchronized should NOT have members from their parent(s)
        copied onto them when they are detached.

        Specific setup for this test
        # - Playground                workspace    w+    (customer-r+,employee-w+)
        #   - Child1                  "            w+DES (customer-r+,employee-r+)
        #     - Gd Child1             "            "
        #     - Gd Child2             "            "
        #       - GdGd Child1         "            "
        #   - Child2                  "            "
        #     - Gd Child1             "            "
        #       - GdGd Child          "            "
        """
        # add employee on playground and desynchronize its child
        self.article_workspace._add_members(self.partner_employee, 'write')
        self.workspace_children[0]._set_member_permission(
            self.article_workspace.article_member_ids.filtered(
                lambda member: member.partner_id == self.partner_employee
            ),
            'read',
            is_based_on=True,
        )
        # check updated data
        self.assertTrue(self.workspace_children[0].is_desynchronized)
        self.assertMembers(
            self.article_workspace,
            'write',
            {self.partner_employee: 'write'}
        )
        self.assertMembers(
            self.workspace_children[0],
            'write',
            {self.partner_employee: 'read'}
        )

        article_workspace = self.article_workspace.with_env(self.env)
        [workspace_child_desync, workspace_child_tosync] = self.workspace_children.with_env(self.env)

        # add a member on the parent, it will NOT be propagated to the desync child
        article_workspace._add_members(self.customer, 'read')
        self.assertMembers(
            article_workspace,
            'write',
            {self.customer: 'read', self.partner_employee: 'write'}
        )

        # now move the article to private and check the post-processing
        article_workspace._move_and_make_private()

        # 1. desync article: moved to root (as employee does not have write access)
        # and is not desynchronized (root articles are never desynchornized)
        # should be moved to root (as employee does not have write access)
        self.assertEqual(workspace_child_desync.category, "workspace")
        self.assertFalse(workspace_child_desync.is_desynchronized)
        self.assertFalse(workspace_child_desync.parent_id)
        # it should NOT have had customer access copied onto it as it was desync when we moved it
        self.assertMembers(
            workspace_child_desync,
            "write",
            {self.partner_employee: 'read'}
        )

        # 2. sync article: NOT moved to root (as employee has write access) and is
        # still sunchronized
        self.assertEqual(workspace_child_tosync.category, "private")
        self.assertFalse(workspace_child_desync.is_desynchronized)
        self.assertEqual(workspace_child_tosync.parent_id, article_workspace)

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models.unlink')
    @users('employee_manager')
    def test_article_make_private_w_parent(self):
        """ Test a special case when making private: moving under an existing private parent. """
        article_shared = self.article_shared.with_env(self.env)
        article_private_manager = self.article_private_manager.with_env(self.env)

        # first test that making 'article_shared' fails since 'employee_manager'
        # does not have write access to it (only read)
        with self.assertRaises(exceptions.AccessError):
            article_shared._move_and_make_private(parent=article_private_manager)

        # then grant write access to test the flow
        article_shared.sudo().article_member_ids.filtered(
            lambda member: member.partner_id == self.partner_employee_manager
        ).write({'permission': 'write'})

        article_shared._move_and_make_private(parent=article_private_manager)

        self.assertEqual(article_shared.category, 'private')
        # the internal permission should not be set as we inherit from our private parent
        # members should be wiped as we inherit from our private parent
        self.assertMembers(
            article_shared,
            False,
            {}
        )

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_move_to(self):
        """ Testing the API for moving articles. """
        article_workspace = self.article_workspace.with_env(self.env)
        article_shared = self.article_shared.with_env(self.env)
        workspace_children = self.workspace_children.with_env(self.env)

        with self.assertRaises(exceptions.AccessError,
                               msg='Cannot move under readonly parent'):
            workspace_children[0].move_to(parent_id=article_shared.id)
        with self.assertRaises(exceptions.AccessError,
                               msg='Cannot move a readonly article'):
            article_shared[0].move_to(parent_id=article_workspace.id)
        with self.assertRaises(exceptions.AccessError,
                               msg='Cannot move a readonly article (even out of any hierarchy)'):
            article_shared[0].move_to(category='workspace')

        # valid move: put second child of workspace under the first one
        workspace_children[1].move_to(parent_id=workspace_children[0].id)
        workspace_children.flush_model()
        self.assertEqual(article_workspace.child_ids, workspace_children[0])
        self.assertTrue(workspace_children < article_workspace._get_descendants())
        self.assertEqual(workspace_children.root_article_id, article_workspace)
        self.assertEqual(workspace_children[1].parent_id, workspace_children[0])
        self.assertEqual(workspace_children[0].parent_id, article_workspace)

        # Test that desynced articles are resynced when moved to root
        workspace_children[0].sudo().write(workspace_children[0]._desync_access_from_parents_values())
        self.assertTrue(workspace_children[0].is_desynchronized)

        # other valid move: first child is moved to private section
        workspace_children[0].move_to(category='private')
        workspace_children.flush_model()
        self.assertMembers(workspace_children[0], 'none', {self.partner_employee: 'write'})
        self.assertEqual(workspace_children[0].category, 'private')
        self.assertEqual(workspace_children[0].internal_permission, 'none')
        self.assertFalse(workspace_children[0].is_desynchronized)
        self.assertFalse(workspace_children[0].parent_id)
        self.assertEqual(workspace_children.root_article_id, workspace_children[0])

        workspace_child_item = self.env['knowledge.article'].create({
            'name': 'Article Item Child',
            'parent_id': article_workspace.id,
            'is_article_item': True
        }).with_env(self.env)

        with self.assertRaises(exceptions.ValidationError):
            workspace_children[0].move_to(parent_id=workspace_child_item.id)


    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_move_to_shared(self):
        """ Testing the valid moves to the shared section. """
        article_private = self.env['knowledge.article'].sudo().create({
            'article_member_ids': [(0, 0, {
                'partner_id': self.partner_employee.id,
                'permission': 'write',
            })],
            'internal_permission': 'none',
            'name': 'Employee Priv.',
            'sequence': self._base_sequence - 3,
        })
        article_shared_employee = self.env['knowledge.article'].sudo().create({
            'article_member_ids': [
                (0, 0, {
                    'partner_id': self.partner_employee.id,
                    'permission': 'write',
                }),
                (0, 0, {
                    'partner_id': self.partner_employee2.id,
                    'permission': 'read',
                }),
            ],
            'internal_permission': 'none',
            'name': 'Employee Shared',
            'sequence': self._base_sequence - 4,
        })
        article_workspace = self.article_workspace.with_env(self.env)
        article_workspace2 = self.env['knowledge.article'].sudo().create({
            'internal_permission': 'write',
            'name': 'To be shared',
            'article_member_ids': [
                (0, 0, {'partner_id': self.user_employee2.partner_id.id, 'permission': 'read'}),
            ],
        }).with_env(self.env)
        a_ws2_child_write, a_ws2_child_read = self.env['knowledge.article'].sudo().create([{
            'name': 'Employee can write',
            'article_member_ids': [
                (0, 0, {'partner_id': self.partner_employee.id, 'permission': 'write'}),
            ],
            'parent_id': article_workspace2.id,
        }, {
            'name': 'Employee can read',
            'article_member_ids': [
                (0, 0, {'partner_id': self.partner_employee.id, 'permission': 'read'}),
            ],
            'parent_id': article_workspace2.id,
        }]).with_env(self.env)
        shared_child = self.shared_children[0].with_env(self.env)

        # valid move: shared root -> shared root (resequence)
        article_shared_employee.move_to(category='shared')
        article_shared_employee.flush_model()
        self.assertTrue(article_shared_employee.sequence > self.article_shared.sequence)
        self.assertEqual(article_shared_employee.category, 'shared')
        self.assertFalse(article_shared_employee.parent_id)

        # valid move: workspace -> shared child
        article_workspace.move_to(parent_id=article_shared_employee.id)
        article_workspace.flush_model()
        self.assertEqual(article_workspace.inherited_permission_parent_id, article_shared_employee)
        self.assertFalse(article_workspace.internal_permission)

        # valid move: private -> shared child
        article_private.move_to(parent_id=article_shared_employee.id)
        article_private.flush_model()
        self.assertEqual(article_private.inherited_permission_parent_id, article_shared_employee)
        self.assertFalse(article_workspace.internal_permission)

        # valid move: shared child -> shared child
        shared_child.move_to(parent_id=article_shared_employee.id)
        shared_child.flush_model()
        self.assertEqual(shared_child.inherited_permission_parent_id, article_shared_employee)

        # valid move: shared child -> shared root
        shared_child.move_to(category='shared')
        shared_child.flush_model()
        self.assertFalse(shared_child.parent_id)
        self.assertEqual(shared_child.category, 'shared')
        # should have added inherited members on the article
        self.assertMembers(shared_child, 'none', {
            self.partner_employee: 'write',
            self.partner_employee2: 'read',
        })

        # valid move: workspace with 1 partner with read permission -> shared root
        article_workspace2.move_to(category='shared', before_article_id=article_shared_employee.id)
        article_workspace2.flush_model()
        self.assertFalse(article_workspace2.parent_id)
        self.assertEqual(article_workspace2.category, 'shared')
        self.assertTrue(article_workspace2.sequence < article_shared_employee.sequence)
        # should have added user as member on the article
        self.assertMembers(article_workspace2, 'none', {
            self.partner_employee: 'write',
            self.partner_employee2: 'read',
        })
        # ensure that a_ws2_child_write is still a child of article_workspace2
        self.assertEqual(a_ws2_child_write.parent_id, article_workspace2)
        self.assertEqual(a_ws2_child_write.category, 'shared')
        # ensure that a_ws2_child_read has become a root since employee did not
        # have write access on it while moving article_workspace2 to shared
        self.assertFalse(a_ws2_child_read.parent_id)
        self.assertEqual(a_ws2_child_read.category, 'workspace')

    @users('employee')
    def test_user_has_access_parent_path(self):
        Articles = self.env['knowledge.article']

        root = Articles.with_user(self.user_admin).article_create(title="Root")
        child = Articles.with_user(self.user_admin).article_create(title="Child", parent_id=root.id)
        grandchild = Articles.with_user(self.user_admin).article_create(title="Grandchild", parent_id=child.id)
        baby = Articles.with_user(self.user_admin).article_create(title="Baby", parent_id=grandchild.id)

        root_user = root.with_user(self.env.user)
        child_user = child.with_user(self.env.user)
        grandchild_user = grandchild.with_user(self.env.user)
        baby_user = baby.with_user(self.env.user)

        self.assertTrue(baby_user.user_has_access_parent_path)
        self.assertTrue(baby.user_has_access_parent_path)

        child._add_members(self.env.user.partner_id, 'none')
        grandchild._add_members(self.env.user.partner_id, 'write')

        self.assertMembers(child, False, {self.env.user.partner_id: 'none'})
        self.assertMembers(grandchild, False, {self.env.user.partner_id: 'write'})
        self.assertMembers(root, 'write', {self.user_admin.partner_id: 'write'})
        self.assertTrue(root_user.user_has_access)
        self.assertTrue(root.user_has_access)

        self.assertTrue(root_user.user_has_access_parent_path)
        self.assertTrue(root.user_has_access_parent_path)

        self.assertFalse(child_user.user_has_access)
        self.assertTrue(child.user_has_access)

        self.assertTrue(grandchild_user.user_has_access)
        self.assertFalse(grandchild_user.user_has_access_parent_path)

        self.assertTrue(baby.user_has_access_parent_path)
        self.assertFalse(baby_user.user_has_access_parent_path)

        with self.assertRaises(exceptions.AccessError):
            baby_user.action_join()

@tagged('knowledge_internals', 'knowledge_management')
class TestKnowledgeArticleCopy(KnowledgeCommonBusinessCase):
    """ Test copy and duplication of articles """

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_duplicate(self):
        """ Test articles duplication (=copy/copy_batch methods). Verifies that
        the children of a duplicated article are also duplicated, that
        duplicating an article and one of its children does not duplicate the
        children 2 times, and that employee cannot bypass access rules.
        """
        article_workspace = self.article_workspace.with_env(self.env)

        # Selecting several articles in the same hierarchy should only duplicate the highest one
        workspace_articles = article_workspace | article_workspace._get_descendants()
        duplicate = workspace_articles.copy_batch()
        self.assertEqual(
            len(duplicate), 1,
            'Copy batch should not return a copy of workspace descendants as they are already in article children'
        )
        self.assertEqual(duplicate.name, f'{article_workspace.name} (copy)')
        self.assertEqual(len(duplicate.child_ids), 2, 'Copy batch should copy children')
        self.assertEqual(
            sorted(duplicate.mapped('child_ids.name')),
            sorted([f'{name}' for name in article_workspace.mapped('child_ids.name')])
        )

        # Selecting 2 articles in different hierarchies (under same parent) should duplicate both
        workspace_children = self.workspace_children.with_env(self.env)
        duplicates = workspace_children.copy_batch()
        self.assertEqual(
            sorted(duplicates.mapped('name')),
            sorted([f'{name}' for name in workspace_children.mapped('name')])
        )

        # Duplicating readonly article should raise an error
        article_readonly = self.article_shared.with_env(self.env)
        with self.assertRaises(exceptions.AccessError):
            article_readonly.copy()
        # Duplicating hidden article should raise an error
        article_hidden = self.article_private_manager.with_env(self.env)
        with self.assertRaises(exceptions.AccessError):
            article_hidden.copy()
        # Duplicating readonly article's child with write permission should raise an error
        article_write_member = self.shared_children[0].with_env(self.env)
        with self.assertRaises(exceptions.AccessError):
            article_write_member.copy()

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('admin')
    def test_article_duplicate_admin(self):
        """ Test duplicate (copy_batch) as admin as he has enough rights to really
        copy articles, not like employee currently. """
        workspace_children = self.workspace_children.with_env(self.env)
        shared = self.article_shared.with_env(self.env)
        duplicates = (workspace_children + shared).copy_batch()
        for original, copy in zip(workspace_children + shared, duplicates):
            self.assertEqual(copy.name, f'{original.name}{" (copy)" if not original.parent_id else ""}')
            self.assertEqual(len(original.child_ids), len(copy.child_ids))
            self.assertEqual(len(original._get_descendants()), len(copy._get_descendants()))
            self.assertNotEqual(original.child_ids, copy.child_ids)
        self.assertEqual(
            sorted(duplicates.mapped('child_ids.name')),
            sorted([f'{name}' for name in (workspace_children + shared).mapped('child_ids.name')])
        )
        self.assertEqual(
            sorted(article.name for article in duplicates[-1]._get_descendants()),
            sorted(f'{article.name}' for article in shared._get_descendants()),
            "Check descendants name is also updated (not only direct children)"
        )

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_make_private_copy(self):
        article_hidden = self.article_private_manager.with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: copy should not allow to access hidden articles"):
            _new_article = article_hidden.action_make_private_copy()

        # Copying an article should create a private article without parent nor children
        article_readonly = self.article_shared.with_env(self.env)
        new_article = article_readonly.action_make_private_copy()
        self.assertEqual(new_article.name, f'{article_readonly.name} (copy)')
        self.assertMembers(
            new_article,
            'none',
            {self.partner_employee: 'write'}
        )
        self.assertFalse(new_article.child_ids)
        self.assertFalse(new_article.parent_id)

    def test_article_make_private_copy_having_embedded_views_of_article_items(self):
        """ When the user copies an article, the system should copy the body
            of the original article and update the ID references stored within
            it so that the embedded views listing the article items of the original
            article now list the article items of the copy. This test will check
            that the ID references have been updated in the body of the new article. """
        article = self.env['knowledge.article'].create({
            'name': 'Hello'
        })

        def render_embedded_view(embedded_props):
            return '''
                <div data-embedded='view'
                    data-oe-protected='true'
                    data-embedded-props='%s'/>
            ''' % (json.dumps(embedded_props))

        article.write({
            'body': (
                '<p>Hello world</p>' +
                render_embedded_view({
                    'viewProps': {
                        'action_xml_id': 'knowledge.knowledge_article_item_action',
                        'display_name': 'Kanban',
                        'view_type': 'kanban',
                        'context': {
                            'active_id': article.id,
                            'default_parent_id': article.id,
                            'default_icon': '📄',
                            'default_is_article_item': True,
                        }
                    }
                }) +
                render_embedded_view({
                    'viewProps': {
                        'action_xml_id': 'knowledge.knowledge_article_item_action',
                        'display_name': 'List',
                        'view_type': 'list',
                        'context': {
                            'active_id': article.id,
                            'default_parent_id': article.id,
                            'default_icon': '📄',
                            'default_is_article_item': True,
                        }
                    }
                }) +
                render_embedded_view({
                    'viewProps': {
                        'action_xml_id': 'knowledge.knowledge_article_action',
                        'display_name': 'Articles',
                        'view_type': 'list',
                        'context': {
                            'search_default_filter_trashed': 1,
                        }
                    }
                })
            )
        })

        expected_view_types = [
            'kanban',
            'list',
            'list'
        ]
        expected_contexts = [{
            'active_id': article.id,
            'default_parent_id': article.id,
            'default_icon': '📄',
            'default_is_article_item': True,
        }, {
            'active_id': article.id,
            'default_parent_id': article.id,
            'default_icon': '📄',
            'default_is_article_item': True,
        }, {
            'search_default_filter_trashed': 1,
        }]

        fragment = html.fragment_fromstring(article.body, create_parent=True)
        embedded_views = list(fragment.findall('.//*[@data-embedded="view"]'))

        # Check that the original article contains the embedded views we want
        self.assertEqual(len(embedded_views), 3)
        for (embedded_view, expected_view_type, expected_context) in zip(embedded_views, expected_view_types, expected_contexts):
            embedded_props = json.loads(embedded_view.get('data-embedded-props', {}))
            view_props = embedded_props.get('viewProps', {})
            self.assertEqual(view_props['view_type'], expected_view_type)
            self.assertEqual(view_props['context'], expected_context)

        # Copy the article
        new_article = article.action_make_private_copy()

        expected_contexts = [{
            'active_id': new_article.id,
            'default_parent_id': new_article.id,
            'default_icon': '📄',
            'default_is_article_item': True,
        }, {
            'active_id': new_article.id,
            'default_parent_id': new_article.id,
            'default_icon': '📄',
            'default_is_article_item': True,
        }, {
            'search_default_filter_trashed': 1,
        }]

        fragment = html.fragment_fromstring(new_article.body, create_parent=True)
        embedded_views = list(fragment.findall('.//*[@data-embedded="view"]'))

        # Check that the context of the embedded views stored in the body of the
        # newly created article have properly been updated: The embedded views
        # listing the article items of the original article should now list the
        # article items of the copy.

        self.assertEqual(len(embedded_views), 3)
        for (embedded_view, expected_view_type, expected_context) in zip(embedded_views, expected_view_types, expected_contexts):
            embedded_props = json.loads(embedded_view.get('data-embedded-props', {}))
            view_props = embedded_props.get('viewProps', {})
            self.assertEqual(view_props['view_type'], expected_view_type)
            self.assertEqual(view_props['context'], expected_context)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_copy(self):
        article_hidden = self.article_private_manager.with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: copy should not allow to access hidden articles"):
            _new_article = article_hidden.copy()

        # Copying an article should create a private article without parent nor children
        article_readonly = self.article_shared.with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: copy should not allow to access readonly articles members"):
            _new_article = article_readonly.copy()

        # Copy an accessible article
        article_workspace = self.article_workspace.with_env(self.env)
        new_article = article_workspace.copy()
        self.assertEqual(new_article.name, f'{article_workspace.name} (copy)')
        self.assertMembers(
            new_article,
            'write',
            {}
        )
        self.assertEqual(len(new_article.child_ids), 2, 'Copy: should copy children')
        self.assertTrue(new_article.child_ids != article_workspace.child_ids)
        self.assertEqual(
            sorted(new_article.child_ids.mapped('name')),
            sorted([f"{name}" for name in article_workspace.child_ids.mapped('name')])
        )
        self.assertFalse(new_article.parent_id)


@tagged('knowledge_internals', 'knowledge_management')
class TestKnowledgeArticleRemoval(KnowledgeCommonBusinessCase):
    """ Test unlink / archive management of articles """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.shared_article_multi_company = cls.env['knowledge.article'].create({
            'name': "Multi-Company Article",
            'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee_c2.id, 'permission': 'read'}),
                (0, 0, {'partner_id': cls.partner_employee.id, 'permission': 'write'}),
                (0, 0, {'partner_id': cls.partner_admin.id, 'permission': 'write'})
            ],
            'internal_permission': 'none'
        })

    @users('employee')
    def test_send_to_trash_multi_company(self):
        article_to_trash = self.shared_article_multi_company
        article_to_trash.action_send_to_trash()
        self.assertFalse(article_to_trash.active)
        self.assertTrue(article_to_trash.to_delete)

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_archive(self):
        """ Testing archive that should also archive children. """
        self._test_archive(test_trash=False)

    def test_archive_unactive_article(self):
        """ Checking that an unactive article can be archived. """
        article = self.env['knowledge.article'].create({'name': 'Article'})
        self.assertTrue(article.active)
        self.assertFalse(article.to_delete)

        article.action_archive()
        self.assertFalse(article.active)
        self.assertFalse(article.to_delete)

        article.action_send_to_trash()
        self.assertFalse(article.active)
        self.assertTrue(article.to_delete)

    def _test_archive(self, test_trash=False):
        archive_method_name = 'action_send_to_trash' if test_trash else 'action_archive'

        article_shared = self.article_shared.with_env(self.env)
        article_workspace = self.article_workspace.with_env(self.env)
        wkspace_children = self.workspace_children.with_env(self.env)
        # to test descendants computation, add some sub children
        wkspace_grandchildren = self.wkspace_grandchildren.with_env(self.env)
        wkspace_grandgrandchildren = self.wkspace_grandgrandchildren.with_env(self.env)

        # no write access -> cracboum
        with self.assertRaises(exceptions.AccessError,
                               msg='Employee can read thus not archive'):
            getattr(article_shared, archive_method_name)()

        # set the root + children inactive
        getattr(article_workspace, archive_method_name)()
        self.assertFalse(article_workspace.active)
        self.assertEqual(article_workspace.to_delete, test_trash)
        for article in wkspace_children + wkspace_grandchildren + wkspace_grandgrandchildren:
            self.assertFalse(article.active, 'Archive: should propagate to children')
            self.assertEqual(article.root_article_id, article_workspace,
                             'Archive: does not change hierarchy when archiving without breaking hierarchy')
            self.assertEqual(article.to_delete, test_trash)

        # reset as active
        articles_to_restore = article_workspace + wkspace_children + wkspace_grandchildren + wkspace_grandgrandchildren
        articles_to_restore.action_unarchive()
        for article in articles_to_restore:
            self.assertTrue(article.active)
            self.assertFalse(article.to_delete)

        # set only part of tree inactive
        getattr(wkspace_children, archive_method_name)()
        self.assertTrue(article_workspace.active)
        self.assertFalse(article_workspace.to_delete)
        for article in wkspace_children + wkspace_grandchildren + wkspace_grandgrandchildren:
            self.assertFalse(article.active, 'Archive: should propagate to children')
            self.assertEqual(article.to_delete, test_trash, 'Trash: should propagate to children')

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_archive_mixed_rights(self):
        self._test_archive_mixed_rights(test_trash=False)

    def _test_archive_mixed_rights(self, test_trash=False):
        """ Test archive in case of mixed rights """
        # give write access to shared section, but have children in read or none
        # and add a customer on top of shared articles to check propagation
        archive_method_name = 'action_send_to_trash' if test_trash else 'action_archive'

        self.article_shared.write({
            'article_member_ids': [(0, 0, {
                'partner_id': self.customer.id,
                'permission': 'read',
            })]
        })
        self.article_shared.article_member_ids.sudo().filtered(
            lambda article: article.partner_id == self.partner_employee
        ).write({'permission': 'write'})
        self.shared_children[1].write({
            'article_member_ids': [(0, 0, {'partner_id': self.partner_employee.id,
                                           'permission': 'read'})]
        })

        # prepare comparison data as sudo
        writable_child_su = self.article_shared.child_ids.filtered(
            lambda article: article.name in ['Shared Child1'])
        readonly_child_su = self.article_shared.child_ids.filtered(
            lambda article: article.name in ['Shared Child2'])
        hidden_child_su = self.article_shared.child_ids.filtered(
            lambda article: article.name in ['Shared Child3'])

        # perform archive as user
        article_shared = self.article_shared.with_env(self.env)
        article_shared.invalidate_model(['child_ids'])  # context dependent
        shared_children = article_shared.child_ids
        writable_child, readonly_child = writable_child_su.with_env(self.env), readonly_child_su.with_env(self.env)
        self.assertEqual(len(shared_children), 2)
        self.assertFalse(readonly_child.user_has_write_access)
        self.assertTrue(writable_child.user_has_write_access)
        self.assertEqual(shared_children, writable_child + readonly_child,
                         'Should see only two first children')

        getattr(article_shared, archive_method_name)()
        # check writable articles have been archived, readonly or hidden not
        self.assertFalse(article_shared.active)
        self.assertEqual(article_shared.to_delete, test_trash)
        self.assertFalse(writable_child.active)
        self.assertEqual(writable_child.to_delete, test_trash)
        self.assertTrue(readonly_child.active)
        self.assertFalse(readonly_child.to_delete)
        self.assertTrue(hidden_child_su.active)
        self.assertFalse(hidden_child_su.to_delete)

        # check hierarchy
        self.assertEqual(writable_child.parent_id, article_shared,
                         'Archive: archived articles hierarchy does not change')
        self.assertFalse(readonly_child.parent_id, 'Archive: article should be extracted in archive process as non writable')
        self.assertEqual(readonly_child.root_article_id, readonly_child)
        self.assertFalse(hidden_child_su.parent_id, 'Archive: article should be extracted in archive process as non writable')
        self.assertEqual(hidden_child_su.root_article_id, hidden_child_su)

        # verify that the child that was not accessible was moved as a root article...
        self.assertTrue(hidden_child_su.active)
        self.assertEqual(hidden_child_su.category, 'shared')
        self.assertEqual(hidden_child_su.internal_permission, 'none')
        self.assertFalse(hidden_child_su.parent_id)
        # ... and kept his access rights: still member for employee / admin and
        # copied customer access from the archived parent
        self.assertMembers(
            hidden_child_su,
            'none',
            {self.user_admin.partner_id: 'write',
             self.partner_employee_manager: 'read',
             self.partner_employee: 'none',
             self.customer: 'read',
            }
        )

        # Test that articles removed from trash are made roots if their parent are still in the Trash.
        if test_trash:
            writable_child.action_unarchive()
            self.assertFalse(writable_child.to_delete)
            self.assertFalse(writable_child.parent_id)
            self.assertTrue(article_shared.to_delete)
            self.assertTrue(writable_child not in article_shared.with_context(
                active_test=False).child_ids)
            self.assertEqual(writable_child.internal_permission,
                             article_shared.internal_permission)
            # Note: could be different if writable_child had custom partners. Not the case here so we can use '=='.
            self.assertTrue(article_shared.article_member_ids.partner_id == writable_child.article_member_ids.partner_id)

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_trashed(self):
        """ Testing 'send to trash' that should also trash children. """
        self._test_archive(test_trash=True)

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_trashed_mixed_rights(self):
        """ Test Trash in case of mixed rights """
        self._test_archive_mixed_rights(test_trash=True)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule', 'odoo.models.unlink')
    @users('admin')
    def test_unlink_admin(self):
        """ Admin (system) has access to unlink, test propagation and effect
        on children. """
        article_shared = self.article_shared.with_env(self.env)
        article_shared.unlink()
        self.assertFalse(
            (self.article_shared + self.shared_children).exists(),
            'Unlink: should also unlink children'
        )

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule', 'odoo.models.unlink')
    @users('employee')
    def test_unlink_employee(self):
        """ Employee cannot unlink anyway """
        article_hidden = self.article_private_manager.with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: uhnlink is not accessible to employees"):
            article_hidden.unlink()

        article_workspace = self.article_workspace.with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: unlink is not accessible to employees"):
            article_workspace.unlink()

    def test_unarchive_article_items_having_archived_parent(self):
        """ Check that the user can not unarchive an article item whose parent is archived. """
        parent_article = self.env['knowledge.article'].create({
            'active': False,
            'to_delete': True,
            'name': 'Parent article',
        })
        article_item = self.env['knowledge.article'].create({
            'active': False,
            'to_delete': True,
            'name': 'Article item',
            'parent_id': parent_article.id,
            'is_article_item': True,
        })

        with self.assertRaises(UserError):
            article_item.action_unarchive()

        (parent_article + article_item).action_unarchive()
        self.assertTrue(parent_article.active)
        self.assertFalse(parent_article.to_delete)
        self.assertTrue(article_item.active)
        self.assertFalse(article_item.to_delete)
        self.assertEqual(article_item.parent_id, parent_article)


    @users('employee')
    def test_unarchive_article_having_inaccessible_parent(self):
        """ Check that the user can restore an article whose parent is inaccessible. """

        parent_article = self.env['knowledge.article'].sudo().create({
            'active': False,
            'to_delete': True,
            'name': 'Parent article',
            'internal_permission': 'write',
            'article_member_ids': [
                (0, 0, {
                    'partner_id': self.env.user.partner_id.id,
                    'permission': 'none'
                }),
                (0, 0, {
                    'partner_id': self.customer.id,
                    'permission': 'read'
                }),
            ]
        }).with_user(self.env.user)

        child_article = self.env['knowledge.article'].sudo().create({
            'active': False,
            'to_delete': True,
            'name': 'Child article',
            'parent_id': parent_article.id,
            'article_member_ids': [
                (0, 0, {
                    'partner_id': self.env.user.partner_id.id,
                    'permission': 'write'
                }),
            ]
        }).with_user(self.env.user)

        # Check the access rights:
        parent_article.browse().check_access('read')
        with self.assertRaises(exceptions.AccessError):
            parent_article.check_access('read')
        child_article.check_access('write')

        # Unarchive the child article:
        child_article.action_unarchive()

        # When the parent article is in the trash, the child article should be
        # detached from its parent so that it will not be deleted when the parent
        # article is deleted.

        self.assertTrue(child_article.active)
        self.assertFalse(child_article.to_delete)
        self.assertFalse(child_article.parent_id)
        self.assertFalse(child_article.is_desynchronized)
        self.assertMembers(child_article, 'write', {
            self.env.user.partner_id: 'write',
            self.customer: 'read'
        })

        self.assertFalse(parent_article.active)
        self.assertTrue(parent_article.to_delete)
        self.assertMembers(parent_article, 'write', {
            self.env.user.partner_id: 'none',
            self.customer: 'read'
        })

    def test_trashed_article_garbage_collect(self):
        [normal, trashed_not_to_unlink, archived_not_trashed] = self.env['knowledge.article'].create([{
            'name': 'Normal article',
            'internal_permission': 'write',
        }, {
            'active': False,
            'to_delete': True,
            'internal_permission': 'write',
            'name': 'Trashed not to unlink',
            'parent_id': False,
        }, {
            'active': False,
            'internal_permission': 'write',
            'to_delete': False,
            'name': 'Only Archived',
            'parent_id': False,
        }])

        self.env['knowledge.article'].flush_model()

        before = datetime.now() - timedelta(days=self.env['knowledge.article'].DEFAULT_ARTICLE_TRASH_LIMIT_DAYS + 1)
        # Older article
        with patch.object(self.env.cr, 'now', return_value=before):
            trashed_to_unlink = self.env['knowledge.article'].create({
                'active': False,
                'internal_permission': 'write',
                'to_delete': True,
                'name': 'Trashed to unlink',
                'parent_id': False,
            })
            self.env['knowledge.article'].flush_model()

        self.env['knowledge.article']._gc_trashed_articles()
        self.assertFalse(trashed_to_unlink.exists())
        self.assertTrue(normal.exists())
        self.assertTrue(trashed_not_to_unlink.exists(), "This article's deletion date is not yet passed.")
        self.assertTrue(archived_not_trashed.exists(), "This article is archived and not trashed (to_delete = False), it shouldn't be unlinked.")

@tagged('post_install', '-at_install', 'knowledge_internals', 'knowledge_management')
class TestKnowledgeShare(KnowledgeCommonWData):
    """ Test share feature. """
    def test_article_can_invite_members_with_wizard(self):
        """Check that the administrator is allowed to invite a new member
           without 'write' permission by using the invitation wizard."""
        article = self.env['knowledge.article'].create({
            'name': 'My article',
            'internal_permission': 'write',
            'article_member_ids': [
                (0, 0, {'partner_id': self.partner_employee.id, 'permission': 'read'}),
                (0, 0, {'partner_id': self.partner_admin.id, 'permission': 'read'})
            ]
        })

        self.assertFalse(article.with_user(self.user_employee).user_has_write_access)
        self.assertFalse(article.with_user(self.user_admin).user_has_write_access)

        with self.assertRaises(exceptions.AccessError):
            self.env['knowledge.invite'].with_user(self.user_employee).create({
                'article_id': article.id,
                'partner_ids': self.partner_public,
                'permission': 'read',
            })

        self.assertMembers(article, 'write', {
            self.partner_employee: 'read',
            self.partner_admin: 'read'
        })

        self.env['knowledge.invite'].with_user(self.user_admin).create({
            'article_id': article.id,
            'partner_ids': self.partner_public,
            'permission': 'read',
        }).action_invite_members()

        self.assertMembers(article, 'write', {
            self.partner_employee: 'read',
            self.partner_admin: 'read',
            self.partner_public: 'read'
        })

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    @users('employee2')
    def test_knowledge_article_share(self):
        # private article of "employee manager"
        knowledge_article_sudo = self.env['knowledge.article'].sudo().create({
            'name': 'Test Article',
            'body': '<p>Content</p>',
            'internal_permission': 'none',
            'article_member_ids': [(0, 0, {
                'partner_id': self.partner_employee_manager.id,
                'permission': 'write',
            })],
        })
        article = knowledge_article_sudo.with_env(self.env)
        self.assertFalse(article.user_has_access)

        # employee2 is not supposed to be able to share it
        with self.assertRaises(exceptions.AccessError):
            self._knowledge_article_share(article, self.partner_portal.ids, 'read')

        # give employee2 read access on the document
        knowledge_article_sudo.write({
            'article_member_ids': [(0, 0, {
                'partner_id': self.partner_employee2.id,
                'permission': 'read',
            })]
        })
        self.assertTrue(article.user_has_access)

        # still not supposed to be able to share it
        with self.assertRaises(exceptions.AccessError):
            self._knowledge_article_share(article, self.partner_portal.ids, 'read')

        # modify employee2 access to write
        knowledge_article_sudo.article_member_ids.filtered(
            lambda member: member.partner_id == self.partner_employee2
        ).write({'permission': 'write'})

        # now they should be able to share it
        with self.mock_mail_gateway(), self.mock_mail_app():
            self._knowledge_article_share(article, self.partner_portal.ids, 'read')

        # check that portal user received an invitation link
        self.assertEqual(len(self._new_msgs), 1)
        self.assertIn(
            knowledge_article_sudo._get_invite_url(self.partner_portal),
            self._new_mails.body_html
        )

        with self.with_user('portal_test'):
            # portal should now have read access to the article
            # (re-browse to have the current user context for user_permission)
            article_asportal = knowledge_article_sudo.with_env(self.env)
            self.assertTrue(article_asportal.user_has_access)

    def _knowledge_article_share(self, article, partner_ids, permission='write'):
        """ Re-browse the article to make sure we have the current user context on it.
        Necessary for all access fields compute methods in knowledge.article. """

        return self.env['knowledge.invite'].create({
            'article_id': self.env['knowledge.article'].browse(article.id).id,
            'partner_ids': partner_ids,
            'permission': permission,
        }).action_invite_members()

@tagged('post_install', '-at_install', 'knowledge_internals', 'knowledge_management')
class TestKnowledgeArticleCovers(KnowledgeCommonWData):
    """ Test article covers management  """
    @users('employee')
    def test_article_cover_management(self):
        # User cannot modify cover of hidden article
        article_hidden = self.article_private_manager.with_env(self.env)
        cover = self._create_cover()
        with self.assertRaises(exceptions.AccessError,
                               msg="Cannot add cover to hidden article"):
            article_hidden.write({'cover_image_id': cover.id})
        article_hidden.with_user(self.user_admin).write({'cover_image_id': cover.id})
        with self.assertRaises(exceptions.AccessError,
                               msg="Cannot remove cover of hidden article"):
            article_hidden.write({'cover_image_id': False})

        # User cannot modify cover of readable article but has access to it
        article_read = self.article_shared.with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="Cannot add cover to readable article"):
            article_read.write({'cover_image_id': cover.id})
        cover_2 = self._create_cover()
        article_read.with_user(self.user_admin).write({'cover_image_id': cover_2.id})
        with self.assertRaises(exceptions.AccessError,
                               msg="Cannot remove cover of readable article"):
            article_read.write({'cover_image_id': False})

        # User can reuse a cover used in another article.
        article_write = self.article_workspace.with_env(self.env)
        article_write.write({'cover_image_id': cover_2.id})
        self.assertEqual(article_write.cover_image_id, cover_2)


@tagged('post_install', '-at_install', 'knowledge_internals', 'knowledge_management', 'knowledge_visibility')
class TestKnowledgeArticleVisibility(KnowledgeCommon):
    """ Test suite checking that the articles can be marked as hidden.
    This test suite should ensure that:
    1. Users can search for articles that are visible or hidden using the custom
       search method on the `is_article_visible` computed field.
    2. The shared and private articles are always visible.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Articles:
        Article = cls.env['knowledge.article']
        with mute_logger('odoo.models.unlink'):
            Article.search([]).unlink()

        cls.workspace_article = Article.create({
            'name': 'Workspace article'
        })
        cls.shared_article = Article.create({
            'name': 'Shared article',
            'internal_permission': 'none',
            'article_member_ids': [
                (0, 0, {
                    'partner_id': cls.user_admin.partner_id.id,
                    'permission': 'write'
                }),
                (0, 0, {
                    'partner_id': cls.user_employee.partner_id.id,
                    'permission': 'write'
                })
            ]
        })
        cls.private_article = Article.create({
            'name': 'Private article',
            'internal_permission': 'none',
            'article_member_ids': [(0, 0, {
                'partner_id': cls.user_employee.partner_id.id,
                'permission': 'write'
            })]
        })

    @users('employee')
    def test_is_workspace_article_visible(self):
        Article = self.env['knowledge.article']
        workspace_article = self.workspace_article.with_user(self.env.user)

        # When creating a new article in the workspace, the article should be
        # hidden by default and shouldn't appear in the sidebar.

        self.assertEqual(workspace_article.category, 'workspace')
        self.assertTrue(workspace_article.user_has_access)
        self.assertFalse(workspace_article.is_article_visible)
        self.assertFalse(workspace_article.is_article_visible_by_everyone)

        self.assertEqual(Article.search([]), self.workspace_article + self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', True)]), self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', False)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', True)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', False)]), self.shared_article + self.private_article)

        workspace_article.action_join()
        self.assertMembers(workspace_article, 'write', {self.env.user.partner_id: 'write'})

        # If the article is hidden and the user has explicit "read" or "write"
        # permission on the article (with the membership), the article should
        # become visible to the user.

        self.assertTrue(workspace_article.is_article_visible)
        self.assertFalse(workspace_article.is_article_visible_by_everyone)

        self.assertEqual(Article.search([]), self.workspace_article + self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', True)]), self.workspace_article + self.shared_article + self.private_article)
        self.assertFalse(Article.search([('is_article_visible', '=', False)]))
        self.assertFalse(Article.search([('is_article_visible', '!=', True)]))
        self.assertEqual(Article.search([('is_article_visible', '!=', False)]), self.workspace_article + self.shared_article + self.private_article)

        # When setting the `is_article_visible_by_everyone` field to `True`, the
        # article should become visible to everyone (with the exception of those
        # having no access to the article).

        workspace_article.set_is_article_visible_by_everyone(True)

        self.assertTrue(workspace_article.is_article_visible)
        self.assertTrue(workspace_article.is_article_visible_by_everyone)

        self.assertEqual(Article.search([]), self.workspace_article + self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', True)]), self.workspace_article + self.shared_article + self.private_article)
        self.assertFalse(Article.search([('is_article_visible', '=', False)]))
        self.assertFalse(Article.search([('is_article_visible', '!=', True)]))
        self.assertEqual(Article.search([('is_article_visible', '!=', False)]), self.workspace_article + self.shared_article + self.private_article)

        # Removing the user from the member list should not change the visibility
        # status of the article.

        for member in workspace_article.article_member_ids:
            workspace_article._remove_member(member)

        self.assertTrue(workspace_article.is_article_visible)
        self.assertTrue(workspace_article.is_article_visible_by_everyone)

        self.assertEqual(Article.search([]), self.workspace_article + self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', True)]), self.workspace_article + self.shared_article + self.private_article)
        self.assertFalse(Article.search([('is_article_visible', '=', False)]))
        self.assertFalse(Article.search([('is_article_visible', '!=', True)]))
        self.assertEqual(Article.search([('is_article_visible', '!=', False)]), self.workspace_article + self.shared_article + self.private_article)

    @users('employee')
    def test_is_private_article_visible(self):
        Article = self.env['knowledge.article']
        private_article = self.private_article.with_user(self.env.user)

        # For the private articles, the articles should always be visible even
        # if the article is not marked as visible to everyone and the user does
        # not have explicit "read" or "write" permission on the article.

        self.assertEqual(private_article.category, 'private')
        self.assertTrue(private_article.user_has_access)
        self.assertTrue(private_article.is_article_visible)
        self.assertFalse(private_article.is_article_visible_by_everyone)

        self.assertEqual(Article.search([]), self.workspace_article + self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', True)]), self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', False)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', True)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', False)]), self.shared_article + self.private_article)

        private_article.set_is_article_visible_by_everyone(True)

        # When setting the `is_article_visible_by_everyone` field to `True`, the
        # article should remains visible to everyone (with the exception of those
        # having no access to the article).

        self.assertTrue(private_article.is_article_visible)
        self.assertTrue(private_article.is_article_visible_by_everyone)

        self.assertEqual(Article.search([]), self.workspace_article + self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', True)]), self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', False)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', True)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', False)]), self.shared_article + self.private_article)

    @users('employee')
    def test_is_shared_article_visible(self):
        Article = self.env['knowledge.article']
        shared_article = self.shared_article.with_user(self.env.user)

        # For the shared articles, the articles should always be visible even
        # if the article is not marked as visible to everyone and the user does
        # not have explicit "read" or "write" permission on the article.

        self.assertEqual(shared_article.category, 'shared')
        self.assertTrue(shared_article.user_has_access)
        self.assertTrue(shared_article.is_article_visible)
        self.assertFalse(shared_article.is_article_visible_by_everyone)

        self.assertEqual(Article.search([]), self.workspace_article + self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', True)]), self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', False)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', True)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', False)]), self.shared_article + self.private_article)

        shared_article.set_is_article_visible_by_everyone(True)

        self.assertTrue(shared_article.is_article_visible)
        self.assertTrue(shared_article.is_article_visible_by_everyone)

        self.assertEqual(Article.search([]), self.workspace_article + self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', True)]), self.shared_article + self.private_article)
        self.assertEqual(Article.search([('is_article_visible', '=', False)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', True)]), self.workspace_article)
        self.assertEqual(Article.search([('is_article_visible', '!=', False)]), self.shared_article + self.private_article)
