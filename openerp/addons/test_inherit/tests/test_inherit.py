# -*- coding: utf-8 -*-
from openerp.tests import common

class test_inherits(common.TransactionCase):

    def test_access_from_child_to_parent_model(self):
        # This test checks if the new added column of a parent model
        # is accessible from the child model. This test has been written
        # to verify the purpose of the inheritance computing of the class
        # in the openerp.osv.orm._build_model.
        mother = self.registry('test.inherit.mother')
        daugther = self.registry('test.inherit.daugther')

        self.assertIn('field_in_mother', mother._fields)
        self.assertIn('field_in_mother', daugther._fields)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
