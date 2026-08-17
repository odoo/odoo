# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import odoo
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSController(TestPointOfSaleHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

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
            'vat': self.new_partner.vat,
            'street': "Test street",
            'city': "Test City",
            'zipcode': self.new_partner.zip,
            'country_id': self.new_partner.country_id.id,
            'state_id': self.new_partner.state_id.id,
            'phone': "123456789",
            'csrf_token': self.csrf_token()
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=get_invoice_data)
        self.assertEqual(self.env['res.partner'].sudo().search_count([('name', '=', 'AAA Partner')]), 1)
        self.assertTrue(self.pos_order.is_singly_invoiced, "The pos order should have an invoice")
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
        self.assertTrue(self.pos_order.is_singly_invoiced, "The pos order should have an invoice")
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
        self.assertNotEqual(self.pos_order.account_move, self.pos_order.session_id.move_ids)

    def test_qr_code_receipt_with_customer_no_user_connected(self):
        """This test make sure that when the user is not connected (public user) but
            the pos order has a partner, the invoice is correctly created.
            """
        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'is_storable': True,
            'list_price': 10.0,
            'taxes_id': False,
        })
        self.new_partner = self.env['res.partner'].create({
            'name': 'Rangilo Gujarati',
            'zip': '654321',
            'vat': '24AAGCC7144L6ZE',
            'email': 'rangilo@gujarati.com',
            'street': 'swapnpuri',
            'phone': '1234567890',
            'city': 'Ahmedabad',
            'state_id': self.env.ref('base.state_in_gj').id,
            'country_id': self.env.ref('base.in').id,
        })
        self.main_pos_config.open_ui()
        self.pos_order = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'partner_id': self.new_partner.id,
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
            'pos_reference': '2500-002-00003',
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
        self.start_tour('/pos/ticket', 'invoicePoSOrderWithPartner', login=None)
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
            'csrf_token': self.csrf_token()
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=get_invoice_data, timeout=30000)
        self.assertEqual(self.partner_1.vat, 'VAT_TEST_NUMBER_123')
        self.assertEqual(self.partner_1.name, 'New Name')
        self.assertEqual(self.partner_1.zip, '12345')

    def _create_portal_pos_order(self, partner, pos_reference, invoiced=False, amount=10.0, **values):
        """Create a paid order the same way the Point of Sale UI does."""
        config = self.main_pos_config
        if not config.current_session_id:
            config.open_ui()

        cash_payment_method = config.payment_method_ids.filtered(lambda pm: pm.type == 'cash')[:1]
        product = self.desk_pad.product_variant_id

        order_data = self.env['pos.order'].sync_from_ui([{
            'name': pos_reference,
            'pos_reference': pos_reference,
            'session_id': config.current_session_id.id,
            'partner_id': partner.id,
            'user_id': self.env.uid,
            'to_invoice': invoiced,
            'amount_total': amount,
            'amount_paid': amount,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'lines': [(0, 0, {
                'product_id': product.id,
                'qty': 1,
                'price_unit': amount,
                'price_subtotal': amount,
                'price_subtotal_incl': amount,
                'tax_ids': [(6, 0, [])],
            })],
            'payment_ids': [(0, 0, {
                'amount': amount,
                'name': odoo.fields.Datetime.now(),
                'payment_method_id': cash_payment_method.id,
            })],
            **values,
        }])
        return self.env['pos.order'].browse(order_data['pos.order'][0]['id'])

    def test_portal_my_store_orders(self):
        """The portal lists the current partner's paid orders only."""
        portal_user = self._create_new_portal_user()
        other_partner = self.env['res.partner'].create({'name': 'Other Customer'})

        own_order = self._create_portal_pos_order(portal_user.partner_id, '1000-001-00001')
        own_draft_order = self._create_portal_pos_order(portal_user.partner_id, '1000-001-00002', state='draft')
        other_order = self._create_portal_pos_order(other_partner, '1000-001-00003')

        self.authenticate(portal_user.login, portal_user.login)
        response = self.url_open('/my/store-orders')

        self.assertEqual(response.status_code, 200)
        self.assertIn(own_order.pos_reference, response.text)
        self.assertNotIn(own_draft_order.pos_reference, response.text, "an unpaid order is not settled yet")
        self.assertNotIn(other_order.pos_reference, response.text, "orders of another partner stay private")

    def test_portal_store_orders_list_tour(self):
        """Sorting, filtering and the receipt links of the portal order list."""
        portal_user = self._create_new_portal_user()

        self._create_portal_pos_order(portal_user.partner_id, '1000-002-00001', amount=20.0, date_order='2026-01-01 10:00:00')
        self._create_portal_pos_order(portal_user.partner_id, '1000-002-00002', date_order='2026-02-01 10:00:00')
        self._create_portal_pos_order(
            portal_user.partner_id,
            '1000-002-00003',
            amount=15.0,
            date_order='2025-12-01 10:00:00',
            invoiced=True
        )
        self.main_pos_config.current_session_id.close_session_from_ui()

        self.start_tour('/my/home', 'test_portal_store_orders_list_tour', login=portal_user.login)
