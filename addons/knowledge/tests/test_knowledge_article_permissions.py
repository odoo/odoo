# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.knowledge.tests.common import KnowledgeArticlePermissionsCase
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('knowledge_acl')
class TestKnowledgeArticlePermissions(KnowledgeArticlePermissionsCase):

    @users('employee')
    def test_article_main_parent(self):
        """ Test root article computation """
        article_roots = self.article_roots.with_env(self.env)

        articles_write = (self.article_write_contents + self.article_write_contents_children).with_env(self.env)
        self.assertEqual(articles_write.root_article_id, article_roots[0])

        articles_write = self.article_read_contents.with_env(self.env)
        self.assertEqual(articles_write.root_article_id, article_roots[1])

        # desynchronized still have a root (do as sudo)
        self.assertEqual(self.article_write_desync.root_article_id, article_roots[0])
        self.assertEqual(self.article_read_desync.root_article_id, article_roots[1])

    def test_article_permissions_desync(self):
        """ Test computed fields based on permissions (independently from ACLs
        aka not user_permission, ...). Main use cases: desynchronized articles
        or articles without parents. """
        for (exp_inherited_permission,
             exp_inherited_permission_parent_id,
             exp_internal_permission
            ), article in zip(
                [('read', self.env['knowledge.article'], 'read'),
                 ('read', self.article_write_desync[0], False),
                 ('none', self.env['knowledge.article'], 'none'),
                 ('none', self.article_read_desync[0], False),
                 ('write', self.env['knowledge.article'], 'write'),
                 ('read', self.env['knowledge.article'], 'read'),
                ],
                self.article_write_desync + self.article_read_desync + self.article_roots
            ):
            self.assertEqual(article.inherited_permission, exp_inherited_permission,
                             f'Permission: wrong inherit computation for {article.name}: {article.inherited_permission} instead of {exp_inherited_permission}')
            self.assertEqual(article.inherited_permission_parent_id, exp_inherited_permission_parent_id,
                             f'Permission: wrong inherit computation for {article.name}: {article.inherited_permission_parent_id.name} instead of {exp_inherited_permission_parent_id.name}')
            self.assertEqual(article.internal_permission, exp_internal_permission,
                             f'Permission: wrong inherit computation for {article.name}: {article.internal_permission} instead of {exp_internal_permission}')

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_article_permissions_inheritance_desync(self):
        """ Test desynchronize (and therefore member propagation that should be
        stopped). """
        article_desync = self.article_write_desync[0]
        self.assertMembers(article_desync, 'read', {self.partner_employee_manager: 'write'})

        # as employee w write perms
        article_desync = article_desync.with_user(self.user_employee_manager)
        self.assertTrue(article_desync.user_has_write_access)
        self.assertTrue(article_desync.user_has_access)

        # as employee
        article_desync = article_desync.with_user(self.user_employee)
        self.assertFalse(article_desync.user_has_write_access)
        self.assertTrue(article_desync.user_has_access)

        # as portal
        article_desync = article_desync.with_user(self.user_portal)
        self.assertFalse(article_desync.user_has_write_access)
        self.assertFalse(article_desync.user_has_access, 'Permissions: member rights should not be fetch on parents')

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_article_permissions_inheritance_employee(self):
        article_roots = self.article_roots.with_env(self.env)

        # roots: based on internal permissions
        self.assertEqual(article_roots.mapped('user_has_write_access'), [True, False, False, True])
        self.assertEqual(article_roots.mapped('user_has_access'), [True, True, True, True])
        self.assertEqual(article_roots.mapped('user_permission'), ['write', 'read', 'read', 'write'])

        # write permission from ancestors
        article_write_ancestor = self.article_write_contents[2].with_env(self.env)
        self.assertEqual(article_write_ancestor.inherited_permission, 'write')
        self.assertEqual(article_write_ancestor.inherited_permission_parent_id, self.article_roots[0])
        self.assertFalse(article_write_ancestor.internal_permission)
        self.assertEqual(article_write_ancestor.user_permission, 'write')

        # write permission from ancestors overridden by internal permission
        article_read_forced = self.article_write_contents[1].with_env(self.env)
        self.assertEqual(article_read_forced.inherited_permission, 'read')
        self.assertFalse(article_read_forced.inherited_permission_parent_id)
        self.assertEqual(article_read_forced.internal_permission, 'read')
        self.assertEqual(article_read_forced.user_permission, 'read')

        # write permission from ancestors overridden by member permission
        article_read_member = self.article_write_contents[0].with_env(self.env)
        self.assertEqual(article_read_member.inherited_permission, 'write')
        self.assertEqual(article_read_member.inherited_permission_parent_id, self.article_roots[0])
        self.assertFalse(article_read_member.internal_permission)
        self.assertEqual(article_read_member.user_permission, 'read')

        # forced lower than base article perm (see 'Community Paranoïa')
        article_lower = self.article_read_contents[1].with_env(self.env)
        self.assertEqual(article_lower.inherited_permission, 'write')
        self.assertFalse(article_lower.inherited_permission_parent_id)
        self.assertEqual(article_lower.internal_permission, 'write')
        self.assertEqual(article_lower.user_permission, 'read')

        # read permission from ancestors
        article_read_ancestor = self.article_read_contents[2].with_env(self.env)
        self.assertEqual(article_read_ancestor.inherited_permission, 'read')
        self.assertEqual(article_read_ancestor.inherited_permission_parent_id, self.article_roots[1])
        self.assertFalse(article_read_ancestor.internal_permission)
        self.assertEqual(article_read_ancestor.user_permission, 'read')

        # permission denied
        article_none = self.article_read_contents[3].with_env(self.env)
        with self.assertRaises(exceptions.AccessError):
            article_none.name

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('portal_test')
    def test_article_permissions_inheritance_portal(self):
        article_roots = self.article_roots.with_env(self.env)

        with self.assertRaises(exceptions.AccessError):
            article_roots.mapped('internal_permission')

        article_members = self.article_read_contents[0:2].with_env(self.env)
        self.assertEqual(article_members.mapped('inherited_permission'), ['write', 'write'])  # TDE: TOCHECK
        self.assertEqual(article_members.mapped('internal_permission'), ['write', 'write'])  # TDE: TOCHECK
        self.assertEqual(article_members.mapped('user_has_write_access'), [False, False], 'Portal: can never write')
        self.assertEqual(article_members.mapped('user_has_access'), [True, True], 'Portal: access through membership')
        self.assertEqual(article_members.mapped('user_permission'), ['read', 'read'])

    @users('employee')
    def test_article_permissions_employee_new_mode(self):
        """ Test transient / cache mode: computed fields without IDs, ... """
        article = self.env['knowledge.article'].new({'name': 'Transient'})
        self.assertFalse(article.inherited_permission)
        self.assertFalse(article.internal_permission)
        self.assertTrue(article.user_has_write_access)
        self.assertTrue(article.user_has_access)
        self.assertEqual(article.user_permission, 'write')


@tagged('knowledge_internals', 'knowledge_management')
class KnowledgeArticlePermissionsInitialValues(KnowledgeArticlePermissionsCase):
    """ Test initial values or our test data once so that other tests do not have
    to do it. """

    def test_initial_values(self):
        article_roots = self.article_roots.with_env(self.env)
        article_headers = self.article_headers.with_env(self.env)

        # roots: defaults on write, inherited = internal
        self.assertEqual(article_roots.mapped('inherited_permission'), ['write', 'read', 'none', 'none'])
        self.assertFalse(article_roots.inherited_permission_parent_id)
        self.assertEqual(article_roots.mapped('internal_permission'), ['write', 'read', 'none', 'none'])

        # childs: allow void permission, inherited = go up to first defined permission
        self.assertEqual(article_headers.mapped('inherited_permission'), ['write', 'read', 'read'])
        self.assertEqual(
            [p.inherited_permission_parent_id for p in article_headers],
            [article_roots[0], article_roots[1], article_roots[1]]
        )
        self.assertEqual(article_headers.mapped('internal_permission'), [False, False, False])

    @users('employee')
    def test_initial_values_as_employee(self):
        """ Ensure all tests have the same basis (user specific computed as
        employee for acl-dependent tests) """
        article_write_inherit = self.article_write_contents[2].with_env(self.env)

        # initial values: write through inheritance
        self.assertMembers(article_write_inherit, False, {self.partner_portal: 'read'})
        self.assertFalse(article_write_inherit.internal_permission)
        self.assertFalse(article_write_inherit.is_desynchronized)
        self.assertTrue(article_write_inherit.user_has_write_access)
        self.assertTrue(article_write_inherit.user_has_access)

        article_write_inherit_as2 = article_write_inherit.with_user(self.user_employee2)
        self.assertTrue(article_write_inherit_as2.user_has_write_access)
        self.assertTrue(article_write_inherit_as2.user_has_access)


@tagged('knowledge_acl')
class TestKnowledgeArticlePermissionsTools(KnowledgeArticlePermissionsCase):

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_downgrade_internal_permission_none(self):
        writable_as1 = self.article_write_contents[2].with_env(self.env)
        writable_as2 = writable_as1.with_user(self.user_employee2)
        self.assertEqual(writable_as2.user_has_access, True)

        # downgrade write global perm to read
        writable_as1._set_internal_permission('none')
        writable_as1.flush_model()  # ACLs are done using SQL
        self.assertMembers(
            writable_as1, 'none',
            {self.partner_portal: 'read',  # untouched by downgrade
             self.env.user.partner_id: 'write'},
            'Permission: lowering permission adds current user in members to have write access'
        )
        self.assertTrue(writable_as1.is_desynchronized)
        self.assertTrue(writable_as1.user_has_write_access)
        self.assertTrue(writable_as1.user_has_access)

        # check internal permission has been lowered
        with self.assertRaises(exceptions.AccessError):
            writable_as2.body  # trigger ACLs

    @users('employee')
    def test_downgrade_internal_permission_read(self):
        writable_as1 = self.article_write_contents[2].with_env(self.env)
        writable_as2 = writable_as1.with_user(self.user_employee2)
        self.assertEqual(writable_as2.user_has_access, True)

        # downgrade write global perm to read
        writable_as1._set_internal_permission('read')
        writable_as1.flush_model()  # ACLs are done using SQL
        self.assertMembers(
            writable_as1, 'read',
            {self.partner_portal: 'read', self.env.user.partner_id: 'write'},
            'Permission: lowering permission adds current user in members to have write access'
        )
        self.assertTrue(writable_as1.is_desynchronized)
        self.assertTrue(writable_as1.user_has_write_access)
        self.assertTrue(writable_as1.user_has_access)
        self.assertFalse(writable_as2.user_has_write_access)
        self.assertTrue(writable_as2.user_has_access)

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models.unlink')
    @users('employee')
    def test_remove_member_inherited_rights(self):
        """ Remove a member from a child inheriting rights: will desync """
        writable = self.article_write_contents[2].with_env(self.env)
        self.assertTrue(writable.user_has_access)
        self.assertTrue(writable.user_has_write_access)
        self.assertMembers(writable, False,
                           {self.partner_portal: 'read'})

        # set partner employee manager as writable member of its root
        writable_root = writable.root_article_id
        writable_root._add_members(self.partner_employee_manager, 'write')
        self.assertMembers(writable_root, 'write',
                           {self.partner_employee_manager: 'write'})

        # remove partner employee manager that has rights based on inheritance
        manager_member = writable_root.article_member_ids.filtered(lambda m: m.partner_id == self.partner_employee_manager)
        writable._remove_member(manager_member)
        self.assertTrue(writable.is_desynchronized,
                        'Permission: when removing a member having inherited rights it has be be desynchronized')
        self.assertMembers(writable, 'write',
                           {self.partner_portal: 'read'})

        # resync
        writable.restore_article_access()
        self.assertFalse(writable.is_desynchronized)
        self.assertMembers(writable, False,
                           {self.partner_portal: 'read'})

        # remove portal partner that has rights based on membership
        portal_member = writable.article_member_ids.filtered(lambda m: m.partner_id == self.partner_portal)
        writable._remove_member(portal_member)
        self.assertFalse(writable.is_desynchronized)
        self.assertMembers(writable, False, {})

    @mute_logger('odoo.models.unlink')
    @users('employee')
    def test_set_member_permission(self):
        """ Test setting member-specific permission """
        writable = self.article_write_contents[2].with_env(self.env)
        self.assertTrue(writable.user_has_access)
        self.assertTrue(writable.user_has_write_access)

        # set partner employee manager as readable member of its root
        writable_root = writable.root_article_id
        writable_root._add_members(self.partner_employee_manager, 'read')
        self.assertMembers(writable_root, 'write',
                           {self.partner_employee_manager: 'read'})

        # update a member permission directly
        portal_member = writable.article_member_ids.filtered(lambda m: m.partner_id == self.partner_portal)
        writable._set_member_permission(portal_member, 'none')
        self.assertMembers(writable, False,
                           {self.partner_portal: 'none'})

        # upgrade a permission based on inheritance
        manager_member_root = writable_root.article_member_ids.filtered(lambda m: m.partner_id == self.partner_employee_manager)
        writable._set_member_permission(manager_member_root, 'write', is_based_on=True)
        self.assertFalse(writable.is_desynchronized)
        self.assertMembers(writable, False,
                           {self.partner_portal: 'none',
                            self.partner_employee_manager: 'write'})

        # now test downgrading
        manager_member = writable.article_member_ids.filtered(lambda m: m.partner_id == self.partner_employee_manager)
        writable_root._set_member_permission(manager_member_root, 'write')
        writable._remove_member(manager_member)
        self.assertMembers(writable_root, 'write',
                           {self.partner_employee_manager: 'write'})
        self.assertMembers(writable, False,
                           {self.partner_portal: 'none'})

        # downgrade a permission, should desynchronize from parent
        writable._set_member_permission(manager_member_root, 'read', is_based_on=True)
        self.assertTrue(writable.is_desynchronized,
                        'Permission: when removing a member having inherited rights it has be be desynchronized')
        self.assertMembers(writable, 'write',
                           {self.partner_portal: 'none',
                            self.partner_employee_manager: 'read'})

    @mute_logger('odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_update_internal_permission_escalation(self):
        """ Check no privilege escalation is possible """
        # direct try at setting higher internal permission
        readonly = self.article_read_contents[1].with_env(self.env)
        self.assertTrue(readonly.user_has_access)
        self.assertFalse(readonly.user_has_write_access)
        writable = self.article_write_contents[2].with_env(self.env)
        self.assertTrue(writable.user_has_access)
        self.assertTrue(writable.user_has_write_access)

        with self.assertRaises(exceptions.AccessError,
                               msg='Permission: that is plain stupid trying to do this'):
            readonly.write({'internal_permission': 'write'})
        with self.assertRaises(exceptions.AccessError,
                               msg='Permission: do not allow privilege escalation'):
            readonly._set_internal_permission('write')

        portal_member = writable.article_member_ids.filtered(lambda m: m.partner_id == self.partner_portal)
        with self.assertRaises(exceptions.ValidationError,
                               msg='Permission: share partner cannot gain write access'):
            writable._set_member_permission(portal_member, 'write')

    @mute_logger('odoo.addons.base.models.ir_rule', 'odoo.models.unlink')
    @users('employee')
    def test_update_permissions_rights(self):
        """ Check no privilege escalation is possible """
        # direct try at setting higher internal permission
        readonly = self.article_read_contents[1].with_env(self.env)
        self.assertTrue(readonly.user_has_access)
        self.assertFalse(readonly.user_has_write_access)
        with self.assertRaises(exceptions.AccessError,
                               msg='Permission: that is plain stupid trying to do this'):
            readonly.write({'internal_permission': 'write'})
        with self.assertRaises(exceptions.AccessError,
                               msg='Permission: do not allow privilege escalation'):
            readonly._set_internal_permission('write')

        other_member = readonly.article_member_ids.filtered(lambda m: m.partner_id == self.partner_portal)
        with self.assertRaises(exceptions.AccessError,
                               msg='Permission: do not allow to remove members when having only read access'):
            readonly._remove_member(other_member)
        self.assertMembers(readonly, 'write',
                           {self.env.user.partner_id: 'read',
                            self.partner_portal: 'read'})

        # cannot gain privilege: setting none if I remove myself to ensure no gain is performed
        my_member = readonly.article_member_ids.filtered(lambda m: m.partner_id == self.env.user.partner_id)
        readonly._remove_member(my_member)
        self.assertMembers(readonly, 'write',
                           {self.env.user.partner_id: 'none',
                            self.partner_portal: 'read'})


@tagged('knowledge_acl')
class TestKnowledgeArticleSearch(KnowledgeArticlePermissionsCase):

    @users('admin')
    def test_article_search_admin(self):
        """ Test admin: can read / write everything but user_has_access and
        user_has_write_access should still be based on real permissions. """
        self.assertTrue(self.env.user.has_group('base.group_system'))
        articles = self.env['knowledge.article'].search([])
        expected = self.articles_all
        self.assertEqual(articles, expected,
                         'Search on user_has_write_access: aka write access (additional: %s, missing: %s)' %
                         ((articles - expected).mapped('name'), (expected - articles).mapped('name'))
                        )

        articles = self.env['knowledge.article'].search([('user_has_write_access', '=', True)])
        expected = self.article_roots[0] + self.article_headers[0] + \
                   self.article_write_contents[0] + self.article_write_contents[2] + \
                   self.article_write_contents_children + \
                   self.article_read_contents[0:2]
        self.assertEqual(articles, expected,
                         'Search on user_has_write_access: aka write access (additional: %s, missing: %s)' %
                         ((articles - expected).mapped('name'), (expected - articles).mapped('name'))
                        )

    @users('employee')
    def test_article_search_employee(self):
        """ Test regular searches using permission-based ACLs """
        # explicitly remove an article, check it is not included (nor its child)
        self.article_write_desync[0].write({
            'article_member_ids': [
                (0, 0, {'partner_id': self.user_employee.partner_id.id,
                        'permission': 'none'})]
        })
        articles = self.env['knowledge.article'].search([])
        # not reachable: 'none', desynchronized 'none' (and their children)
        expected = self.articles_all - self.article_read_contents[3] - self.article_write_desync
        self.assertEqual(articles, expected,
                         'Search on main article: aka everything except "none"-based articles (additional: %s, missing: %s)' %
                         ((articles - expected).mapped('name'), (expected - articles).mapped('name'))
                        )

        # add its child as readable through membership and perform a new search
        self.article_write_desync[1].write({
            'article_member_ids': [
                (0, 0, {'partner_id': self.user_employee.partner_id.id,
                        'permission': 'read'})]
        })

        articles = self.env['knowledge.article'].search([('root_article_id', '=', self.article_roots[0].id)])
        expected = self.article_roots[0] + self.article_headers[0] + \
                   self.article_write_contents + self.article_write_contents_children + self.article_write_desync[1]
        self.assertEqual(articles, expected,
                         'Search on main article: aka read access on read root + its children (additional: %s, missing: %s)' %
                         ((articles - expected).mapped('name'), (expected - articles).mapped('name'))
                        )

    @users('employee')
    def test_article_search_employee_method_based(self):
        """ Test search methods """
        articles = self.env['knowledge.article'].search([('user_has_write_access', '=', True)])
        expected = self.article_roots[0] + self.article_roots[3] + \
                   self.article_headers[0] + \
                   self.article_write_contents[2] + self.article_write_contents_children + \
                   self.article_read_contents[0] + self.article_read_desync
        self.assertEqual(articles, expected,
                         'Search on user_has_write_access: aka write access (additional: %s, missing: %s)' %
                         ((articles - expected).mapped('name'), (expected - articles).mapped('name'))
                        )
