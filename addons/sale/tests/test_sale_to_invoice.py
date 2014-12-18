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


class TestSale(TestMail):
    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.osv.orm')
    
    def setUp(self):
        super(TestSale, self).setUp()
        
    def test_sale_to_invoice(self):
        """ Testing for invoice create,validate and pay with invoicing and payment user."""
        cr, uid = self.cr, self.uid   
        
        # Usefull models
        data_obj = self.registry('ir.model.data')
        user_obj = self.registry('res.users')
        partner_obj = self.registry('res.partner')
        sale_obj = self.registry('sale.order')
        sale_order_line = self.registry('sale.order.line')
        sale_advance_payment_inv = self.registry('sale.advance.payment.inv')
        invoice_obj = self.registry('account.invoice')
        voucher_obj = self.registry('account.voucher')
        
        # Usefull record id
        group_id = data_obj.get_object_reference(cr, uid, 'account', 'group_account_invoice')[1]
        product_ref = data_obj.get_object_reference(cr, uid, 'product', 'product_category_5')
        product_id = product_ref and product_ref[1] or False
        account_id = data_obj.get_object_reference(cr, uid, 'account', 'cash')[1]
        company_id = data_obj.get_object_reference(cr, uid, 'base', 'main_company')[1]
        journal_id = data_obj.get_object_reference(cr, uid, 'account', 'bank_journal')[1]
        period_id = data_obj.get_object_reference(cr, uid, 'account', 'period_8')[1]
        
        # In order to test, I create new user and applied Invoicing & Payments group.
        user_id = user_obj.create(cr, uid, {
            'name': 'Test User',
            'login': 'test@test.com',
            'company_id': 1,
            'groups_id': [(6, 0, [group_id])]
        })
        assert user_id, "User will not created."
        
        # I create partner for sale order.
        partner_id = partner_obj.create(cr, uid, {
            'name': 'Test Customer',
            'email': 'testcustomer@test.com',
        })
        
        # In order to test I create sale order and confirmed it.
        order_id = sale_obj.create(cr, uid, {
            'partner_id': partner_id,
            'date_order': datetime.today(),
        })
        order_line = sale_order_line.create(cr, uid, {
                'order_id': order_id, 
                'product_id': product_id,
        })
        assert order_id, "Sale order will not created."
        
        context = {"active_model": 'sale.order', "active_ids": [order_id], "active_id":order_id}
        sale_obj.action_button_confirm(cr, uid, [order_id], context=context)
        
        # Now I create invoice.
        pay_id = sale_advance_payment_inv.create(cr, uid, {'advance_payment_method': 'fixed', 'amount': 5})
        inv = sale_advance_payment_inv.create_invoices(cr, uid, [pay_id], context=context)
        invoice_ids = sale_obj.browse(cr, uid, order_id).invoice_ids
        assert invoice_ids,"No any invoice is created for this sale order"
        
        # Now I validate pay invoice wihth Test User(invoicing and payment).
        for invoice in invoice_ids:
            invoice_obj.invoice_validate(cr, uid, [invoice.id], context=context)
        
        # Now I create and post an account voucher of amount 75.0 for the partner Test Customer.
        voucher_id = voucher_obj.create(cr, uid, {
            'account_id': account_id,
            'amount': 75.0,
            'company_id': company_id,
            'journal_id': journal_id,
            'partner_id': partner_id,
            'period_id': period_id,
            'type': 'receipt',
        })
        assert voucher_id,"Voucher will not created."
        voucher = voucher_obj.browse(cr, uid, voucher_id)
        voucher.signal_workflow('proforma_voucher')