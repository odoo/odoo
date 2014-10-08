import unittest2

import openerp.tests.common as common

class test_ir_model(common.TransactionCase):

    def test_00(self):
        # Create some custom model and fields
        cr, uid, context = self.cr, self.uid, {}

        ir_model = self.registry('ir.model')
        ir_model_fields = self.registry('ir.model.fields')
        ir_model_access = self.registry('ir.model.access')
        candy_model_id = ir_model.create(cr, uid, {
                'name': 'Candies',
                'model': 'x_candy',
                'info': 'List of candies',
                'state': 'manual',
            }, context=context)
        # security rule to avoid warning
        ir_model_access.create(cr, uid, {
                'name': 'Candies are for everybody',
                'model_id': candy_model_id,
                'perm_read': True,
                'perm_write': True,
                'perm_create': True,
                'perm_unlink': True,
            })

        assert self.registry('x_candy'), "Custom model not present in registry"

        ir_model_fields.create(cr, uid, {
                'name': 'x_name',
                'field_description': 'Name',
                'model_id': candy_model_id,
                'state': 'manual',
                'ttype': 'char',
            }, context=context)
        
        assert 'x_name' in self.registry('x_candy')._all_columns, "Custom field not present in registry"
        assert self.registry('x_candy')._rec_name == 'x_name', "The _rec_name on custom model was not updated"

if __name__ == '__main__':
    unittest2.main()
