import unittest2

import openerp.tests.common as common

class test_ir_attachment(common.TransactionCase):

    def test_00_attachment_flow(self):

        registry, cr, uid = self.registry, self.cr, self.uid

        ira = registry('ir.attachment')
        d = ira.create(cr, uid, {'name': 'a1', 'datas':'blob1'})

        #name_asc = partners.search(cr, uid, [('name', 'like', 'test_search_order%')], order="name asc")
        #self.assertEqual([a, ab, b, c], name_asc, "Search with 'NAME ASC' order failed.")

