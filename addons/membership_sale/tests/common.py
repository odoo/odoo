# -*- coding: utf-8 -*-
from openerp.tests import common

class TestMembershipSale(common.TransactionCase):

    def setUp(self):
        super(TestMembershipSale, self).setUp()

        # Usefull models
        self.sale_order = self.env['sale.order']
        self.membership_line = self.env['membership.membership_line']
        self.invoice_line = self.env['account.invoice']
        self.partner = self.env['res.partner']
        self.IrModelDataObj = self.env['ir.model.data']

        # create partner for sale order.
        self.partner_id = self.partner.create({
            'name': 'Test Customer',
            'email': 'testcustomer@test.com',
        })
        self.product_id = self.IrModelDataObj.xmlid_to_res_id(
            'membership.membership_0') or False
