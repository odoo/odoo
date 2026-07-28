# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class test_inherits(common.TransactionCase):

    def test_ir_model_data_inherits_again(self):
        """ Re-run test_inherits test to make sure another imd hasn't been created """
        IrModelData = self.env['ir.model.data']
        field = IrModelData.search([('name', '=', 'field_test_unit__name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_inherits')

        field = IrModelData.search([('name', '=', 'field_test_box__name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_inherits')


    def test_ir_model_data_inherits_depends(self):
        """ Check the existence of the correct ir.model.data """
        IrModelData = self.env['ir.model.data']
        field = IrModelData.search([('name', '=', 'field_test_unit__second_name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_inherits_depends')

        field = IrModelData.search([('name', '=', 'field_test_box__second_name')])
        self.assertEqual(len(field), 1)
        self.assertEqual(field.module, 'test_inherits_depends')
