# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common

class TestDelegation(common.TransactionCase):

    def setUp(self):
        super(TestDelegation, self).setUp()
        env = self.env
        record = env['delegation.parent'].create({
            'child0_id': env['delegation.child0'].create({'field_0': 0}).id,
            'child1_id': env['delegation.child1'].create({'field_1': 1}).id,
        })
        self.record = record

    def test_delegating_record(self):
        env = self.env
        record = self.record

        # children fields can be looked up on the parent record directly
        self.assertEqual(record.field_0, 0)
        self.assertEqual(record.field_1, 1)

    def test_swap_child(self):
        env = self.env
        record = self.record

        record.write({
            'child0_id': env['delegation.child0'].create({'field_0': 42}).id
        })
        self.assertEqual(record.field_0, 42)

    def test_write(self):
        record = self.record

        record.write({'field_1': 4})
        self.assertEqual(record.field_1, 4)
        self.assertEqual(record.child1_id.field_1, 4)
