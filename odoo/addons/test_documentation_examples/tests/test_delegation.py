# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common

class TestDelegation(common.TransactionCase):

    def setUp(self):
        super(TestDelegation, self).setUp()
        env = self.env
        record = env['delegation.laptop'].create({
            'screen_id': env['delegation.screen'].create({'size': 13.0}).id,
            'keyboard_id': env['delegation.keyboard'].create({'layout': 'QWERTY'}).id,
        })
        self.record = record

    def test_delegating_record(self):
        env = self.env
        record = self.record

        # children fields can be looked up on the parent record directly
        self.assertEqual(
            record.size
            ,
            13.0
        )
        self.assertEqual(
            record.layout
            ,
            'QWERTY'
        )

    def test_swap_child(self):
        env = self.env
        record = self.record

        record.write({
            'screen_id': env['delegation.screen'].create({'size': 17.0}).id
        })
        self.assertEqual(record.size, 17.0)

    def test_write(self):
        record = self.record

        record.write({'size': 14.0})
        self.assertEqual(record.size, 14.0)
        self.assertEqual(record.screen_id.size, 14.0)
