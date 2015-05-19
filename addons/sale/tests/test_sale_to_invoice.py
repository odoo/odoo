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
        import time
        # Usefull models
        IrModelData = self.env['ir.model.data']
        partner_obj = self.env['res.partner']
        journal_obj = self.env['account.journal']
        account_obj = self.env['account.account']
        # Usefull record id
        group_id = IrModelData.xmlid_to_res_id('account.group_account_invoice') or False
        product_id = IrModelData.xmlid_to_res_id('product.product_category_3') or False
        company_id = IrModelData.xmlid_to_res_id('base.main_company') or False
        journal_id = self.env['res.company'].browse(company_id)._create_bank_account_and_journal('BNK')
        account_id = journal_obj.browse(journal_id).default_credit_account_id.id
        date = time.strftime("%Y/%m/%d")

        # Usefull accounts
        user_type_id = IrModelData.xmlid_to_res_id('account.data_account_type_revenue')
        account_rev_id = account_obj.create({'code': 'X2020', 'name': 'Sales - Test Sales Account', 'user_type': user_type_id, 'reconcile': True})
        user_type_id = IrModelData.xmlid_to_res_id('account.data_account_type_receivable')
        account_recv_id = account_obj.create({'code': 'X1012', 'name': 'Sales - Test Reicv Account', 'user_type': user_type_id, 'reconcile': True})

        # Add account to product
        product_template_id = self.env.ref('sale.advance_product_0').product_tmpl_id
        product_template_id.write({'property_account_income': account_rev_id})

        # Create Sale Journal
        journal_obj.create({'name': 'Sale Journal - Test', 'code': 'STSJ', 'type': 'sale', 'company_id': company_id})

        # In order to test, I create new user and applied Invoicing & Payments group.
        user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test@test.com',
            'company_id': 1,
            'groups_id': [(6, 0, [group_id])]})
        assert user, "User will not created."
        # I create partner for sale order.
        partner = partner_obj.create({
            'name': 'Test Customer',
            'email': 'testcustomer@test.com',
            'property_account_receivable': account_recv_id,
        })
        
        # In order to test I create sale order and confirmed it.
        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'date_order': datetime.today()})
        order_line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product_id})
        assert order, "Sale order will not created."
        context = {"active_model": 'sale.order', "active_ids": [order.id], "active_id": order.id}
        order.with_context(context).action_button_confirm()
        # Now I create invoice.
        payment = self.env['sale.advance.payment.inv'].create({'advance_payment_method': 'fixed', 'amount': 5})
        invoice = payment.with_context(context).create_invoices()
        assert order.invoice_ids, "No any invoice is created for this sale order"
        # Now I validate pay invoice wihth Test User(invoicing and payment).
        for invoice in order.invoice_ids:
            invoice.with_context(context).invoice_validate()
