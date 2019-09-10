# -*- coding: utf-8 -*-
from openerp.tests import common


class test_no_infinite_recursion(common.TransactionCase):

    def setUp(self):
        super(test_no_infinite_recursion, self).setUp()
        self.tstfct = self.registry['test_old_api.function_noinfiniterecursion']

    def test_00_create_and_update(self):
        """
        Check that computing old api function field does not cycle infinitely
        See https://github.com/odoo/odoo/pull/7558
        """
        cr, uid, context, tstfct = self.cr, self.uid, {}, self.tstfct

        vals = {
            'f0': 'Test create',
        }
        idnew = tstfct.create(cr, uid, vals, context=context)
        tst = tstfct.browse(cr, uid, idnew, context=context)

        self.assertEqual(tst.f1, 'create')

        vals = {
            'f0': 'Test write',
        }
        tstfct.write(cr, uid, idnew, vals, context=context)

        self.assertEqual(tst.f1, 'write')
