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

    def test_read_3_levels_inherits(self):
        """ Check that we can read an inherited field on 3 levels """
        pallet = self.env.ref('test_inherits.pallet_a')
        self.assertEqual(pallet.read(['name']), [{'id': pallet.id, 'name': 'Unit A'}])

    def test_write_3_levels_inherits(self):
        """ Check that we can create an inherits on 3 levels """
        pallet = self.env.ref('test_inherits.pallet_a')
        pallet.write({'name': 'C'})
        self.assertEqual(pallet.name, 'C')

    def test_create_3_levels_inherits_default_fields(self):
        """ Check that creating an inherits on 3 levels doesn't override
        parent's values """
        unit = self.env.ref('test_inherits.unit_a')
        unit.state = 'b'
        self.env['test.pallet'].with_context(default_state='a').create({
            'name': 'Pallet B',
            'unit_id': unit.id,
        })
        self.assertEqual(unit.state, 'b')
