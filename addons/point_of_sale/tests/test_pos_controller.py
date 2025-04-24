# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSController(TestPointOfSaleHttpCommon):
    def test_qr_code_receipt(self):
        """This test make sure that no user is created when a partner is set on the PoS order.
            It also makes sure that the invoice is correctly created.
        """
        self.authenticate(None, None)
        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.partner_full.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.test_product3.id,
                'price_unit': 10,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_tax': 10,
            'amount_total': 10,
            'amount_paid': 10.0,
            'amount_return': 10.0,
        })
        self.main_pos_config.current_session_id.close_session_from_ui()
        get_invoice_data = {
            'access_token': self.pos_order.access_token,
            'name': self.partner_full.name,
            'email': "test@test.com",
            'company_name': self.partner_full.company_name,
            'vat': self.partner_full.vat,
            'street': "Test street",
            'city': "Test City",
            'zipcode': self.partner_full.zip,
            'country_id': self.partner_full.country_id.id,
            'state_id': self.partner_full.state_id.id,
            'phone': "123456789",
            'csrf_token': odoo.http.Request.csrf_token(self)
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=get_invoice_data)
        self.assertEqual(self.env['res.partner'].sudo().search_count([('name', '=', 'Partner Full')]), 1)
        self.assertTrue(self.pos_order.is_invoiced, "The pos order should have an invoice")

    def test_qr_code_receipt_user_connected(self):
        """This test make sure that when the user is already connected he correctly gets redirected to the invoice."""
        self.partner_full_user = mail_new_test_user(
            self.env,
            name=self.partner_full.name,
            login='partner_full',
            email=self.partner_full.email,
            groups='base.group_portal',
        )
        self.authenticate('partner_full', 'partner_full')

        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.test_product3.id,
                'price_unit': 10,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_tax': 10,
            'amount_total': 10,
            'amount_paid': 10.0,
            'amount_return': 10.0,
        })
        self.main_pos_config.current_session_id.close_session_from_ui()
        res = self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', timeout=30000)
        self.assertTrue(self.pos_order.is_invoiced, "The pos order should have an invoice")
        self.assertTrue("my/invoices" in res.url)
