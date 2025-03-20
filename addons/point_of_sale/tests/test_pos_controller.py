# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSController(TestPointOfSaleDataHttpCommon):
    def test_qr_code_receipt(self):
        """This test make sure that no user is created when a partner is set on the PoS order.
            It also makes sure that the invoice is correctly created.
        """
        self.authenticate(None, None)
        self.pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.pos_config.current_session_id.id,
            'partner_id': self.partner_one.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product_awesome_item.product_variant_ids[0].id,
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
        self.pos_config.current_session_id.close_session_from_ui()
        get_invoice_data = {
            'access_token': self.pos_order.access_token,
            'name': self.partner_one.name,
            'email': "test@test.com",
            'company_name': self.partner_one.company_name,
            'vat': self.partner_one.vat,
            'street': "Test street",
            'city': "Test City",
            'zipcode': self.partner_one.zip,
            'country_id': self.partner_one.country_id.id,
            'state_id': self.partner_one.state_id.id,
            'phone': "123456789",
            'csrf_token': odoo.http.Request.csrf_token(self)
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=get_invoice_data)
        self.assertEqual(self.env['res.partner'].sudo().search_count([('name', '=', 'Partner One')]), 1)
        self.assertTrue(self.pos_order.is_invoiced, "The pos order should have an invoice")

    def test_qr_code_receipt_user_connected(self):
        """This test make sure that when the user is already connected he correctly gets redirected to the invoice."""
        self.partner_one_user = mail_new_test_user(
            self.env,
            name=self.partner_one.name,
            login='partner_one',
            email=self.partner_one.email,
            groups='base.group_portal',
        )
        self.authenticate('partner_one', 'partner_one')
        self.pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product_awesome_item.product_variant_ids[0].id,
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
        self.pos_config.current_session_id.close_session_from_ui()
        res = self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', timeout=30000)
        self.assertTrue(self.pos_order.is_invoiced, "The pos order should have an invoice")
        self.assertTrue("my/invoices" in res.url)
