# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from unittest.mock import patch

from werkzeug.exceptions import Forbidden

from odoo import api
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseUsersCommon
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


@tagged('post_install', '-at_install')
class TestCheckoutAddress(BaseUsersCommon, WebsiteSaleCommon):
    """Test the address management part of the checkout process:

    * address creation (/shop/address)
    * address update (/shop/address)
    * address choice (/shop/checkout)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country_id = cls.country_be.id
        cls.user_internal.partner_id.company_id = cls.env.company

    def setUp(self):
        super().setUp()
        self.WebsiteSaleController = WebsiteSale()
        self.default_address_values = {
            'name': 'a res.partner address',
            'email': 'email@email.email',
            'street': 'ooo',
            'city': 'ooo',
            'zip': '1200',
            'country_id': self.country_id,
            'phone': '+333333333333333',
            'address_type': 'delivery',
        }
        self.default_billing_address_values = dict(
            self.default_address_values, address_type='billing',
        )

    def _get_last_address(self, partner):
        """ Useful to retrieve the last created address (shipping or billing) """
        return partner.child_ids.sorted('id', reverse=True)[0]

    # TEST WEBSITE
    def test_01_create_shipping_address_specific_user_account(self):
        ''' Ensure `website_id` is correctly set (specific_user_account) '''
        p = self.env.user.partner_id
        p.active = True
        so = self._create_so(partner_id=p.id)

        with MockRequest(self.env, website=self.website, sale_order_id=so.id) as req:
            req.httprequest.method = "POST"
            self.WebsiteSaleController.shop_address_submit(**self.default_address_values)
            self.assertFalse(self._get_last_address(p).website_id, "New shipping address should not have a website set on it (no specific_user_account).")

            self.website.specific_user_account = True

            self.WebsiteSaleController.shop_address_submit(**self.default_address_values)
            self.assertEqual(self._get_last_address(p).website_id, self.website, "New shipping address should have a website set on it (specific_user_account).")

    # TEST COMPANY
    def _setUp_multicompany_env(self):
        ''' Have 2 companies A & B.
            Have 1 website 1 which company is B
            Have admin on company A
        '''
        self.company_a, self.company_b, self.company_c = self.env['res.company'].create([
            {'name': 'Company A'},
            {'name': 'Company B'},
            {'name': 'Company C'},
        ])
        self.website.company_id = self.company_b
        self.env.user.company_id = self.company_a

        self.demo_user = self.user_internal
        self.demo_user.company_ids += self.company_b
        self.demo_user.company_id = self.company_b
        self.demo_partner = self.demo_user.partner_id

        self.portal_user = self.user_portal
        self.portal_partner = self.portal_user.partner_id

    def test_02_demo_address_and_company(self):
        ''' This test ensure that the company_id of the address (partner) is
            correctly set and also, is not wrongly changed.
            eg: new shipping should use the company of the website and not the
                one from the admin, and editing a billing should not change its
                company.
        '''
        self._setUp_multicompany_env()
        so = self._create_so(partner_id=self.demo_partner.id)

        env = api.Environment(self.env.cr, self.demo_user.id, {})
        # change also website env for `sale_get_order` to not change order partner_id
        with MockRequest(env, website=self.website.with_env(env), sale_order_id=so.id) as req:
            req.httprequest.method = "POST"

            # 1. Logged in user, new shipping
            self.WebsiteSaleController.shop_address_submit(**self.default_address_values)
            new_shipping = self._get_last_address(self.demo_partner)
            self.assertTrue(new_shipping.company_id != self.env.user.company_id, "Logged in user new shipping should not get the company of the sudo() neither the one from it's partner..")
            self.assertEqual(new_shipping.company_id, self.website.company_id, ".. but the one from the website.")

            # 2. Logged in user/internal user, should not edit name or email address of billing
            self.default_address_values['partner_id'] = self.demo_partner.id
            self.WebsiteSaleController.shop_address_submit(**self.default_billing_address_values)
            self.assertEqual(self.demo_partner.company_id, self.company_b, "Logged in user edited billing (the partner itself) should not get its company modified.")
            self.assertNotEqual(self.demo_partner.name, self.default_address_values['name'], "Employee cannot change their name during the checkout process.")
            self.assertNotEqual(self.demo_partner.email, self.default_address_values['email'], "Employee cannot change their email during the checkout process.")

    def test_03_public_user_address_and_company(self):
        ''' Same as test_02 but with public user '''
        self._setUp_multicompany_env()
        so = self._create_so(partner_id=self.website.user_id.partner_id.id)

        env = api.Environment(self.env.cr, self.website.user_id.id, {})
        # change also website env for `sale_get_order` to not change order partner_id
        with MockRequest(env, website=self.website.with_env(env), sale_order_id=so.id) as req:
            req.httprequest.method = "POST"

            # 1. Public user, new billing
            self.default_address_values['partner_id'] = -1
            self.WebsiteSaleController.shop_address_submit(**self.default_address_values)
            new_partner = so.partner_id
            self.assertNotEqual(new_partner, self.website.user_id.partner_id, "New billing should have created a new partner and assign it on the SO")
            self.assertEqual(new_partner.company_id, self.website.company_id, "The new partner should get the company of the website")

            # 2. Public user, edit billing
            self.default_address_values['partner_id'] = new_partner.id
            self.WebsiteSaleController.shop_address_submit(**self.default_billing_address_values)
            self.assertEqual(new_partner.company_id, self.website.company_id, "Public user edited billing (the partner itself) should not get its company modified.")

    def test_03_carrier_rate_on_shipping_address_change(self):
        """ Test that when a shipping address is changed the price of delivery is recalculated
        and updated on the order."""
        partner = self.env.user.partner_id
        order = self._create_so()
        order.carrier_id = self.carrier.id  # Set the carrier on the order.
        shipping_partner_values = {'name': 'dummy', 'parent_id': partner.id, 'type': 'delivery'}
        shipping_partner = self.env['res.partner'].create(shipping_partner_values)
        order.partner_shipping_id = shipping_partner
        with MockRequest(self.env, website=self.website, sale_order_id=order.id), patch(
            'odoo.addons.delivery.models.delivery_carrier.DeliveryCarrier.rate_shipment',
            return_value={'success': True, 'price': 10, 'warning_message': ''}
        ) as rate_shipment_mock:
            # Change a shipping address of the order in the checkout.
            shipping_partner2 = shipping_partner.copy()
            self.WebsiteSaleController.shop_update_address(
                partner_id=shipping_partner2.id, address_type='delivery'
            )
            self.assertGreaterEqual(
                rate_shipment_mock.call_count,
                1,
                msg="The carrier rate must be recalculated when shipping address is changed.",
            )
            self.assertEqual(
                order.order_line.filtered(lambda l: l.is_delivery)[0].price_unit,
                10,
                msg="The recalculated delivery price must be updated on the order.",
            )

    def test_04_apply_empty_pl(self):
        ''' Ensure empty pl code reset the applied pl '''
        so = self._create_so(partner_id=self.env.user.partner_id.id)
        eur_pl = self.env['product.pricelist'].create({
            'name': 'EUR_test',
            'website_id': self.website.id,
            'code': 'EUR_test',
        })

        with MockRequest(self.env, website=self.website, sale_order_id=so.id):
            self.WebsiteSaleController.pricelist('EUR_test')
            self.assertEqual(so.pricelist_id, eur_pl, "Ensure EUR_test is applied")

            self.WebsiteSaleController.pricelist('')
            self.assertNotEqual(so.pricelist_id, eur_pl, "Pricelist should be removed when sending an empty pl code")

    def test_04_pl_reset_on_login(self):
        """Check that after login, the SO pricelist is correctly recomputed."""
        test_user = self.env['res.users'].create({
            'name': 'Toto',
            'login': 'long_enough_password',
            'password': 'long_enough_password',
        })
        pl_with_code = self.env['product.pricelist'].create({
            'name': 'EUR_test',
            'website_id': self.website.id,
            'code': 'EUR_test',
        })
        self.website.user_id.partner_id.property_product_pricelist = self.pricelist
        test_user.partner_id.property_product_pricelist = pl_with_code

        public_user_env = self.env(user=self.website.user_id)
        so = self._create_so(partner_id=public_user_env.user.partner_id.id)
        self.assertEqual(so.pricelist_id, self.pricelist)

        with MockRequest(
            self.env, website=self.website,
            sale_order_id=so.id,
            website_sale_current_pl=so.pricelist_id.id
        ):
            self.assertEqual(self.website.pricelist_id, self.pricelist)
            order = self.website.with_env(public_user_env).sale_get_order()
            self.assertEqual(order, so)
            self.assertEqual(order.pricelist_id, self.pricelist)
            order_b = self.website.with_user(test_user).sale_get_order()
            self.assertEqual(order, order_b)
            self.assertEqual(order_b.pricelist_id, pl_with_code)

    # TEST WEBSITE & MULTI COMPANY

    def test_05_create_so_with_website_and_multi_company(self):
        ''' This test ensure that the company_id of the website set on the order
            is the same as the env company or the one set on the order.
        '''
        self._setUp_multicompany_env()
        # No company on the SO
        so = self._create_so(partner_id=self.demo_partner.id)
        self.assertEqual(so.company_id, self.website.company_id)

        # Same company on the SO and the env user company but no website
        with self.assertRaises(ValueError, msg="Should not be able to create SO with company different than the website company"):
            self._create_so(partner_id=self.demo_partner.id, company_id=self.company_a.id)

        # Same company on the SO and the website company
        so = self._create_so(partner_id=self.demo_partner.id, company_id=self.company_b.id)
        self.assertEqual(so.company_id, self.website.company_id)

        # Different company on the SO and the env user company
        with self.assertRaises(ValueError, msg="Should not be able to create SO with company different than the website company"):
            self._create_so(partner_id=self.demo_partner.id, company_id=self.company_c.id)

    def test_06_portal_user_address_and_company(self):
        ''' Same as test_03 but with portal user '''
        self._setUp_multicompany_env()
        so = self._create_so(partner_id=self.portal_partner.id)

        env = api.Environment(self.env.cr, self.portal_user.id, {})
        # change also website env for `sale_get_order` to not change order partner_id
        with MockRequest(env, website=self.website.with_env(env), sale_order_id=so.id) as req:
            req.httprequest.method = "POST"

            # 1. Portal user, new shipping, same with the log in user
            self.WebsiteSaleController.shop_address_submit(**self.default_address_values)
            new_shipping = self._get_last_address(self.portal_partner)
            self.assertTrue(new_shipping.company_id != self.env.user.company_id, "Portal user new shipping should not get the company of the sudo() neither the one from it's partner..")
            self.assertEqual(new_shipping.company_id, self.website.company_id, ".. but the one from the website.")

            # 2. Portal user, edit billing
            self.default_address_values['partner_id'] = self.portal_partner.id
            self.WebsiteSaleController.shop_address_submit(**self.default_billing_address_values)
            # Name cannot be changed if there are issued invoices
            self.assertNotEqual(self.portal_partner.name, self.default_address_values['name'], "Portal User should not be able to change the name if they have invoices under their name.")

    def test_07_change_fiscal_position(self):
        """
            Check that the sale order is updated when you change fiscal position.
            Change fiscal position by modifying address during checkout process.
        """
        self.env.company.country_id = self.country_us
        be_address_POST, nl_address_POST = [
            {
                'name': 'Test name', 'email': 'test@email.com', 'street': 'test', 'phone': '+333333333333333',
                'city': 'test', 'zip': '3000', 'country_id': self.env.ref('base.be').id, 'submitted': 1,
                'partner_id': self.partner.id,
                'callback': '/shop/checkout',
            },
            {
                'name': 'Test name', 'email': 'test@email.com', 'street': 'test', 'phone': '+333333333333333',
                'city': 'test', 'zip': '3000', 'country_id': self.env.ref('base.nl').id, 'submitted': 1,
                'partner_id': self.partner.id,
                'callback': '/shop/checkout',
            },
        ]

        tax_10_incl, tax_20_excl, tax_15_incl = self.env['account.tax'].create([
            {'name': 'Tax 10% incl', 'amount': 10, 'price_include_override': 'tax_included'},
            {'name': 'Tax 20% excl', 'amount': 20, 'price_include_override': 'tax_excluded'},
            {'name': 'Tax 15% incl', 'amount': 15, 'price_include_override': 'tax_included'},
        ])
        fpos_be, fpos_nl = self.env['account.fiscal.position'].create([
            {
                'sequence': 1,
                'name': 'BE',
                'auto_apply': True,
                'country_id': self.env.ref('base.be').id,
                'tax_ids': [Command.create({'tax_src_id': tax_10_incl.id, 'tax_dest_id': tax_20_excl.id})],
            },
            {
                'sequence': 2,
                'name': 'NL',
                'auto_apply': True,
                'country_id': self.env.ref('base.nl').id,
                'tax_ids': [Command.create({'tax_src_id': tax_10_incl.id, 'tax_dest_id': tax_15_incl.id})],
            },
        ])

        product = self.env['product.product'].create({
            'name': 'Product test',
            'list_price': 100,
            'website_published': True,
            'sale_ok': True,
            'taxes_id': [tax_10_incl.id]
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'website_id': self.website.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'name': 'Product test',
            })]
        })

        self.assertEqual(
            [so.amount_untaxed, so.amount_tax, so.amount_total],
            [90.91, 9.09, 100.0]
        )

        env = api.Environment(self.env.cr, self.website.user_id.id, {})
        with MockRequest(self.env, website=self.website.with_env(env), sale_order_id=so.id) as req:
            req.httprequest.method = "POST"

            self.WebsiteSaleController.shop_address_submit(**be_address_POST)
            self.assertEqual(
                so.fiscal_position_id,
                fpos_be,
            )
            self.assertEqual(
                [so.amount_untaxed, so.amount_tax, so.amount_total],
                [90.91, 18.18, 109.09] # (100 : (1 + 10%)) * (1 + 20%) = 109.09
            )

            self.WebsiteSaleController.shop_address_submit(**nl_address_POST)
            self.assertEqual(
                so.fiscal_position_id,
                fpos_nl,
            )
            self.assertEqual(
                [so.amount_untaxed, so.amount_tax, so.amount_total],
                [90.91, 13.64, 104.55] # (100 : (1 + 10%)) * (1 + 15%) = 104.55
            )

    def test_08_new_user_address_state(self):
        ''' Test the billing and shipping addresses creation values. '''
        self._setUp_multicompany_env()
        so = self._create_so(partner_id=self.demo_partner.id)

        env = api.Environment(self.env.cr, self.demo_user.id, {})
        # change also website env for `sale_get_order` to not change order partner_id
        with MockRequest(env, website=self.website.with_env(env), sale_order_id=so.id) as req:
            req.httprequest.method = "POST"

            # check the default values
            self.assertEqual(self.demo_partner, so.partner_invoice_id)
            self.assertEqual(self.demo_partner, so.partner_shipping_id)

            # 1. Logged-in user, new shipping
            self.WebsiteSaleController.shop_address_submit(**self.default_address_values)
            new_shipping = self._get_last_address(self.demo_partner)
            msg = "New shipping address should have its type set as 'delivery'"
            self.assertTrue(new_shipping.type == 'delivery', msg)

            # 2. Logged-in user, new billing
            self.WebsiteSaleController.shop_address_submit(**self.default_billing_address_values)
            new_billing = self._get_last_address(self.demo_partner)
            msg = "New billing should have its type set as 'invoice'"
            self.assertTrue(new_billing.type == 'invoice', msg)
            self.assertNotEqual(new_billing, self.demo_partner)

            # 3. Check that invoice/shipping address of so changed
            self.assertEqual(new_billing, so.partner_invoice_id)
            self.assertEqual(new_shipping, so.partner_shipping_id)

            # 4. Logged-in user, new delivery, use delivery as billing
            use_delivery_as_billing = (
                self.default_address_values | {'use_delivery_as_billing': 'true'}
            )
            self.WebsiteSaleController.shop_address_submit(**use_delivery_as_billing)
            new_delivery_use_same = self._get_last_address(self.demo_partner)
            msg = "New delivery use same should have its type set as 'other'"
            self.assertTrue(new_delivery_use_same.type == 'other', msg)
            self.assertNotEqual(new_billing, self.demo_partner)

            # 5. Check that invoice/shipping address of so changed
            self.assertEqual(new_delivery_use_same, so.partner_invoice_id)
            self.assertEqual(new_delivery_use_same, so.partner_shipping_id)

            # 6. forbid address page opening with wrong partners:
            with self.assertRaises(Forbidden):
                self.WebsiteSaleController.shop_address_submit(
                    partner_id=self.env.user.partner_id.id, address_type='billing'
                )
            with self.assertRaises(Forbidden):
                self.WebsiteSaleController.shop_address_submit(
                    partner_id=self.env.user.partner_id.id, address_type='delivery'
                )

    def test_09_shop_update_address(self):
        self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', 4)
        user = self.env['res.users'].create({
            'name': 'test',
            'login': 'test',
            'password': 'test',
        })
        user_partner = user.partner_id
        partner_company = self.env['res.partner'].create({
            'name': 'My company',
            'is_company': True,
            'child_ids': [Command.link(user_partner.id)],
        })
        colleague = self.env['res.partner'].create({
            'parent_id': partner_company.id,
            'name': 'whatever',
        })
        colleague_shipping = self.env['res.partner'].create({
            'parent_id': colleague.id,
            'name': 'whatever',
            'type': 'delivery',
        })

        self.assertEqual(partner_company.commercial_partner_id, partner_company)
        self.assertEqual(user_partner.commercial_partner_id, partner_company)

        invoicing, shipping, bad_invoicing, bad_shipping = self.env['res.partner'].create([
            {
                'name': 'Invoicing',
                'street': '215 Vine St',
                'city': 'Scranton',
                'zip': '18503',
                'country_id': self.country_us.id,
                'state_id': self.country_us_state_id,
                'phone': '+1 555-555-5555',
                'email': 'admin@yourcompany.example.com',
                'type': 'invoice',
                'parent_id': user_partner.id,
            },
            {
                'name': 'Shipping',
                'street': '215 Vine St',
                'city': 'Scranton',
                'zip': '18503',
                'country_id': self.country_us.id,
                'state_id': self.country_us_state_id,
                'phone': '+1 555-555-5555',
                'email': 'admin@yourcompany.example.com',
                'type': 'delivery',
                'parent_id': user_partner.id,
            },
            {
                'name': 'Invalid billing', # missing email
                'street': '215 Vine St',
                'city': 'Scranton',
                'zip': '18503',
                'country_id': self.country_us.id,
                'state_id': self.country_us_state_id,
                'phone': '+1 555-555-5555',
                'type': 'invoice',
                'parent_id': user_partner.id,
            },
            {
                'name': 'Invalid Shipping',
                'type': 'delivery',
                'parent_id': user_partner.id,
            },
        ])

        so = self._create_so(partner_id=user_partner.id)
        self.assertNotEqual(so.partner_shipping_id, shipping)
        self.assertNotEqual(so.partner_invoice_id, invoicing)
        self.assertFalse(colleague._can_be_edited_by_current_customer(so, 'billing'))
        self.assertFalse(colleague._can_be_edited_by_current_customer(so, 'delivery'))

        env = api.Environment(self.env.cr, user.id, {})
        # change also website env for `sale_get_order` to not change order partner_id
        with MockRequest(env, website=self.website.with_env(env), sale_order_id=so.id):

            # Invalid addresses unaccessible to current customer
            with self.assertRaises(Forbidden):
                # cannot use contact type addresses
                self.WebsiteSaleController.shop_update_address(partner_id=colleague.id)
            with self.assertRaises(Forbidden):
                # unrelated partner
                self.WebsiteSaleController.shop_update_address(partner_id=self.env.user.partner_id.id)

            # Good addresses
            self.WebsiteSaleController.shop_update_address(
                partner_id=colleague_shipping.id, address_type='delivery')
            self.assertEqual(so.partner_shipping_id, colleague_shipping)
            self.WebsiteSaleController.shop_update_address(
                partner_id=shipping.id, address_type='delivery',
            )
            self.assertEqual(so.partner_shipping_id, shipping)

            self.WebsiteSaleController.shop_update_address(
                partner_id=invoicing.id, address_type='billing',
            )
            self.assertEqual(so.partner_shipping_id, shipping)
            self.assertEqual(so.partner_invoice_id, invoicing)

            # Using invalid addresses --> change and the customer is forced to update the address
            self.WebsiteSaleController.shop_update_address(
                partner_id=bad_invoicing.id, address_type='billing')
            self.assertEqual(so.partner_invoice_id, bad_invoicing)
            redirection = self.WebsiteSaleController._check_addresses(so)
            self.assertTrue(redirection is not None)
            self.assertEqual(redirection.location, f'/shop/address?partner_id={bad_invoicing.id}&address_type=billing')

            # reset to valid one
            self.WebsiteSaleController.shop_update_address(
                partner_id=invoicing.id, address_type='billing',
            )

            self.WebsiteSaleController.shop_update_address(
                partner_id=bad_shipping.id, address_type='delivery')
            self.assertEqual(so.partner_shipping_id, bad_shipping)
            redirection = self.WebsiteSaleController._check_addresses(so)
            self.assertTrue(redirection is not None)
            self.assertEqual(redirection.location, f'/shop/address?partner_id={bad_shipping.id}&address_type=delivery')

            # reset to valid one
            self.WebsiteSaleController.shop_update_address(
                partner_id=shipping.id, address_type='delivery',
            )

            # Using commercial partner address
            self.WebsiteSaleController.shop_update_address(
                partner_id=partner_company.id, address_type='billing',
            )
            self.assertEqual(so.partner_invoice_id, partner_company)
            self.WebsiteSaleController.shop_update_address(
                partner_id=partner_company.id, address_type='delivery',
            )
            self.assertEqual(so.partner_shipping_id, partner_company)

    def test_10_addresses_updates(self):
        # TODO dispatch test to sale & account
        partner_company = self.env['res.partner'].create({
            'name': 'My company',
            'is_company': True,
            'child_ids': [
                Command.create({
                    'name': 'partner_1',
                }),
                Command.create({
                    'name': 'partner_2',
                }),
                Command.create({
                    'name': 'partner_3',
                }),
            ],
        })
        partner_1, _partner_2, _partner_3 = partner_company.child_ids
        self.assertTrue(partner_company.can_edit_vat())
        self.assertTrue(partner_company._can_edit_name())
        self.assertTrue(all(not p.can_edit_vat() for p in partner_company.child_ids))
        self.assertTrue(all(p._can_edit_name() for p in partner_company.child_ids))

        dumb_product = self.env['product.product'].create({'name': 'test'})
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner_company.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': dumb_product.id,
                })
            ],
        })
        invoice.action_post()

        self.assertEqual(invoice.state, 'posted')
        self.assertFalse(partner_company.can_edit_vat())
        self.assertFalse(partner_company._can_edit_name())
        self.assertTrue(all(p._can_edit_name() for p in partner_company.child_ids))
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner_1.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': dumb_product.id,
                })
            ],
        })
        invoice.action_post()
        self.assertFalse(partner_1._can_edit_name())

    def test_11_payment_term_when_address_change(self):
        """Make sure the expected payment terms are set on ecommerce orders"""
        self.portal_user = self.user_portal
        self.portal_partner = self.portal_user.partner_id
        self.assertFalse(self.portal_partner.property_payment_term_id)
        so = self._create_so(partner_id=self.portal_partner.id)
        self.assertTrue(so.payment_term_id, "A payment term should be set by default on the sale order")

        env = api.Environment(self.env.cr, self.portal_user.id, {})
        with MockRequest(env, website=self.website.with_env(env).with_context(website_id=self.website.id)) as req:
            req.httprequest.method = "POST"

            self.default_address_values['partner_id'] = self.portal_partner.id
            self.WebsiteSaleController.shop_address_submit(**self.default_billing_address_values)
            self.assertTrue(so.payment_term_id, "A payment term should still be set on the sale order")

            so.website_id = False
            so._compute_payment_term_id()
            self.assertFalse(so.payment_term_id, "The website default payment term should not be set on a sale order not coming from the website")

    def test_12_recompute_taxes_on_address_change(self):
        self.env.company.country_id = self.env.ref('base.us')
        tax_15_incl, tax_0 = self.env['account.tax'].create([
            {
                'name': "15% excl",
                'amount': 15,
                'price_include_override': 'tax_included',
            },
            {
                'name': "0%",
                'amount': 0,
            },
        ])
        fpos_be = self.env['account.fiscal.position'].create({
            'name': "Fiscal Position BE",
            'auto_apply': True,
            'country_id': self.country_id,
            'tax_ids': [Command.create({
                'tax_src_id': tax_15_incl.id,
                'tax_dest_id': tax_0.id,
            })],
        })
        self.product.taxes_id = [Command.set(tax_15_incl.ids)]
        self.partner.country_id = self.country_id

        cart = self.empty_cart
        cart.order_line = [Command.create({'product_id': self.product.id})]
        amount_untaxed = cart.amount_untaxed

        self.assertEqual(cart.fiscal_position_id, fpos_be)
        self.assertEqual(cart.order_line.tax_id, tax_0)

        self.partner.country_id = self.env.company.country_id
        self.assertNotEqual(cart.fiscal_position_id, fpos_be)
        self.assertEqual(cart.order_line.tax_id, tax_15_incl)
        self.assertEqual(cart.amount_untaxed, amount_untaxed, "Untaxed amount should not change")

        cart.action_confirm()
        self.partner.country_id = self.country_id
        self.assertEqual(
            cart.order_line.tax_id, tax_15_incl,
            "Tax should no longer change after order confirmation",
        )

    def test_imported_user_with_trailing_name_can_checkout(self):
        """Ensure that an imported user with trailing spaces in their name can complete checkout without error."""

        imported_user = self.env['res.users'].create({
            'name': 'Imported User ',  # trailing space
            'login': 'imported_user',
            'email': 'imported@example.com',
        })
        imported_partner = imported_user.partner_id
        so = self._create_so(partner_id=imported_partner.id)

        env = api.Environment(self.env.cr, imported_user.id, {})
        with MockRequest(env, website=self.website.with_env(env), sale_order_id=so.id) as req:
            req.httprequest.method = "POST"

            values = {
                'name': 'Imported User',  # trimmed input
                'email': 'imported@example.com',
                'street': '123 Some Street',
                'city': 'Cityville',
                'zip': '12345',
                'country_id': self.country_id,
                'phone': '+33123456789',
                'partner_id': imported_partner.id,
                'address_type': 'delivery',
                'use_delivery_as_billing': 'true',
            }
            res = self.WebsiteSaleController.shop_address_submit(**values).data
            self.assertIsNotNone(json.loads(res).get('redirectUrl'), "We should get a 'redirectUrl' in the response")
