# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.mail.tests.common import TestMail
from openerp.tools import mute_logger
from datetime import datetime


class TestPurchase(TestMail):
    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    
    def setUp(self):
        super(TestPurchase, self).setUp()
        
    def test_purchase_to_invoice(self):
        """ Testing for invoice create,validate and pay with invoicing and payment user."""
        cr, uid = self.cr, self.uid   
        
        # Usefull models
        data_obj = self.registry('ir.model.data')
        user_obj = self.registry('res.users')
        partner_obj = self.registry('res.partner')
        purchase_obj = self.registry('purchase.order')
        purchase_order_line = self.registry('purchase.order.line')
        invoice_obj = self.registry('account.invoice')
        
        # Usefull record id
        group_id = data_obj.get_object_reference(cr, uid, 'account', 'group_account_invoice')[1]
        product_ref = data_obj.get_object_reference(cr, uid, 'product', 'product_category_5')
        product_id = product_ref and product_ref[1] or False
        company_id = data_obj.get_object_reference(cr, uid, 'base', 'main_company')[1]
        location_id = data_obj.get_object_reference(cr, uid, 'stock', 'stock_location_3')[1]
        
        # In order to test, I create new user and applied Invoicing & Payments group.
        user_id = user_obj.create(cr, uid, {
            'name': 'Test User',
            'login': 'test@test.com',
            'company_id': 1,
            'groups_id': [(6, 0, [group_id])]
        })
        assert user_id, "User will not created."
        
        # I create partner for purchase order.
        partner_id = partner_obj.create(cr, uid, {
            'name': 'Test Customer',
            'email': 'testcustomer@test.com',
        })
        
        # In order to test I create purchase order and confirmed it.
        order_id = purchase_obj.create(cr, uid, {
            'partner_id': partner_id,
            'location_id': location_id,
            'pricelist_id': 1,
        })
        order_line = purchase_order_line.create(cr, uid, {
                'order_id': order_id, 
                'product_id': product_id,
                'product_qty': 100.0,
                'product_uom': 1,
                'price_unit': 89.0,
                'name': 'Service',
                'date_planned': '2014-05-31',
        })
        assert order_id, "purchase order will not created."
        
        context = {"active_model": 'purchase.order', "active_ids": [order_id], "active_id":order_id}
        purchase_obj.wkf_confirm_order(cr, uid, [order_id], context=context)
        
        # In order to test I create invoice.
        invoice_id = purchase_obj.action_invoice_create(cr, uid, [order_id], context=context)
        assert invoice_id,"No any invoice is created for this purchase order"
        
        # In order to test I validate invoice wihth Test User(invoicing and payment).
        res = invoice_obj.invoice_validate(cr, uid, [invoice_id], context=context)
        self.assertTrue(res, 'Invoice will not validated')
