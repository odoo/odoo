# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import unittest
import pooler
import netsvc
from cStringIO import StringIO
from osv import osv

cr = None
uid = None
order_id = None

class sale_order_test_case(unittest.TestCase):
    def setUp(self):
        try:
            self.pool = pooler.get_pool(cr.dbname)
            self.sale_order = self.pool.get('sale.order')
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)


    def tearDown(self):
        try:
            self.pool = None
            self.sale_order = None
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)


    def test_1_Create(self):

        try:
            global order_id
            model_obj = self.pool.get('ir.model.data')

            ### SALE ORDER
            shop = model_obj._get_id(cr, uid, 'sale', 'shop')
            shop_id = model_obj.browse(cr, uid, shop).res_id
            partner = model_obj._get_id(cr,uid, 'base', 'res_partner_9')
            partner_id = model_obj.browse(cr, uid, partner,).res_id
            partner_invoice = model_obj._get_id(cr, uid, 'base', 'res_partner_address_9')
            partner_invoice_id = model_obj.browse(cr, uid, partner_invoice).res_id
            pricelist_id = self.pool.get('res.partner').browse(cr, uid,partner_id).property_product_pricelist.id
            order_id = self.sale_order.create(cr,uid,
                            {'shop_id':shop_id,'pricelist_id':pricelist_id,'user_id':uid,
                             'partner_id':partner_id,'partner_invoice_id':partner_invoice_id,
                             'partner_shipping_id':partner_invoice_id,'partner_order_id':partner_invoice_id})
            ### SALE ORDER LINE
            product = model_obj._get_id(cr,uid, 'product', 'product_product_pc2')
            product_id = model_obj.browse(cr, uid, product).res_id
            product_uom = model_obj._get_id(cr, uid, 'product', 'product_uom_unit')
            product_uom_id = model_obj.browse(cr, uid, product_uom).res_id
            self.pool.get('sale.order.line').create(cr,uid,
                            {'order_id':order_id,'name':'[PC2] Computer assembled on demand',
                             'product_id':product_id,'product_uom':product_uom_id,'price_unit':600,
                             'type':'make_to_order'})
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)

    def test_2_ConfirmOrder(self):
        try:
            self.failUnless(order_id,"No Sale Order Created !")
            wf_service = netsvc.LocalService("workflow")
            res = wf_service.trg_validate(uid, 'sale.order',order_id, 'order_confirm', cr)
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)

    def test_3_CreateInvoice(self):

        try:
            self.failUnless(order_id,"No Sale Order Created !")
            wf_service = netsvc.LocalService("workflow")
            res = wf_service.trg_validate(uid, 'sale.order',order_id, 'manual_invoice', cr)
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)

    def test_4_CancelPicking(self):
        try:
            self.failUnless(order_id,"No Sale Order Created !")
            picking_obj = self.pool.get('stock.picking')
            pickings = picking_obj.search(cr,uid,[('sale_id','=',order_id)])
            picking_obj.action_cancel(cr, uid, pickings)
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)

    def test_5_PrintOrder(self):
        try:
            self.failUnless(order_id,"No Sale Order Created !")
            report_service = netsvc.LocalService("report")
            model_obj = self.pool.get('ir.model.data')
            passwd = self.pool.get('res.users').browse(cr,uid,uid).password
            report = model_obj._get_id(cr, uid, 'sale', 'report_sale_order')
            report_id = model_obj.browse(cr, uid, report).res_id
            report_service.report(cr.dbname, uid, passwd, 'sale.order', [order_id])
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)

    def test_6_CancelOrder(self):
        try:
            self.failUnless(order_id,"No Sale Order Created !")
            self.sale_order.action_cancel(cr, uid, [order_id])
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)

    def test_7_Unlink(self):
        try:
            self.failUnless(order_id,"No Sale Order Created !")
            self.sale_order.unlink(cr, uid, [order_id])
        except osv.except_osv,e:
            self.fail(e.name + e.value)
        except Exception,e:
            self.fail(e)


def runTest(cursor=None, user=None):
    global cr
    global uid
    cr = cursor
    uid = user
    out = StringIO()
    suite = unittest.TestLoader().loadTestsFromTestCase(sale_order_test_case)
    res = unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
    if res.wasSuccessful():
        return (True,out.getvalue())
    return (res,out.getvalue())
