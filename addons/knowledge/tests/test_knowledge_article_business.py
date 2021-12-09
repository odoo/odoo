# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo import exceptions
from odoo.addons.knowledge.tests.common import KnowledgeCommonWData
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('knowledge_internals', 'knowledge_management')
class TestKnowledgeArticleBusiness(KnowledgeCommonWData):
    """ Test business API and main tools or helpers methods. """

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_archive(self):
        """ Testing archive that should also archive children. """
        article_shared = self.article_shared.with_env(self.env)
        article_workspace = self.article_workspace.with_env(self.env)
        wkspace_children = self.workspace_children.with_env(self.env)
        # to test descendants computation, add some sub children
        wkspace_grandchildren = self.env['knowledge.article'].create([
            {'name': 'Grand Children of workspace',
             'parent_id': wkspace_children[0].id,
            },
            {'name': 'Grand Children of workspace',
             'parent_id': wkspace_children[0].id,
            },
            {'name': 'Grand Children of workspace',
             'parent_id': wkspace_children[1].id,
            }
        ])
        wkspace_grandgrandchildren = self.env['knowledge.article'].create([
            {'name': 'Grand Grand Children of workspace',
             'parent_id': wkspace_grandchildren[1].id,
            },
            {'name': 'Grand Children of workspace',
             'parent_id': wkspace_grandchildren[2].id,
            },
        ])

        # no read access -> cracboum
        with self.assertRaises(exceptions.AccessError,
                               msg='Employee can read thus not archive'):
            article_shared.action_archive()

        # set the root + children inactive
        article_workspace.action_archive()
        self.assertFalse(article_workspace.active)
        for article in wkspace_children + wkspace_grandchildren + wkspace_grandgrandchildren:
            self.assertFalse(article.active, 'Archive: should propagate to children')
            self.assertEqual(article.root_article_id, article_workspace,
                             'Archive: does not change hierarchy when archiving without breaking hierarchy')

        # reset as active
        (article_workspace + wkspace_children + wkspace_grandchildren + wkspace_grandgrandchildren).toggle_active()
        for article in article_workspace + wkspace_children + wkspace_grandchildren + wkspace_grandgrandchildren:
            self.assertTrue(article.active)

        # set only part of tree inactive
        wkspace_children.action_archive()
        self.assertTrue(article_workspace.active)
        for article in wkspace_children + wkspace_grandchildren + wkspace_grandgrandchildren:
            self.assertFalse(article.active, 'Archive: should propagate to children')

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_archive_mixed_rights(self):
        """ Test archive in case of mixed rights """
        # give write access to shared section, but have children in read or none
        self.article_shared.article_member_ids.sudo().filtered(
            lambda article: article.partner_id == self.partner_employee
        ).write({'permission': 'write'})
        # one additional read child and one additional none child
        self.shared_children += self.env['knowledge.article'].sudo().create([
            {'article_member_ids': [
                (0, 0, {'partner_id': self.partner_admin.id,
                        'permission': 'write',
                       }),
                (0, 0, {'partner_id': self.partner_employee.id,
                        'permission': 'read',
                       }),
             ],
             'internal_permission': False,
             'name': 'Shared Child2',
             'parent_id': self.article_shared.id,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': self.partner_admin.id,
                        'permission': 'write',
                       }),
                (0, 0, {'partner_id': self.partner_employee.id,
                        'permission': 'none',
                       }),
             ],
             'internal_permission': False,
             'name': 'Shared Child3',
             'parent_id': self.article_shared.id,
            },
        ])

        # prepare comparison data as sudo
        writable_child_su = self.article_shared.child_ids.filtered(lambda article: article.name in ['Shared Child1'])
        readonly_child_su = self.article_shared.child_ids.filtered(lambda article: article.name in ['Shared Child2'])
        hidden_child_su = self.article_shared.child_ids.filtered(lambda article: article.name in ['Shared Child3'])

        # perform archive as user
        article_shared = self.article_shared.with_env(self.env)
        article_shared.invalidate_cache(fnames=['child_ids'])  # context dependent
        shared_children = article_shared.child_ids
        writable_child, readonly_child = writable_child_su.with_env(self.env), readonly_child_su.with_env(self.env)
        self.assertEqual(len(shared_children), 2)
        self.assertEqual(shared_children, writable_child + readonly_child, 'Should see only two first children')

        article_shared.action_archive()
        # check writable articles have been archived, readonly or hidden not
        self.assertFalse(article_shared.active)
        self.assertFalse(writable_child.active)
        self.assertTrue(readonly_child.active)
        self.assertTrue(hidden_child_su.active)
        # check hierarchy
        self.assertEqual(writable_child.parent_id, article_shared,
                         'Archive: archived articles hierarchy does not change')
        self.assertFalse(readonly_child.parent_id, 'Archive: article should be extracted in archive process as non writable')
        self.assertEqual(readonly_child.root_article_id, readonly_child)
        self.assertFalse(hidden_child_su.parent_id, 'Archive: article should be extracted in archive process as non writable')
        self.assertEqual(hidden_child_su.root_article_id, hidden_child_su)

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_create(self):
        """ Testing the helper to create articles with right values. """
        Article = self.env['knowledge.article']
        article = self.article_workspace.with_env(self.env)
        readonly_article = self.article_shared.with_env(self.env)

        _title = 'Fthagn'
        new = Article.article_create(title=_title, parent_id=False, is_private=False)
        self.assertMembers(new, 'write', {})
        self.assertFalse(new.article_member_ids)
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
        _title = 'Fthagn, but with parent private none: cracboum'
        with self.assertRaises(exceptions.AccessError):
            Article.article_create(title=_title, parent_id=private_nonmember.id, is_private=False)

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.addons.mail.models.mail_mail', 'odoo.models.unlink', 'odoo.tests')
    @users('employee')
    def test_article_invite_members(self):
        """ Test inviting members API. Create a hierarchy of 3 shared articles
        and check privilege is not granted below invited articles. """
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
             'parent_id': self.shared_children.id,
            },
            {'article_member_ids': [
                (0, 0, {'partner_id': self.partner_employee.id,
                        'permission': 'write',
                       }),
             ],
             'internal_permission': False,
             'name': 'Shared Writable Child (propagate is ok)',
             'parent_id': self.shared_children.id,
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

        shared_article = self.shared_children.with_env(self.env)
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
                            self.customer: 'read',  # shared partners are always read only
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
        shared_article.with_user(self.user_employee2).check_access_rule('write')
        direct_child_write.with_user(self.user_employee2).check_access_rule('write')
        with self.assertRaises(exceptions.AccessError,
                               msg='Invite: access should have been blocked'):
            direct_child_read.with_user(self.user_employee2).check_access_rule('read')
        with self.assertRaises(exceptions.AccessError,
                               msg='Invite: access should have been blocked'):
            grand_child.with_user(self.user_employee2).check_access_rule('read')

        # employee2 is downgraded, employee_manager is removed
        with self.mock_mail_gateway():
            shared_article.invite_members(partners[2], 'read')
        with self.mock_mail_gateway():
            shared_article.invite_members(partners[1], 'none')

        self.assertMembers(shared_article, False,
                           {self.partner_employee: 'write',
                            self.customer: 'read',
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
        when inviting people. """
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
        playground_articles.invalidate_cache(fnames=['is_user_favorite'])
        self.assertEqual(playground_articles.mapped('is_user_favorite'), [True, False, False])

        # correct uid-based computation
        playground_articles_asmanager = playground_articles.with_user(self.user_employee_manager)
        self.assertEqual(playground_articles_asmanager.mapped('is_user_favorite'), [False, False, False])

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
            article_shared[0].move_to(parent_id=False)

        # valid move: put second child of workspace under the first one
        workspace_children[1].move_to(parent_id=workspace_children[0].id)
        workspace_children.flush()
        self.assertEqual(article_workspace.child_ids, workspace_children[0])
        self.assertEqual(article_workspace._get_descendants(), workspace_children)
        self.assertEqual(workspace_children.root_article_id, article_workspace)
        self.assertEqual(workspace_children[1].parent_id, workspace_children[0])
        self.assertEqual(workspace_children[0].parent_id, article_workspace)

        # Test that desynced articles are resynced when moved to root
        workspace_children[0]._desync_access_from_parents()
        self.assertTrue(workspace_children[0].is_desynchronized)

        # other valid move: first child is moved to private section
        workspace_children[0].move_to(parent_id=False, is_private=True)
        workspace_children.flush()
        self.assertMembers(workspace_children[0], 'none', {self.partner_employee: 'write'})
        self.assertEqual(workspace_children[0].category, 'private')
        self.assertEqual(workspace_children[0].internal_permission, 'none')
        self.assertFalse(workspace_children[0].is_desynchronized)
        self.assertFalse(workspace_children[0].parent_id)
        self.assertEqual(workspace_children.root_article_id, workspace_children[0])

    @users('employee')
    def test_article_sort_for_user(self):
        """ Testing the sort + custom info returned by get_user_sorted_articles """
        self.workspace_children.write({
            'favorite_ids': [
                (0, 0, {'user_id': user.id})
                for user in self.user_admin + self.user_employee2 + self.user_employee_manager
            ],
        })
        article_workspace = self.article_workspace.with_env(self.env)
        workspace_children = self.workspace_children.with_env(self.env)
        (article_workspace + workspace_children[1]).action_toggle_favorite()

        new_root_child = self.env['knowledge.article'].create({
            'name': 'Child3 without parent name in its name',
            'parent_id': article_workspace.id,
        })
        (self.workspace_children + new_root_child).flush()

        # ensure initial values
        self.assertTrue(article_workspace.is_user_favorite)
        self.assertEqual(article_workspace.favorite_count, 2)
        self.assertEqual(article_workspace.user_favorite_sequence, 1)
        self.assertFalse(workspace_children[0].is_user_favorite)
        self.assertEqual(workspace_children[0].favorite_count, 3)
        self.assertEqual(workspace_children[0].user_favorite_sequence, -1)
        self.assertTrue(workspace_children[1].is_user_favorite)
        self.assertEqual(workspace_children[1].favorite_count, 4)
        self.assertEqual(workspace_children[1].user_favorite_sequence, 2)
        self.assertFalse(new_root_child.is_user_favorite)
        self.assertEqual(new_root_child.favorite_count, 0)
        self.assertEqual(new_root_child.user_favorite_sequence, -1)

        # search also includes descendants of articles having the term in their name
        result = self.env['knowledge.article'].get_user_sorted_articles('laygroun')
        expected = self.article_workspace + self.workspace_children[1] + self.workspace_children[0] + new_root_child
        found_ids = [a['id'] for a in result]
        self.assertEqual(found_ids, expected.ids)
        # check returned result once (just to be sure)
        workspace_info = next(article_result for article_result in result if article_result['id'] == article_workspace.id)
        self.assertTrue(workspace_info['is_user_favorite'], article_workspace.name)
        self.assertFalse(workspace_info['icon'])
        self.assertEqual(workspace_info['favorite_count'], 2)
        self.assertEqual(workspace_info['name'], article_workspace.name)
        self.assertEqual(workspace_info['root_article_id'], (article_workspace.id, f'📄 {article_workspace.name}'))


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
                article.with_user(self.user_employee2).flush()
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


@tagged('post_install', '-at_install', 'knowledge_internals', 'knowledge_management')
class TestKnowledgeShare(KnowledgeCommonWData):
    """ Test share feature. """

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
            self._new_msgs.body
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
