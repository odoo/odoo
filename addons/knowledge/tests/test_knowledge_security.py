# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.knowledge.tests.common import KnowledgeArticlePermissionsCase
from odoo.tests.common import tagged, users
from odoo.tools import mute_logger


@tagged('knowledge_acl')
class TestKnowledgeSecurity(KnowledgeArticlePermissionsCase):
    """ Tests ACLs and low level access on models. Do not test the internals
    of permission comuptation as those are done in another test suite. Here
    we rely on them to check the create/read/write/unlink access checks. """

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('user_public')
    def test_models_as_public(self):
        # ARTICLE
        with self.assertRaises(exceptions.AccessError, msg='ACLs: No article access to public'):
            self.env['knowledge.article'].search([])

        # FAVORITES
        with self.assertRaises(exceptions.AccessError, msg='ACLs: No favorite access to public'):
            self.env['knowledge.article.favorite'].search([])

        # MEMBERS
        with self.assertRaises(exceptions.AccessError, msg='ACLs: No member access to public'):
            self.env['knowledge.article.member'].search([])

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('portal_test')
    def test_models_as_portal(self):
        article_root = self.article_roots[0].with_env(self.env)

        # ARTICLES
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: No access given to portal"):
            article_root.body  # access body should trigger acls

        article_shared = self.article_roots[2].with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: Internal permission 'none', not for portal"):
            article_shared.body  # access body should trigger acls

        article_accessible = self.article_write_contents[2].with_env(self.env)
        self.assertEqual(article_accessible.body, '<p>Writable Subarticle through inheritance</p>',
                        "ACLs: should be accessible due to explicit 'read' member permission")
        self.assertTrue(article_accessible.is_user_favorite)

        # FAVORITES
        favs = self.env['knowledge.article.favorite'].search([])
        self.assertEqual(len(favs), 1)
        self.assertEqual(favs.article_id, article_accessible)
        sudo_favorites = self.article_roots.favorite_ids.with_env(self.env)
        self.assertEqual(len(sudo_favorites), 2)
        with self.assertRaises(exceptions.AccessError,
                               msg='ACLs: Breaking rule for portal'):
            sudo_favorites.mapped('user_id')  # access body should trigger acls

        # MEMBERS
        my_members = self.env['knowledge.article.member'].search([])
        self.assertEqual(len(my_members), 3)
        self.assertEqual(my_members.partner_id, self.env.user.partner_id)
        sudo_members = self.article_roots.article_member_ids.with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg='Breaking rule for portal'):
            sudo_members.mapped('partner_id')  # access body should trigger acls

    @mute_logger('odoo.models.unlink')
    @users('admin')
    def test_models_as_system(self):
        self.assertTrue(self.env.user.has_group('base.group_system'))

        article_roots = self.article_roots.with_env(self.env)
        article_roots.mapped('body')  # access body should trigger acls
        article_hidden = self.article_read_contents[3].with_env(self.env)
        article_hidden.body  # access body should trigger acls

        # ARTICLE: CREATE/READ
        # create a private article for another user
        other_private = self.env['knowledge.article'].create({
            'article_member_ids': [(0, 0, {
                'partner_id': self.partner_employee.id,
                'permission': 'write',
            })],
            'internal_permission': 'none',
            'name': 'Private for Employee',
        })
        self.assertMembers(other_private, 'none', {self.partner_employee: 'write'})
        self.assertEqual(other_private.category, 'private')
        self.assertFalse(other_private.user_has_write_access, 'Can write based on permission is False but can perform write due to ACLs')
        other_private.write({'name': 'Admin can do everything'})

        # create a child to it
        other_private_child = self.env['knowledge.article'].create({
            'name': 'Child of Private for Employee',
            'parent_id': other_private.id,
        })
        self.assertMembers(other_private_child, False, {})
        self.assertEqual(other_private_child.article_member_ids.partner_id, self.env['res.partner'])
        self.assertEqual(other_private_child.category, 'private')
        self.assertFalse(other_private_child.user_has_write_access, 'Can write based on permission is False but can perform write due to ACLs')

        # ARTICLE: WRITE
        other_private.write({'name': 'Can Update'})
        other_private_child.write({'name': 'Can Also Update'})

        # FAVORITES: CREATE/READ/UNLINK
        other_private_child.action_toggle_favorite()
        self.assertTrue(other_private_child.is_user_favorite)
        favorite_rec = self.env['knowledge.article.favorite'].search([('article_id', '=', other_private_child.id)])
        favorite_rec.unlink()
        self.assertFalse(other_private_child.is_user_favorite)

        # MEMBERS: CREATE/READ/UNLINK
        members = other_private.article_member_ids
        self.assertEqual(members.partner_id, self.partner_employee)
        new_member = self.env['knowledge.article.member'].create({
            'article_id': other_private.id,
            'partner_id': self.partner_employee2.id,
            'permission': 'read',
        })
        members = other_private.article_member_ids
        self.assertEqual(members.partner_id, self.partner_employee + self.partner_employee2)
        new_member.write({'permission': 'write'})
        members.filtered(lambda m: m.partner_id == self.partner_employee).unlink()
        members = other_private.article_member_ids
        self.assertEqual(members, new_member)
        self.assertEqual(members.partner_id, self.partner_employee2)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_models_as_user(self):
        article_roots = self.article_roots.with_env(self.env)

        # ARTICLES
        article_roots.mapped('body')  # access body should trigger acls
        article_roots[0].write({'name': 'Hacked (or not)'})
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: 'read' internal permission"):
            article_roots[1].write({'name': 'Hacked'})
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: 'read' member permission"):
            article_roots[2].write({'name': 'Hacked'})

        article_hidden = self.article_read_contents[3].with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: 'none' internal permission"):
            article_hidden.body  # access body should trigger acls

        # FAVORITES
        my_favs = self.env['knowledge.article.favorite'].search([])
        self.assertEqual(
            my_favs,
            self.articles_all.favorite_ids.filtered(lambda f: f.user_id == self.env.user),
            'Favorites: employee should see its own favorites'
        )
        my_favs.mapped('user_id')  # access body should trigger acls
        my_favs.write({'sequence': 0})
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: should not be used to change article/user"):
            my_favs[0].write({'article_id': article_roots[0].id})
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: should not be used to change article/user"):
            my_favs[0].write({'user_id': self.user_portal.id})

        # MEMBERS
        my_members = self.env['knowledge.article.member'].search([('article_id', 'in', self.article_roots.ids)])
        self.assertEqual(len(my_members), 4)
        self.assertEqual(
            my_members,
            self.article_roots.article_member_ids,
            'Members: employee should memberships of visible '
        )
        # remove employee from Shared root, check they cannot read those members
        self.article_roots[2].article_member_ids.filtered(lambda m: m.partner_id == self.partner_employee).unlink()
        my_members = self.env['knowledge.article.member'].search([('article_id', 'in', self.article_roots.ids)])
        self.assertEqual(len(my_members), 2)
        self.assertEqual(
            my_members,
            (self.article_roots[1] + self.article_roots[3]).article_member_ids,
            'Members: employee should see its own memberships'
        )
        my_members.mapped('partner_id')  # access body should trigger acls
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: no ACLs for write for user"):
            my_members.write({'permission': 'write'})

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.addons.base.models.ir_rule')
    @users('employee')
    def test_models_as_user_copy(self):
        article_hidden = self.article_read_contents[3].with_env(self.env)
        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: 'none' internal permission"):
            article_hidden.body  # access body should trigger acls

        with self.assertRaises(exceptions.AccessError,
                               msg="ACLs: copy should not allow to access hidden articles"):
            _new_article = article_hidden.copy()

        article_root_readonly = self.article_roots[0].with_env(self.env)
        new_article = article_root_readonly.copy()
        self.assertEqual(new_article.name, f'{article_root_readonly.name} (copy)')
