# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.mail.tests.common import MailCase
from odoo.addons.payment.tests.common import PaymentCommon


@tagged('post_install', '-at_install')
class TestSaleOrder(WebsiteSaleCommon, MailCase, PaymentCommon):

    def test_delivery_methods_match_order_company(self):
        company_1 = self.env['res.company'].create({'name': 'Test Company 1'})
        company_2 = self.env['res.company'].create({'name': 'Test Company 2'})
        product_delivery_1, product_delivery_2 = self.env['product.product'].create([
            {
                'name': 'Delivery Product 1',
                'type': 'service',
                'company_id': company_1.id,
            },
            {
                'name': 'Delivery Product 2',
                'type': 'service',
                'company_id': company_2.id,
            },
        ])
        delivery_1, delivery_2 = self.env['delivery.carrier'].create([
            {
                'name': 'Delivery 1',
                'delivery_type': 'fixed',
                'product_id': product_delivery_1.id,
                'is_published': True,
            },
            {
                'name': 'Delivery 2',
                'delivery_type': 'fixed',
                'product_id': product_delivery_2.id,
                'is_published': True,
            },
        ])
        sale_order = self.env['sale.order'].create(
            {
                'partner_id': self.partner.id,
                'company_id': company_1.id,
                'order_line': [
                    Command.create(
                        {
                            'product_id': self.product.id,
                        }
                    )],
            }
        )
        available_dms = sale_order._get_delivery_methods()
        self.assertIn(delivery_1, available_dms)
        self.assertNotIn(delivery_2, available_dms)

    def test_website_id_is_set_on_invoice(self):
        """Check that the website is correctly set on invoices created from e-commerce orders."""
        self.cart.action_confirm()
        invoice = self.cart._create_invoices()
        self.assertTrue(self.cart.website_id)
        self.assertEqual(
            self.cart.website_id,
            invoice.website_id,
        )

    def test_unregistered_customer_archiving(self):
        self.cart._archive_partner_if_no_user()
        self.assertFalse(self.cart.partner_id.active)

        # Customers with parent company record (if a parent_name is provided)
        customer = self.env["res.partner"].create({"parent_name": "Company", "name": "Cuzco"})
        billing = self.env["res.partner"].create({
            "parent_id": customer.parent_id.id,
            "type": "invoice",
            "name": "Cuzco Billing",
        })
        cart = self._create_so(partner_id=customer.id)
        self.assertEqual(cart.partner_invoice_id, billing)

        cart._archive_partner_if_no_user()
        self.assertFalse(customer.active)
        self.assertFalse(billing.active)
        self.assertFalse(customer.parent_id.active)

        # Customers without a parent company.
        customer = self.env["res.partner"].create({"name": "Simple"})
        billing = self.env["res.partner"].create({
            "parent_id": customer.id,
            "type": "invoice",
            "name": "Simple Billing",
        })
        cart = self._create_so(partner_id=customer.id)
        self.assertEqual(cart.partner_invoice_id, billing)

        cart._archive_partner_if_no_user()
        self.assertFalse(customer.active)
        self.assertFalse(billing.active)

    def test_customer_archiving_if_has_user(self):
        self._create_new_portal_user(login="whatever", partner_id=self.cart.partner_id.id)
        self.cart._archive_partner_if_no_user()
        self.assertTrue(
            self.cart.partner_id.active, "Registered customers shouldn't be archived on payment"
        )

        # Case when SO is toward the parent company and one of its contact has a user
        customer = self.env["res.partner"].create({"parent_name": "Company", "name": "Cuzco"})
        self._create_new_portal_user(login=f"whatever-{customer.id}", partner_id=customer.id)
        self.assertNotEqual(customer, customer.parent_id)

        cart = self._create_so(partner_id=customer.parent_id.id)
        cart._archive_partner_if_no_user()
        self.assertTrue(
            self.cart.partner_id.active, "Registered company shouldn't be archived if any contact has a user"
        )

    def test_partner_email_confirmation_automatic_invoice(self):
        """Partner receives email confirmation for a
        delivery when automatic_invoice is enabled."""
        self.company.stock_move_email_validation = True
        self.env['ir.config_parameter'].sudo().set_bool('sale.automatic_invoice', True)
        new_so = self._create_so()
        tx = self._create_transaction(flow='redirect', sale_order_ids=[new_so.id], state='done')
        with (
            mute_logger('odoo.addons.sale.models.payment_transaction'),
            self.mock_mail_gateway(),
        ):
            tx._post_process()
        new_so.picking_ids.button_validate()
        self.assertTrue(
            any(partner.email == self.partner.email
            for partner in new_so.picking_ids.message_ids.notified_partner_ids
        ))

    def test_partner_email_confirmation_no_automatic_invoice(self):
        """Partner receives email confirmation for a delivery."""
        self.company.stock_move_email_validation = True
        # self.env['ir.config_parameter'].sudo().set_bool('website_sale.automatic_archiving_of_guest_contacts', False)
        new_so = self._create_so()
        new_so._validate_order()
        new_so.picking_ids.button_validate()
        self.assertTrue(
            any(partner.email == self.partner.email
            for partner in new_so.picking_ids.message_ids.notified_partner_ids
        ))
