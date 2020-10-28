# -*- coding: utf-8 -*-
from odoo.tests import common


class test_inherits(common.TransactionCase):

    def test_create_3_levels_inherits(self):
        """ Check that we can create an inherits on 3 levels """
        pallet = self.env['test.pallet'].create({
            'name': 'B',
            'field_in_box': 'box',
            'field_in_pallet': 'pallet',
        })
        self.assertTrue(pallet)
        self.assertEqual(pallet.name, 'B')
        self.assertEqual(pallet.field_in_box, 'box')
        self.assertEqual(pallet.field_in_pallet, 'pallet')

    def test_create_3_levels_inherits_with_defaults(self):
        unit = self.env['test.unit'].create({
            'name': 'U',
            'state': 'a',
            'size': 1,
        })
        ctx = {
            'default_state': 'b',       # 'state' is inherited from 'test.unit'
            'default_size': 2,          # 'size' is inherited from 'test.box'
        }
        pallet = self.env['test.pallet'].with_context(ctx).create({
            'name': 'P',
            'unit_id': unit.id,         # grand-parent field is set
        })
        # default 'state' should be ignored, but default 'size' should not
        self.assertEqual(pallet.state, 'a')
        self.assertEqual(pallet.size, 2)

    def test_read_3_levels_inherits(self):
        """ Check that we can read an inherited field on 3 levels """
        pallet = self.env.ref('test_inherits.pallet_a')
        self.assertEqual(pallet.read(['name']), [{'id': pallet.id, 'name': 'Unit A'}])

    def test_write_3_levels_inherits(self):
        """ Check that we can create an inherits on 3 levels """
        pallet = self.env.ref('test_inherits.pallet_a')
        pallet.write({'name': 'C'})
        self.assertEqual(pallet.name, 'C')
