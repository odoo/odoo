# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
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
        self.new_partner = self.env['res.partner'].create({
            'name': 'AAA Partner',
            'zip': '12345',
            'state_id': self.env.ref('base.state_us_1').id,
            'country_id': self.env.ref('base.us').id,
        })
        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'is_storable': True,
            'list_price': 10.0,
            'taxes_id': False,
        })
        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'partner_id': self.new_partner.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
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
            'name': self.new_partner.name,
            'email': "test@test.com",
            'company_name': self.new_partner.company_name,
            'vat': self.new_partner.vat,
            'street': "Test street",
            'city': "Test City",
            'zipcode': self.new_partner.zip,
            'country_id': self.new_partner.country_id.id,
            'state_id': self.new_partner.state_id.id,
            'phone': "123456789",
            'csrf_token': odoo.http.Request.csrf_token(self)
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=get_invoice_data)
        self.assertEqual(self.env['res.partner'].sudo().search_count([('name', '=', 'AAA Partner')]), 1)
        self.assertTrue(self.pos_order.is_invoiced, "The pos order should have an invoice")
        self.assertTrue(len(self.pos_order.pos_reference) >= 12, "The pos reference should not be less than 12 characters")

    def test_qr_code_receipt_user_connected(self):
        """This test make sure that when the user is already connected he correctly gets redirected to the invoice."""
        self.partner_1 = self.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })
        self.partner_1_user = mail_new_test_user(
            self.env,
            name=self.partner_1.name,
            login='partner_1',
            email=self.partner_1.email,
            groups='base.group_portal',
        )
        self.authenticate('partner_1', 'partner_1')

        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'is_storable': True,
            'list_price': 10.0,
            'taxes_id': False,
        })
        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
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

    def test_qr_code_receipt_user_not_connected(self):
        """This test make sure that when the user is not connected (public user). Order should invoiced with public user data."""

        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'is_storable': True,
            'list_price': 10.0,
            'taxes_id': False,
        })
        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "Test Product 1",
                'product_id': self.product1.id,
                'price_unit': 10,
                'tax_ids': False,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_tax': 10,
            'amount_total': 10,
            'amount_paid': 10.0,
            'amount_return': 10.0,
            'pos_reference': '2500-002-00002',
            'ticket_code': 'inPoS',
            'date_order': datetime.today(),
        })
        context_make_payment = {"active_ids": [self.pos_order.id], "active_id": self.pos_order.id}
        self.pos_make_payment = self.env['pos.make.payment'].with_context(context_make_payment).create({
            'amount': 10.0,
            'payment_method_id': self.main_pos_config.payment_method_ids[0].id,
        })
        context_payment = {'active_id': self.pos_order.id}
        self.pos_make_payment.with_context(context_payment).check()
        self.main_pos_config.current_session_id.close_session_from_ui()
        self.start_tour('/pos/ticket', 'invoicePoSOrderWithSelfInvocing', login=None)
        self.assertTrue(self.pos_order.account_move, "The pos order should have an invoice after self invoicing")

    def test_qr_code_receipt_user_updated(self):
        """This test make sure that when the user is already connected he correctly gets redirected to the invoice."""
        self.authenticate(None, None)
        self.partner_1 = self.env['res.partner'].create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })

        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'is_storable': True,
            'list_price': 10.0,
            'taxes_id': False,
        })
        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'partner_id': self.partner_1.id,
            'access_token': '1234567890',
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
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
            'name': 'New Name',
            'email': "test@test.com",
            'vat': 'VAT_TEST_NUMBER_123',
            'street': "Test street",
            'city': "Test City",
            'zipcode': '12345',
            'country_id': self.company.country_id.id,
            'phone': "123456789",
            'state_id': self.env['res.country.state'].search([], limit=1).id,
            'csrf_token': odoo.http.Request.csrf_token(self)
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=get_invoice_data, timeout=30000)
        self.assertEqual(self.partner_1.vat, 'VAT_TEST_NUMBER_123')
        self.assertEqual(self.partner_1.name, 'New Name')
        self.assertEqual(self.partner_1.zip, '12345')
