# -*- coding: utf-8 -*-
import unittest2

import openerp
from openerp.tests import common


class test_transaction_case(common.TransactionCase):

    def _test_00(self):
        cr, uid = self.cr, self.uid
        location_id = self.registry('stock.location').create(cr, uid,
            {'name': 'Test Location A'})
        product_id = self.registry('product.product').create(cr, uid,
            {
                'name': 'Test Product A',
                'standard_price': 1,
            })
        value = self.registry('stock.value')._get_value(cr, uid,
            location_id, product_id, openerp.osv.fields.datetime.now())
        self.assertEqual(value, 0)

    def _test_01(self):
        cr, uid = self.cr, self.uid
        stock_location_company = self.registry('ir.model.data').get_object(cr, uid, 'stock', 'stock_location_company')
        location_id = self.registry('stock.location').create(cr, uid,
            {'name': 'Test Location A'})
        product_id = self.registry('product.product').create(cr, uid,
            {
                'name': 'Test Product A',
                'standard_price': 1,
            })
        product = self.registry('product.product').browse(cr, uid, product_id)
        move_id = self.registry('stock.move').create(cr, uid,
            {
                'name': 'Test Stock Move 1',
                'product_id': product_id,
                'location_id': stock_location_company.id, # arbitrary source location
                'location_dest_id': location_id,
                'product_uom_qty': 10,
                'product_uom': product.uom_id.id,
            })
        value = self.registry('stock.value')._get_value(cr, uid,
            location_id, product_id, openerp.osv.fields.datetime.now())
        self.assertEqual(value, 0)

        self.registry('stock.move').action_done(cr, uid, [move_id])
        value = self.registry('stock.value')._get_value(cr, uid,
            location_id, product_id, openerp.osv.fields.datetime.now())
        self.assertEqual(value, 10)

if __name__ == '__main__':
    unittest2.main()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
