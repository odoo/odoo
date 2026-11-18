# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import odoo
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSController(TestPointOfSaleHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    def _pay_order(self, order):
        payment = self.env['pos.make.payment'].with_context(
            active_ids=[order.id], active_id=order.id,
        ).create({
            'amount': order.amount_total,
            'payment_method_id': self.main_pos_config.payment_method_ids[0].id,
        })
        payment.with_context(active_id=order.id).check()
        self.assertEqual(order.state, 'paid')

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
        self._pay_order(self.pos_order)
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

    def test_qr_code_receipt_anonymous_cannot_modify_partner_with_user(self):
        """An anonymous user must not be able to modify a partner that is linked to a user, but still gets the invoice."""
        self.authenticate(None, None)
        self.new_partner_user = mail_new_test_user(
            self.env,
            name='My Partner',
            login='my_partner',
            email='original@test.com',
            groups='base.group_portal',
        )
        self.new_partner = self.new_partner_user.partner_id
        self.new_partner.write({
            'street': 'Original street',
            'city': 'Original City',
            'zip': '12345',
            'phone': '000000000',
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
        self._pay_order(self.pos_order)
        self.main_pos_config.current_session_id.close_session_from_ui()
        form_data = {
            'access_token': self.pos_order.access_token,
            'name': 'new name',
            'email': 'newemail@test.com',
            'street': 'new street',
            'city': 'new City',
            'zipcode': '99999',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_1').id,
            'phone': '999999999',
            'csrf_token': self.csrf_token(),
        }
        res = self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data=form_data)
        self.assertEqual(self.new_partner.name, 'My Partner')
        self.assertEqual(self.new_partner.email, 'original@test.com')
        self.assertEqual(self.new_partner.street, 'Original street')
        self.assertEqual(self.new_partner.city, 'Original City')
        self.assertEqual(self.new_partner.zip, '12345')
        self.assertEqual(self.new_partner.phone, '000000000')
        self.assertTrue(self.pos_order.account_move, "The pos order should have an invoice")
        self.assertTrue("my/invoices" in res.url)

    def test_qr_code_receipt_create_customer(self):
        """Submitting invoice details creates a customer for an anonymous order."""
        self.authenticate(None, None)
        self.product1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'is_storable': True,
            'list_price': 10.0,
            'taxes_id': False,
        })
        self.main_pos_config.open_ui()

        self.pos_order_2 = self.env['pos.order'].create({
            'session_id': self.main_pos_config.current_session_id.id,
            'company_id': self.env.company.id,
            'access_token': '1234567891',
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
        self._pay_order(self.pos_order_2)
        self.main_pos_config.current_session_id.close_session_from_ui()
        get_invoice_data = {
            'access_token': self.pos_order_2.access_token,
            'name': 'New Customer',
            'email': 'test@test.com',
            'vat': 'VAT_TEST_NUMBER_124',
            'street': 'Test street',
            'city': 'Test City',
            'zipcode': '12345',
            'country_id': self.company.country_id.id,
            'phone': '123456789',
            'state_id': self.env['res.country.state'].search([], limit=1).id,
            'csrf_token': self.csrf_token()
        }
        self.url_open(f'/pos/ticket/validate?access_token={self.pos_order_2.access_token}', data=get_invoice_data, timeout=30000)
        partner_2 = self.pos_order_2.partner_id
        self.assertEqual(partner_2.name, 'New Customer')
        self.assertEqual(partner_2.email, 'test@test.com')
        self.assertEqual(partner_2.phone, '123456789')
        self.assertEqual(partner_2.vat, 'VAT_TEST_NUMBER_124')
        self.assertEqual(partner_2.zip, '12345')

    def test_self_invoicing_refused_on_unpaid_order(self):
        """An order that has not been paid yet must not be invoiceable from the customer portal"""
        self.authenticate(None, None)
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
            'access_token': 'unpaid_token_1234',
            'lines': [(0, 0, {
                'name': "Test Product 1",
                'product_id': self.product1.id,
                'price_unit': 10,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_tax': 0,
            'amount_total': 10,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'pos_reference': '2500-002-00004',
            'ticket_code': 'unpad',
            'date_order': datetime.today(),
        })
        self.assertEqual(self.pos_order.state, 'draft', "The order should not be paid yet")

        res = self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}')
        self.assertEqual(res.status_code, 404, "The validation screen should not be reachable")

        res = self.url_open(f'/pos/ticket?order_uuid={self.pos_order.uuid}', allow_redirects=False)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn('Location', res.headers, "The order_uuid shortcut should not redirect")

        res = self.url_open('/pos/ticket', data={
            'pos_reference': self.pos_order.pos_reference,
            'date_order': self.pos_order.date_order.strftime('%Y-%m-%d'),
            'ticket_code': self.pos_order.ticket_code,
            'csrf_token': self.csrf_token(),
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('No sale order found.', res.text)

        res = self.url_open(f'/pos/ticket/validate?access_token={self.pos_order.access_token}', data={
            'access_token': self.pos_order.access_token,
            'name': 'Hungry Customer',
            'email': 'hungry@customer.com',
            'street': "Test street",
            'city': "Test City",
            'zipcode': '12345',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_1').id,
            'phone': "123456789",
            'csrf_token': self.csrf_token(),
        })
        self.assertEqual(res.status_code, 404)

        self.assertFalse(self.pos_order.account_move, "No invoice should have been created for an unpaid order")
        self.assertEqual(self.pos_order.state, 'draft', "The order should still be waiting for its payment")

    def test_pos_ticket_whitespace_pos_reference(self):
        """Test that a whitespace-only pos_reference is rejected, while an unstripped real reference is successfully found."""
        self.authenticate(None, None)
        self.main_pos_config.open_ui()
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': self.main_pos_config.current_session_id.id,
            'pos_reference': '261-1-000001',
            'ticket_code': '12345',
            'access_token': '1234567890',
            'amount_tax': 0.0,
            'amount_total': 10.0,
            'amount_paid': 10.0,
            'amount_return': 0.0,
            'state': 'paid',
        })

        form_data = {
            'date_order': order.date_order.strftime('%Y-%m-%d'),
            'ticket_code': order.ticket_code,
            'csrf_token': self.csrf_token(),
        }

        res = self.url_open('/pos/ticket', data={**form_data, 'pos_reference': ' ' * 12})
        self.assertIn("Please fill all the required fields.", res.content.decode('utf-8'))

        res = self.url_open('/pos/ticket', data={**form_data, 'pos_reference': f'  {order.pos_reference}  '}, allow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertIn(f'/pos/ticket/validate?access_token={order.access_token}', res.headers['Location'])

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
        response = self.url_open('/my/pos-orders')

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
            invoiced=True,
        )
        self.main_pos_config.current_session_id.close_session_from_ui()

        self.start_tour('/my/home', 'test_portal_store_orders_list_tour', login=portal_user.login)
