# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger
from odoo import Command


class TestRules(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        ObjCateg = cls.env['test_access_right.obj_categ']
        SomeObj = cls.env['test_access_right.some_obj']
        cls.categ = ObjCateg.create({'name': 'Food'})
        cls.allowed = SomeObj.create({'val': 1, 'categ_id': cls.categ.id})
        cls.forbidden = SomeObj.create({'val': -1, 'categ_id': cls.categ.id})
        # create a global rule forbidding access to records with a negative
        # (or zero) val
        cls.env['ir.rule'].create({
            'name': 'Forbid negatives',
            'model_id': cls.env.ref('test_access_rights.model_test_access_right_some_obj').id,
            'domain_force': "[('val', '>', 0)]"
        })
        # create a global rule that forbid access to records without
        # categories, the search is part of the test
        cls.env['ir.rule'].create({
            'name': 'See all categories',
            'model_id': cls.env.ref('test_access_rights.model_test_access_right_some_obj').id,
            'domain_force': "[('categ_id', 'in', user.env['test_access_right.obj_categ'].search([]).ids)]"
        })

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_basic_access(self):
        env = self.env(user=self.env.ref('base.public_user'))
        allowed = self.allowed.with_env(env)
        forbidden = self.forbidden.with_env(env)

        # this one should not blow up
        self.assertEqual(allowed.val, 1)

        # but this one should
        allowed.invalidate_model(['val'])
        with self.assertRaises(AccessError):
            self.assertEqual(forbidden.val, -1)

    @mute_logger('odoo.addons.base.models.ir_rule')
    def test_group_rule(self):
        env = self.env(user=self.env.ref('base.public_user'))
        allowed = self.allowed.with_env(env)
        forbidden = self.forbidden.with_env(env)

        # we forbid access to the public group, to which the public user belongs
        self.env['ir.rule'].create({
            'name': 'Forbid public group',
            'model_id': self.env.ref('test_access_rights.model_test_access_right_some_obj').id,
            'groups': [Command.set([self.env.ref('base.group_public').id])],
            'domain_force': "[(0, '=', 1)]"
        })

        # everything should blow up
        (allowed + forbidden).invalidate_model(['val'])
        with self.assertRaises(AccessError):
            self.assertEqual(forbidden.val, -1)
        with self.assertRaises(AccessError):
            self.assertEqual(allowed.val, 1)

    def test_many2many(self):
        """ Test assignment of many2many field where rules apply. """
        ids = [self.allowed.id, self.forbidden.id]

        # create container as superuser, connected to all some_objs
        container_admin = self.env['test_access_right.container'].create({'some_ids': [Command.set(ids)]})
        self.assertItemsEqual(container_admin.some_ids.ids, ids)

        # check the container as the public user
        container_user = container_admin.with_user(self.env.ref('base.public_user'))
        container_user.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [self.allowed.id])

        # this should not fail
        container_user.write({'some_ids': [Command.set(ids)]})
        container_user.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [self.allowed.id])
        container_admin.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_admin.some_ids.ids, ids)

        # this removes all records
        container_user.write({'some_ids': [Command.clear()]})
        container_user.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [])
        container_admin.invalidate_model(['some_ids'])
        self.assertItemsEqual(container_admin.some_ids.ids, [])

    def test_access_rule_performance(self):
        env = self.env(user=self.env.ref('base.public_user'))
        Model = env['test_access_right.some_obj']
        # cache warmup for check() in 'ir.model.access'
        Model.check_access('read')
        with self.assertQueryCount(0):
            Model._filtered_access('read')

    def test_no_context_in_ir_rules(self):
        """ The context should not impact the ir rules. """
        ObjCateg = self.env['test_access_right.obj_categ']
        SomeObj = self.env['test_access_right.some_obj']

        # validate the effect of context on category search, there are
        # no existing media category
        self.assertTrue(ObjCateg.search([]))
        self.assertFalse(ObjCateg.with_context(only_media=True).search([]))

        # record1 is food and is accessible with an empy context
        self.env.registry.clear_cache()
        records = SomeObj.search([('id', '=', self.allowed.id)])
        self.assertTrue(records)

        # it should also be accessible as the context is not used when
        # searching for SomeObjs
        self.env.registry.clear_cache()
        records = SomeObj.with_context(only_media=True).search([('id', '=', self.allowed.id)])
        self.assertTrue(records)

    def test_check_access_rule_with_inherits(self):
        """
        For models in `_inherits`, verify that both methods `check_access`
        and `_apply_ir_rules` check the rules from parent models.
        """
        ChildModel = self.env['test_access_right.inherits']
        allowed_child, __ = children = ChildModel.create([
            {'some_id': self.allowed.id}, {'some_id': self.forbidden.id},
        ])

        user = self.env.ref('base.public_user')
        search_result = children.with_user(user).search([('id', 'in', children.ids)], order='id')
        filter_result = children.with_user(user)._filtered_access('read')

        self.assertEqual(search_result, allowed_child)
        self.assertEqual(filter_result, allowed_child)

    def test_flush_with_inherits(self):
        """
        For models with `_inherits`, verify that fields of the rules from inherited models
        are flushed correctly.
        """
        ChildModel = self.env['test_access_right.inherits']
        child = ChildModel.create([{'some_id': self.allowed.id}])
        self.env.flush_all()

        self.env['ir.rule'].create({
            'name': 'Forbid 0 value',
            'model_id': self.env['ir.model']._get('test_access_right.some_obj').id,
            'domain_force': str([('val', '!=', 0)]),
        })

        user = self.env.ref('base.public_user')

        # the parent record is accessible, so is the child record
        search_result = ChildModel.with_user(user).search([('id', '=', child.id)], order='id')
        self.assertEqual(search_result, child)

        # make the parent record inaccessible, and verify that the child record
        # becomes inaccessible, too
        self.allowed.val = 0
        search_result = ChildModel.with_user(user).search([('id', '=', child.id)], order='id')
        self.assertEqual(search_result, ChildModel)

    def test_domain_constrains(self):
        """ An error should be raised if domain is not correct """

        rule = self.env['ir.rule'].create({
            'name': 'Test record rule',
            'model_id': self.env.ref('test_access_rights.model_test_access_right_some_obj').id,
            'domain_force': [],
        })
        invalid_domains = [
            'A really bad domain!',
            [(1, '!=', 1)],
            [('non_existing_field', '=', 'value')],
        ]

        for domain in invalid_domains:
            with self.assertRaisesRegex(ValidationError, 'Invalid domain'):
                rule.domain_force = domain

        valid_domains = [
            False,
            [(1, '=', 1)],
            [('val', '=', 12)],
        ]
        for domain in valid_domains:
            # no error is raised
            rule.domain_force = domain
