# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

class TestRules(TransactionCase):
    def setUp(self):
        super(TestRules, self).setUp()

        self.id1 = self.env['test_access_right.some_obj']\
            .create({'val': 1}).id
        self.id2 = self.env['test_access_right.some_obj']\
            .create({'val': -1}).id
        # create a global rule forbidding access to records with a negative
        # (or zero) val
        self.env['ir.rule'].create({
            'name': 'Forbid negatives',
            'model_id': self.browse_ref('test_access_rights.model_test_access_right_some_obj').id,
            'domain_force': "[('val', '>', 0)]"
        })

    def test_basic_access(self):
        env = self.env(user=self.browse_ref('base.public_user'))

        # put forbidden record in cache
        browse2 = env['test_access_right.some_obj'].browse(self.id2)
        # this is the one we want
        browse1 = env['test_access_right.some_obj'].browse(self.id1)

        # this should not blow up
        self.assertEqual(browse1.val, 1)

        # but this should
        browse1.invalidate_cache(['val'])
        with self.assertRaises(AccessError):
            self.assertEqual(browse2.val, -1)

    def test_group_rule(self):
        env = self.env(user=self.browse_ref('base.public_user'))

        # we forbid access to the public group, to which the public user belongs
        self.env['ir.rule'].create({
            'name': 'Forbid public group',
            'model_id': self.browse_ref('test_access_rights.model_test_access_right_some_obj').id,
            'groups': [(6, 0, [self.browse_ref('base.group_public').id])],
            'domain_force': "[(0, '=', 1)]"
        })

        browse2 = env['test_access_right.some_obj'].browse(self.id2)
        browse1 = env['test_access_right.some_obj'].browse(self.id1)

        # everything should blow up
        (browse1 + browse2).invalidate_cache(['val'])
        with self.assertRaises(AccessError):
            self.assertEqual(browse2.val, -1)
        with self.assertRaises(AccessError):
            self.assertEqual(browse1.val, 1)

    def test_many2many(self):
        """ Test assignment of many2many field where rules apply. """
        ids = [self.id1, self.id2]

        # create container as superuser, connected to all some_objs
        container_admin = self.env['test_access_right.container'].create({'some_ids': [(6, 0, ids)]})
        self.assertItemsEqual(container_admin.some_ids.ids, ids)

        # check the container as the public user
        container_user = container_admin.with_user(self.browse_ref('base.public_user'))
        container_user.invalidate_cache(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [self.id1])

        # this should not fail
        container_user.write({'some_ids': [(6, 0, ids)]})
        container_user.invalidate_cache(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [self.id1])
        container_admin.invalidate_cache(['some_ids'])
        self.assertItemsEqual(container_admin.some_ids.ids, ids)

        # this removes all records
        container_user.write({'some_ids': [(5,)]})
        container_user.invalidate_cache(['some_ids'])
        self.assertItemsEqual(container_user.some_ids.ids, [])
        container_admin.invalidate_cache(['some_ids'])
        self.assertItemsEqual(container_admin.some_ids.ids, [])

    def test_access_rule_performance(self):
        env = self.env(user=self.browse_ref('base.public_user'))
        Model = env['test_access_right.some_obj']
        with self.assertQueryCount(0):
            Model._filter_access_rules('read')
