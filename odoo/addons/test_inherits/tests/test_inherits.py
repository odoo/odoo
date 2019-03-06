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

    def test_ir_model_data_inherits(self):
        """ Check the existence of the correct ir.model.data """
        IrModelData = self.env['ir.model.data']
        field = IrModelData.search([('name', '=', 'field_test_unit__name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_inherits')

        field = IrModelData.search([('name', '=', 'field_test_box__name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_inherits')
