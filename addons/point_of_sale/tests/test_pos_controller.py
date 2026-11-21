# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.point_of_sale.tests.common import PosHttpCommon


@tagged('post_install', '-at_install')
class TestPoSController(PosHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wall_shelf.list_price = 10

    def test_qr_code_receipt(self):
        """This test make sure that no user is created when a partner is set on the PoS order.
            It also makes sure that the invoice is correctly created.
        """
        self.authenticate(None, None)
        self.new_partner = self.partner_full
        self.open_new_session()
        self.pos_order = self.create_pos_order([[self.wall_shelf.product_variant_id]], customer=self.new_partner)
        self.close_pos_session()
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
        self.assertEqual(self.env['res.partner'].sudo().search_count([('name', '=', self.new_partner.name)]), 1)
        self.assertTrue(self.pos_order.is_singly_invoiced, "The pos order should have an invoice")
        self.assertTrue(len(self.pos_order.pos_reference) >= 12, "The pos reference should not be less than 12 characters")

    def test_qr_code_receipt_user_connected(self):
        """This test make sure that when the user is already connected he correctly gets redirected to the invoice."""
        self.partner_1 = self.partner_full
        self.partner_1.phone = False
        self.partner_1_user = mail_new_test_user(
            self.env,
            name=self.partner_1.name,
            login='partner_1',
            email=self.partner_1.email,
            groups='base.group_portal',
            partner_id=self.partner_1.id
        )
        self.authenticate('partner_1', 'partner_1')

        self.open_new_session()
        self.pos_order_1 = self.create_pos_order([[self.wall_shelf.product_variant_id]])
        self.close_pos_session()
        res = self.url_open(f'/pos/ticket/validate?access_token={self.pos_order_1.access_token}', timeout=30000)
        # Invoice is not created because user does not contains required field phone
        self.assertIn('The Phone must be filled in your details.', res.content.decode('utf-8'))
        self.assertFalse(self.pos_order_1.is_singly_invoiced, "The pos order should not have an invoice")
        self.assertFalse("my/invoices" in res.url)

        self.partner_1.phone = '+1 (555) 555-5555'
        self.open_new_session()
        self.pos_order_2 = self.create_pos_order([[self.wall_shelf.product_variant_id]])
        self.close_pos_session()
        res = self.url_open(f'/pos/ticket/validate?access_token={self.pos_order_2.access_token}', timeout=30000)
        # Invoice will be created because user contains all required fields
        self.assertNotIn('The Phone must be filled in your details.', res.content.decode('utf-8'))
        self.assertTrue(self.pos_order_2.is_singly_invoiced, "The pos order should have an invoice")
        self.assertTrue("my/invoices" in res.url)

    def test_qr_code_receipt_user_not_connected(self):
        """This test make sure that when the user is not connected (public user). Order should invoiced with public user data."""

        self.open_new_session()
        self.pos_order = self.create_pos_order(
            [[self.wall_shelf.product_variant_id]],
            pos_reference='2500-002-00002',
            ticket_code='inPoS',
        )
        self.close_pos_session()
        self.start_tour('/pos/ticket', 'invoicePoSOrderWithSelfInvocing', login=None)
        self.assertTrue(self.pos_order.account_move, "The pos order should have an invoice after self invoicing")
        self.assertNotEqual(self.pos_order.account_move, self.pos_order.session_id.move_ids)

    def test_qr_code_receipt_with_customer_no_user_connected(self):
        """This test make sure that when the user is not connected (public user) but
            the pos order has a partner, the invoice is correctly created.
            """
        self.new_partner = self.partner_full
        self.open_new_session()
        self.pos_order = self.create_pos_order(
            [[self.wall_shelf.product_variant_id]],
            customer=self.new_partner,
            pos_reference='2500-002-00003',
            ticket_code='inPoS',
        )
        self.close_pos_session()
        self.start_tour('/pos/ticket', 'invoicePoSOrderWithPartner', login=None)
        self.assertTrue(self.pos_order.account_move, "The pos order should have an invoice after self invoicing")

    def test_qr_code_receipt_anonymous_cannot_modify_partner_with_user(self):
        """An anonymous user must not be able to modify a partner that is linked to a user, but still gets the invoice."""
        self.authenticate(None, None)
        self.new_partner_user = mail_new_test_user(
            self.env,
            name=self.partner_full.name,
            login='my_partner',
            partner_id=self.partner_full.id,
            email=self.partner_full.email,
            groups='base.group_portal',
        )
        self.new_partner = self.partner_full
        self.new_partner.write({
            'street': 'Original street',
            'city': 'Original City',
            'zip': '12345',
            'phone': '000000000',
            'state_id': self.env.ref('base.state_us_1').id,
            'country_id': self.env.ref('base.us').id,
        })
        original_name = self.new_partner.name
        original_email = self.new_partner.email
        self.open_new_session()
        self.pos_order = self.create_pos_order([[self.wall_shelf.product_variant_id]], customer=self.new_partner)
        self.close_pos_session()
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
        self.assertEqual(self.new_partner.name, original_name)
        self.assertEqual(self.new_partner.email, original_email)
        self.assertEqual(self.new_partner.street, 'Original street')
        self.assertEqual(self.new_partner.city, 'Original City')
        self.assertEqual(self.new_partner.zip, '12345')
        self.assertEqual(self.new_partner.phone, '000000000')
        self.assertTrue(self.pos_order.account_move, "The pos order should have an invoice")
        self.assertTrue("my/invoices" in res.url)

    def test_qr_code_receipt_user_updated(self):
        """This test make sure that when the user is already connected he correctly gets redirected to the invoice."""
        self.authenticate(None, None)
        self.partner_1 = self.partner_test_1
        self.partner_1.email = 'valid.lelitre@agrolait.com'

        self.open_new_session()

        # Invoice will be directly created if the public user and order has a partner
        self.pos_order_1 = self.create_pos_order([[self.wall_shelf.product_variant_id]], customer=self.partner_1)
        self.close_pos_session()
        res = self.url_open(f'/pos/ticket/validate?access_token={self.pos_order_1.access_token}', timeout=30000)
        self.assertTrue(self.pos_order_1.is_singly_invoiced, "The pos order should have an invoice")
        self.assertTrue("my/invoices" in res.url)

        # Order without a customer should create a new partner using the submitted form data by public user.
        self.open_new_session()
        self.pos_order_2 = self.create_pos_order([[self.wall_shelf.product_variant_id]])
        self.close_pos_session()
        get_invoice_data = {
            'access_token': self.pos_order_2.access_token,
            'name': 'New Customer',
            'email': 'test@test.com',
            'vat': 'VAT_TEST_NUMBER_124',
            'street': 'Test street',
            'city': 'Test City',
            'zipcode': '12345',
            'country_id': self.partner_full.country_id.id,
            'phone': '123456789',
            'state_id': self.partner_full.state_id.id,
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
        self.open_new_session()
        self.pos_order = self.create_pos_order(
            [[self.wall_shelf.product_variant_id]],
            state='draft',
            pos_reference='2500-002-00004',
            ticket_code='unpad',
        )
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
