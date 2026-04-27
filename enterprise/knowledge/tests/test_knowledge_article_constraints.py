# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2 import IntegrityError

from odoo import exceptions
from odoo.addons.knowledge.tests.common import KnowledgeCommon
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('knowledge_internals')
class TestKnowledgeArticleConstraints(KnowledgeCommon):
    """ This test suite has the responsibility to test the different constraints
    defined on the `knowledge.article`, `knowledge.article.member` and
    `knowledge.article.favorite` models. """

    @classmethod
    def setUpClass(cls):
        """ Add some hierarchy to have mixed rights tests """
        super().setUpClass()

        # (i) means is_article_item = True
        # - Employee Priv.  seq=19    private      none    (employee-w+)
        # - Playground      seq=20    workspace    w+      (admin-w+)
        # - Shared          seq=21    shared       none    (admin-w+,employee-r+,manager-r+)
        # -   Shared Child1 seq=0     "            "       (employee-w+)
        # - Playground Item  seq=22    worksapce    w+
        # - Item Child       seq=0     ""           ""
        cls.article_private_employee = cls.env['knowledge.article'].create(
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': 'none',
             'name': 'Employee Priv.',
             'sequence': 19,
            }
        )
        cls.article_workspace = cls.env['knowledge.article'].create(
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.user_admin.partner_id.id,
                        'permission': 'write'})],
             'internal_permission': 'write',
             'favorite_ids': [(0, 0, {'sequence': 1,
                                      'user_id': cls.user_admin.id,
                                     }),
             ],
             'name': 'Playground',
             'sequence': 20,
            }
        )
        cls.article_shared = cls.env['knowledge.article'].create(
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_admin.id,
                        'permission': 'write',
                       }),
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'read',
                       }),
                (0, 0, {'partner_id': cls.partner_employee_manager.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': 'none',
             'name': 'Shared',
             'sequence': 21,
            }
        )
        cls.shared_child = cls.env['knowledge.article'].create(
            {'article_member_ids': [
                (0, 0, {'partner_id': cls.partner_employee.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': False,
             'name': 'Shared Child1',
             'parent_id': cls.article_shared.id,
            },
        )
        cls.items_parent = cls.env['knowledge.article'].create([
            {'internal_permission': 'write',
             'name': 'Parent of items',
             'parent_id': False,
             'sequence': 22,
             }
        ])
        cls.item_child = cls.env['knowledge.article'].create([{
            'internal_permission': False,
            'name': 'Child Item',
            'parent_id': cls.items_parent.id,
            'is_article_item': True,
        }])

    @users('employee')
    def test_article_acyclic_graph_move_to(self):
        """ Check that the article hierarchy does not contain cycles using the move_to method. """
        article = self.article_workspace.with_env(self.env)
        article_children = self.env['knowledge.article'].create([
            {'name': 'ChildNew1',
             'parent_id': article.id,
             'sequence': 3,
            },
            {'name': 'ChildNew2',
             'parent_id': article.id,
             'sequence': 4,
            }
        ])

        # move the parent article under one of its children should raise an exception
        with self.assertRaises(exceptions.UserError, msg='The article hierarchy contains a cycle'):
            article.move_to(parent_id=article_children[1].id)

    @users('employee')
    def test_article_acyclic_graph_write_parent(self):
        """ Check that the article hierarchy does not contain cycles when writing on parent_id. """
        article = self.article_workspace.with_env(self.env)
        article_children = self.env['knowledge.article'].create([
            {'name': 'ChildNew1',
             'parent_id': article.id,
             'sequence': 3,
            },
            {'name': 'ChildNew2',
             'parent_id': article.id,
             'sequence': 4,
            }
        ])

        # move the parent article under one of its children should raise an exception
        with self.assertRaises(exceptions.UserError, msg='The article hierarchy contains a cycle'):
            article.write({
                'parent_id': article_children[1].id
            })

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_create(self):
        """ Testing the helper to create articles with right values. """
        article = self.article_workspace.with_env(self.env)
        readonly_article = self.article_shared.with_env(self.env)

        _title = 'Fthagn, private'
        private = self.env['knowledge.article'].create({
            'article_member_ids': [
                (0, 0, {'partner_id': self.env.user.partner_id.id,
                        'permission': 'write'})
            ],
            'body': f'<p>{_title}</p>',
            'internal_permission': 'none',
            'name': _title,
        })
        self.assertMembers(private, 'none', {self.env.user.partner_id: 'write'})
        self.assertEqual(private.category, 'private')
        self.assertFalse(private.parent_id)
        self.assertEqual(private.sequence, 23)

        _title = 'Fthagn, with parent (workspace)'
        children = self.env['knowledge.article'].create([
            {'body': f'<p>{_title}</p>',
             'name': _title,
             'parent_id': article.id,
            } for idx in range(3)
        ])
        for idx, child in enumerate(children):
            self.assertMembers(child, False, {})
            self.assertEqual(child.category, 'workspace')
            self.assertEqual(child.parent_id, article)
            self.assertEqual(child.sequence, idx, 'Batch create should correctly set sequence')

        _title = 'Fthagn, with parent (private)'
        child_private = self.env['knowledge.article'].create({
            'body': f'<p>{_title}</p>',
            'internal_permission': False,
            'name': _title,
            'parent_id': private.id,
        })
        self.assertMembers(child, False, {})
        self.assertEqual(child_private.category, 'private')
        self.assertEqual(child_private.parent_id, private)
        self.assertEqual(child_private.sequence, 0)

        _title = 'Fthagn, but private under non private: cracboum'
        with self.assertRaises(exceptions.AccessError):
            _unwanted_child = self.env['knowledge.article'].create({
                'article_member_ids': [
                    (0, 0, {'partner_id': self.env.user.partner_id.id,
                            'permission': 'write'})
                ],
                'body': f'<p>{_title}</p>',
                'internal_permission': 'none',
                'name': _title,
                'parent_id': article.id,
            })

        _title = 'Fthagn, but with parent read only: cracboum'
        with self.assertRaises(exceptions.AccessError):
            _unallowed_child = self.env['knowledge.article'].create({
                'body': f'<p>{_title}</p>',
                'internal_permission': 'write',
                'name': _title,
                'parent_id': readonly_article.id,
            })

    @users('employee')
    def test_article_move_to_shared_root(self):
        """ Check constraints restricting moving as a shared root.
        Only articles that are shared with at least 1 other member (not counting
        internal permission) can be moved as a shared root"""

        # Add members with permission='none' to make sure they are not counted as members
        workspace_article = self.env['knowledge.article'].sudo().create({
            'article_member_ids': [
                (0, 0, {'partner_id': self.env.user.partner_id.id, 'permission': 'write'}),
                (0, 0, {'partner_id': self.partner_employee2.id, 'permission': 'none'}),
                (0, 0, {'partner_id': self.partner_employee_manager.id, 'permission': 'none'}),
            ],
            'internal_permission': 'write',
            'name': 'Workspace Article without other read members',
        })
        private_article = self.article_private_employee.with_env(self.env)
        no_member_article = self.items_parent.with_env(self.env)

        with self.assertRaises(exceptions.ValidationError,
                               msg='Cannot move an article that is not shared with another member as a shared root'):
            workspace_article.move_to(category='shared')
        with self.assertRaises(exceptions.ValidationError,
                               msg='Cannot move a private article as a shared root'):
            private_article.move_to(category='shared')

        with self.assertRaises(exceptions.ValidationError,
                               msg='Cannot move an article that has no member on it'):
            no_member_article.move_to(category='shared')

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_parent_constraints_create(self):
        """ Checking various article constraints linked to parents """
        article = self.article_workspace.with_env(self.env)

        # Add employee2 as read member
        article.invite_members(self.partner_employee2, 'read')

        article_as2 = article.with_user(self.user_employee2)
        self.assertFalse(article_as2.user_has_write_access)
        self.assertTrue(article_as2.user_has_access)

        # Member should not be allowed to create an article under an article without "write" permission
        with self.assertRaises(exceptions.AccessError):
            self.env['knowledge.article'].with_user(self.user_employee2).create({
                'internal_permission': 'write',
                'name': 'My Own',
                'parent_id': article_as2.id,
            })

        # Member should not be allowed to create a private article under a non-owned article
        article_private = self._create_private_article('MyPrivate')
        self.assertMembers(article_private, 'none', {self.partner_employee: 'write'})
        self.assertTrue(article_private.category, 'private')
        self.assertTrue(article_private.user_has_write_access)
        with self.assertRaises(exceptions.AccessError):
            self.env['knowledge.article'].with_user(self.user_employee2).create({
                'name': 'My Own Private',
                'parent_id': article_as2.id,
            })

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_parent_constraints_write(self):
        """ Checking the article parent constraints. """
        article = self.article_workspace.with_env(self.env)

        # Add employee2 as read member
        article.invite_members(self.partner_employee2, 'read')

        article_as2 = article.with_user(self.user_employee2)
        self.assertFalse(article_as2.user_has_write_access)
        self.assertTrue(article_as2.user_has_access)

        # Member should not be allowed to move an article under an article without "write" permission
        article_user2 = self.env['knowledge.article'].with_user(self.user_employee2).create({
            'internal_permission': 'write',
            'name': 'My Own',
        })
        with self.assertRaises(exceptions.AccessError):
            article_user2.write({'parent_id': article_as2.id})
        with self.assertRaises(exceptions.AccessError):
            article_user2.move_to(parent_id=article_as2.id)

        # Member should be allowed to move an editable article under its current
        # parent even if the parent is readonly, and specifying the parent id
        # should not throw an error even if unnecessary.
        article_child1 = self.env['knowledge.article'].create({
            'internal_permission': 'write',
            'name': 'Ze Name',
            'parent_id': article.id,
            'sequence': 1,
        })
        article_child2 = self.env['knowledge.article'].create({
            'internal_permission': 'write',
            'name': 'Ze Name',
            'parent_id': article.id,
            'sequence': 2,
        })
        article_child2.invite_members(self.partner_employee2, 'write')
        article_child2_as2 = article_child2.with_user(self.user_employee2)
        article_child2_as2.move_to(parent_id=article.id, before_article_id=article_child1.id)
        self.assertEqual(article_child2_as2.sequence, 1)
        self.assertEqual(article_child1.sequence, 2)

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_private_management(self):
        """ Checking the article private management. """
        article_workspace = self.article_workspace.with_env(self.env)

        # Private-like article whose parent is not in private category is under workspace
        article_private_u2 = self.env['knowledge.article'].sudo().create({
            'article_member_ids': [(0, 0, {'partner_id': self.partner_employee2.id, 'permission': 'write'})],
            'internal_permission': 'none',
            'name': 'Private Child',
            'parent_id': article_workspace.id,
        }).with_user(self.user_employee2)
        self.assertEqual(article_private_u2.category, 'workspace')
        self.assertTrue(article_private_u2.user_has_write_access)

        # Effectively private: other user cannot read it
        article_private_u2_asuser = article_private_u2.with_user(self.env.user)
        with self.assertRaises(exceptions.AccessError):
            article_private_u2_asuser.body  # should trigger ACLs

        # Private root article
        article_private = self._create_private_article('MyPrivate').with_user(self.env.user)
        self.assertTrue(article_private.category, 'private')
        self.assertTrue(article_private.user_has_write_access)

        # Effectively private: other user cannot read it
        article_private_asu2 = article_private.with_user(self.user_employee2)
        with self.assertRaises(exceptions.AccessError):
            article_private_asu2.body  # should trigger ACLs

        # Move to workspace, makes it workspace
        article_private.move_to(parent_id=article_workspace.id)
        self.assertEqual(article_private.category, 'workspace')

        # Should be accessible by any user of the workspace since its permission is now inherited
        article_private_asu2 = article_private.with_user(self.user_employee2)
        article_private_asu2.body  # should not trigger ACLs
        self.assertFalse(article_private.internal_permission)
        self.assertEqual(article_private.inherited_permission, 'write')

    @mute_logger('odoo.sql_db')
    @users('employee')
    def test_article_root_internal_permission(self):
        """Check that the root article has internal permission set."""
        # defaulting to write permission if nothing is given
        article = self.env['knowledge.article'].create({
            'name': 'Article',
            'parent_id': False,
        })
        self.assertEqual(article.category, 'workspace')
        self.assertEqual(article.internal_permission, 'write')

        # ensure a member has write access before trying to remove global access
        # and allow raising the IntegrityError (otherwise a ValidationError raises)
        article.sudo().write({
            'article_member_ids': [(0, 0, {'partner_id': self.env.user.partner_id.id,
                                           'permission': 'write'})],
        })

        with self.assertRaises(IntegrityError, msg='An internal permission should be set for root article'):
            with self.cr.savepoint():
                article.write({'internal_permission': False})

        article_child = self.env['knowledge.article'].create({
            'name': 'Article',
            'parent_id': article.id,
        })
        self.assertMembers(article_child, False, {})
        self.assertEqual(article_child.category, 'workspace')
        self.assertEqual(article_child.root_article_id, article)
        with self.assertRaises(IntegrityError, msg='An internal permission should be set for root article'):
            with self.cr.savepoint():
                article_child.sudo().write({'parent_id': False})

    @users('employee')
    def test_article_should_have_at_least_one_writer(self):
        """ Check that an article has at least one writer."""
        with self.assertRaises(exceptions.ValidationError, msg='Article should have at least one writer'):
            self.env['knowledge.article'].create({
                'internal_permission': 'none',
                'name': 'Article',
            })
        with self.assertRaises(exceptions.ValidationError, msg='Article should have at least one writer'):
            self.env['knowledge.article'].create({
                'internal_permission': 'read',
                'name': 'Article',
            })

        article_private = self._create_private_article('MyPrivate')
        self.assertMembers(article_private, 'none', {self.partner_employee: 'write'})
        self.assertEqual(article_private.category, 'private')

        # take membership as sudo to really have access to unlink feature
        membership_sudo = article_private.sudo().article_member_ids
        # cannot transform last writer into rejected
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            article_private.sudo().write({
                'article_member_ids': [(1, membership_sudo.id, {'permission': 'none'})]
            })
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            article_private.sudo().write({
                'article_member_ids': [(1, membership_sudo.id, {'permission': 'read'})]
            })
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            article_private._add_members(membership_sudo.partner_id, 'none')
        # cannot remove last writer
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            membership_sudo.unlink()
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            article_private.sudo().write({
                'article_member_ids': self.env['knowledge.article.member']
            })
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            article_private.sudo().write({
                'article_member_ids': [(2, membership_sudo.id)]
            })
        # Special Case: can leave own private article via _remove_member: will archive the article.
        article_private.sudo()._remove_member(membership_sudo)
        self.assertFalse(article_private.active)
        self.assertMembers(article_private, 'none', {self.env.user.partner_id: 'write'})

        # moving the article to private will remove the second member
        # but should not trigger an error since we also add 'employee' as a write member
        article_workspace = self.article_workspace.with_env(self.env)
        article_workspace.move_to(category='private')
        self.assertEqual(article_workspace.category, 'private')
        self.assertTrue(article_workspace._has_write_member())

    @mute_logger('odoo.sql_db')
    @users('employee')
    def test_article_trashed_should_be_archived(self):
        """ Ensure that a trashed article is archived."""
        article = self.env['knowledge.article'].create({
            'name': 'Article',
            'parent_id': False,
        })

        with self.assertRaises(IntegrityError, msg='Trashed articles must be archived.'):
            with self.cr.savepoint():
                article.write({'to_delete': True})

        article.write({
            'to_delete': True,
            'active': False,
        })
        self.assertTrue(article.to_delete)
        self.assertFalse(article.active)

        with self.assertRaises(IntegrityError, msg='Trashed articles must be archived.'):
            with self.cr.savepoint():
                article.write({'active': True})

        article.write({
            'to_delete': False,
            'active': True,
        })
        self.assertTrue(article.active)
        self.assertFalse(article.to_delete)

    @mute_logger('odoo.sql_db')
    @users('employee')
    def test_favourite_uniqueness(self):
        """ Check there is at most one 'knowledge.article.favourite' entry per
        article and user. """
        article = self.env['knowledge.article'].create(
            {'internal_permission': 'write',
             'name': 'Article'}
        )
        self.assertFalse(article.is_user_favorite)
        article.action_toggle_favorite()
        self.assertTrue(article.is_user_favorite)
        with self.assertRaises(IntegrityError,
                               msg='Multiple favorite entries are not accepted'):
            article.write({'favorite_ids': [(0, 0, {'user_id': self.env.user.id})]})
        self.assertTrue(article.is_user_favorite)

    @mute_logger('odoo.sql_db')
    @users('employee')
    def test_member_uniqueness(self):
        """Check that there are no duplicated members in the member list. """
        article = self.env['knowledge.article'].create({
            'internal_permission': 'write',
            'name': 'Article',
        })
        article.sudo().write({
            'article_member_ids': [(0, 0, {'partner_id': self.env.user.partner_id.id,
                                           'permission': 'write'})]
        })
        self.assertEqual(len(self.env['knowledge.article.member'].sudo().search([('article_id', '=', article.id)])), 1)

        # adding a duplicate
        with self.assertRaises(IntegrityError,
                               msg='Members should be unique (article_id/partner_id)'):
            article.sudo().write({
                'article_member_ids': [(0, 0, {'partner_id': self.env.user.partner_id.id,
                                               'permission': 'write'})]
            })
        self.assertEqual(len(self.env['knowledge.article.member'].sudo().search([('article_id', '=', article.id)])), 1)

        # trying with tool method
        article.invite_members(self.env.user.partner_id, 'write')
        self.assertEqual(len(self.env['knowledge.article.member'].sudo().search([('article_id', '=', article.id)])), 1)

        # creating duplicates
        with self.assertRaises(IntegrityError,
                               msg='Members should be unique (article_id/partner_id)'):
            article.invite_members(self.partner_employee2 + self.partner_employee2, 'write')
        self.assertEqual(len(self.env['knowledge.article.member'].sudo().search([('article_id', '=', article.id)])), 1)

        with self.assertRaises(IntegrityError,
                               msg='Members should be unique (article_id/partner_id)'):
            article.sudo().write({
                'article_member_ids': [(0, 0, {'partner_id': self.partner_admin.id,
                                               'permission': 'write'}),
                                       (0, 0, {'partner_id': self.partner_admin.id,
                                               'permission': 'write'})
                                      ],
            })
        self.assertEqual(len(self.env['knowledge.article.member'].sudo().search([('article_id', '=', article.id)])), 1)

    @mute_logger('odoo.sql_db')
    @users('employee')
    def test_article_item_create(self):
        with self.assertRaises(IntegrityError, msg='Cannot create an article item without parent'):
            self.env['knowledge.article'].create([{
                'internal_permission': False,
                'name': 'Orphan Item',
                'parent_id': False,
                'is_article_item': True,
            }])

        # Checking children.
        self.assertEqual(len(self.items_parent.child_ids), 1)
        self.assertTrue(self.items_parent.has_item_children)

        # Can create an article item under a parent of items
        self.env['knowledge.article'].create([{
            'internal_permission': False,
            'name': 'Child Item 2',
            'parent_id': self.items_parent.id,
            'is_article_item': True,
        }])
        self.assertEqual(len(self.items_parent.child_ids), 2)
        self.assertTrue(self.items_parent.has_item_children)

        # Can create a normal article under a parent of items
        self.env['knowledge.article'].create([{
            'internal_permission': False,
            'name': 'Child Item 3',
            'parent_id': self.items_parent.id,
            'is_article_item': False,
        }])

        # Can create an article item under parent with no child. A parent item can be an item itself.
        self.assertTrue(len(self.item_child.child_ids) == 0)
        self.env['knowledge.article'].create([{
            'internal_permission': False,
            'name': 'grand child item',
            'parent_id': self.item_child.id,
            'is_article_item': True,
        }])
        self.assertEqual(len(self.item_child.child_ids), 1)
        self.assertTrue(self.item_child.has_item_children)

    @mute_logger('odoo.sql_db')
    @users('employee')
    def test_article_item_write(self):
        # Can move an article item under any parent
        # - Under an item parent: it stays an article item
        items_parent_2 = self.env['knowledge.article'].create([{
            'internal_permission': 'write',
            'name': 'item parent 2',
            'parent_id': False,
        }])
        self.env['knowledge.article'].create([{
            'internal_permission': False,
            'name': 'item child 2',
            'parent_id': items_parent_2.id,
            'is_article_item': True,
        }])
        self.item_child.move_to(items_parent_2.id)
        self.assertTrue(self.item_child.is_article_item)

        # - Under a parent that is not an item parent and has no children :
        #     it stays an article item and the parent becomes an item parent
        self.assertTrue(len(self.shared_child.child_ids) == 0)
        self.item_child.move_to(self.shared_child.id)
        self.assertTrue(self.item_child.is_article_item)
        self.assertEqual(len(self.shared_child.child_ids), 1)
        self.assertTrue(self.shared_child.has_item_children)

        # - Under a parent that is not an item parent and already has children :
        #     it stays an article item - both types can co-exist.
        self.env['knowledge.article'].create([{
            'internal_permission': False,
            'name': 'workspace child',
            'parent_id': self.article_workspace.id,
            'is_article_item': False,
        }])
        self.assertEqual(len(self.article_workspace.child_ids), 1)
        self.assertTrue(self.article_workspace.has_article_children)

        self.item_child.move_to(self.article_workspace.id)

        self.assertTrue(self.item_child.is_article_item)
        self.assertEqual(len(self.article_workspace.child_ids), 2)
        self.assertTrue(self.article_workspace.has_article_children)

        with self.assertRaises(IntegrityError, msg='An article item must have a parent'):
            self.item_child.write({'parent_id': False})

        # Can move a normal article under an item parent: the article stays a normal article
        self.item_child.write({'is_article_item': False})
        self.assertFalse(self.item_child.is_article_item)
        self.item_child.move_to(items_parent_2.id)
        self.assertFalse(self.item_child.is_article_item)
