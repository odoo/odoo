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

        # - Playground     seq=20    workspace    w+      (admin-w+)
        # - Shared         seq=21    shared       none    (admin-w+,employee-r+,manager-r+)
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

    @users('employee')
    def test_article_acyclic_graph(self):
        """ Check that the article hierarchy does not contain cycles. """
        article = self.article_workspace.with_env(self.env)
        article_childs = self.env['knowledge.article'].create([
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
        with self.assertRaises(exceptions.ValidationError, msg='The article hierarchy contains a cycle'):
            article.move_to(parent_id=article_childs[1].id)
        with self.assertRaises(exceptions.ValidationError, msg='The article hierarchy contains a cycle'):
            article.write({
                'parent_id': article_childs[1].id
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
        self.assertEqual(private.sequence, 22)

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

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_private_management(self):
        """ Checking the article private management. """
        article_workspace = self.article_workspace.with_env(self.env)

        # Private-like article whoe parent is not in private category is under workspace
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

        # Moving a private article under a workspace category makes it workspace
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
        article_private_asu2 = article_private.with_user(self.user_employee2)
        # Still not accessible
        with self.assertRaises(exceptions.AccessError):
            article_private_asu2.body  # should trigger ACLs

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
        # cannot remove last writer
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            membership_sudo.unlink()
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            article_private.sudo()._remove_member(membership_sudo)
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            article_private.sudo().write({
                'article_member_ids': self.env['knowledge.article.member']
            })
        with self.assertRaises(exceptions.ValidationError, msg='Cannot remove the last writer on an article'):
            article_private.sudo().write({
                'article_member_ids': [(2, membership_sudo.id)]
            })

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

        # moving the article to private will remove the second member
        # but should not trigger an error since we also add 'employee' as a write member
        article_workspace = self.article_workspace.with_env(self.env)
        article_workspace.move_to(is_private=True)
        self.assertEqual(article_workspace.category, 'private')
        self.assertTrue(article_workspace._has_write_member())

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
        article.write({'favorite_ids': [(0, 0, {'user_id': self.env.user.id})]})
        self.assertTrue(article.is_user_favorite)
        with self.assertRaises(IntegrityError,
                               msg='Multiple favorite entries are not accepted'):
            article.write({'favorite_ids': [(0, 0, {'user_id': self.env.user.id})]})
        self.assertTrue(article.is_user_favorite)

    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.tests')
    @users('employee')
    def test_member_share_restrictions(self):
        """Checking that the external partner can not have 'write' access."""
        article = self._create_private_article('MyPrivate')
        self.assertEqual(article.category, 'private')

        customer = self.customer.with_env(self.env)
        self.assertTrue(customer.partner_share)

        # check that an external partner can not have "write" permission
        with self.assertRaises(exceptions.ValidationError,
                               msg='An external partner can not have "write" permission on an article'):
            article.sudo().write({
                'article_member_ids': [(0, 0, {
                    'partner_id': customer.id,
                    'permission': 'write'
                })]
            })
        article.invite_members(customer, 'write')
        self.assertMembers(article, 'none',
                           {self.env.user.partner_id: 'write',
                            customer: 'read'},
                           msg='Invite: share should not gain write access')

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
