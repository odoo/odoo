# -*- coding: utf-8 -*-
from openerp.tests import common


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

    def test_write_3_levels_inherits(self):
        """ Check that we can create an inherits on 3 levels """
        pallet = self.env.ref('test_inherits.pallet_a')
        pallet.write({'name': 'C'})
        self.assertEqual(pallet.name, 'C')
