# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo.addons.approvals_purchase.tests.common import TestApprovalsCommon
from odoo.exceptions import UserError
from odoo.tests.common import Form


class TestApprovalsPurchase(TestApprovalsCommon):

    def get_purchase_order_for_seller(self, seller):
        return self.env['purchase.order'].search([
            ('partner_id', '=', seller.id)
        ])

    def test_01_create_purchase_request(self):
        """ Creates new purchase request then verifies all is correctly set. """
        request_form = self.create_request_form()
        request_purchase = request_form.save()

        self.assertEqual(request_purchase.has_product, 'required')
        self.assertEqual(request_purchase.has_quantity, 'required',
            "A purchase request must have `has_quantity` forced on 'required'.")
        self.assertEqual(request_purchase.has_product, 'required',
            "A purchase request must have `has_product` forced on 'required'.")

    def test_02_check_constrains(self):
        """ Checks all constrains are respected and all errors are raised. """
        # Create a new purchase request and save it.
        request_form = self.create_request_form(approver=self.user_approver)
        request_purchase = request_form.save()
        # Try to submit it without any product lines -> must raise an UserError.
        with self.assertRaises(UserError):
            request_purchase.action_confirm()

        # Add new lines, they require a description but a onchange will fill the
        # description automatically if we set the product id.
        request_form = Form(request_purchase)
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_mouse
            line.quantity = 1
        with request_form.product_line_ids.new() as line:
            line.description = "The thing with a screen and a keyboard..."
            line.quantity = 1
        # Try to validate, should be OK now.
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        self.assertEqual(request_purchase.request_status, 'pending')

        # Try to approve it...
        with self.assertRaises(UserError):
            # ... but raise an error because all product line need a product_id.
            request_purchase.action_approve()
        # Edit the line without product id then try to approve it again.
        request_purchase.action_draft()
        request_form = Form(request_purchase)
        with request_form.product_line_ids.edit(1) as line:
            line.product_id = self.product_computer
        request_purchase = request_form.save()
        request_purchase.with_user(self.user_approver).action_approve()
        # ... should be approved now.
        self.assertEqual(request_purchase.request_status, 'approved')

        # Try to generate a purchase order from the request...
        with self.assertRaises(UserError):
            # ... but must fail because mouse product doesn't have any seller.
            request_purchase.action_create_purchase_orders()
        self.assertEqual(request_purchase.purchase_order_count, 0)
        # Edit mouse product to add a vendor, then try again.
        self.product_mouse.seller_ids = [(0, 0, {
            'partner_id': self.partner_seller_1.id,
            'min_qty': 1,
            'price': 15,
        })]
        # Should be ok now, check the approval request has purchase order.
        request_purchase.action_create_purchase_orders()
        self.assertEqual(request_purchase.purchase_order_count, 1)

    def test_purchase_01_check_create_purchase(self):
        """ Checks an approval purchase request will create a new purchase order
        and checks also this purchase will have the right seller when create
        purchase (depending of the vendor price list). """
        # Checks we have really no purchase orders for the sellers.
        po_for_seller_1 = self.get_purchase_order_for_seller(self.partner_seller_1)
        po_for_seller_2 = self.get_purchase_order_for_seller(self.partner_seller_2)
        self.assertEqual(len(po_for_seller_1), 0)
        self.assertEqual(len(po_for_seller_2), 0)
        # Create a new purchase request for 9 computers. The selected seller for
        # the purchase order must be partner_seller_1 because he is the one who
        # has the best price under 10 units.
        request_form = self.create_request_form(approver=self.user_approver)
        # Create a purchase product line.
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_computer
            line.quantity = 9
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()

        # Check we have a purchase order and if it is correclty set.
        self.assertEqual(request_purchase.purchase_order_count, 1)
        purchase_order = self.get_purchase_order(request_purchase, 0)
        self.assertEqual(purchase_order.partner_id.id, self.partner_seller_1.id)
        self.assertEqual(len(purchase_order.order_line), 1)
        self.assertEqual(purchase_order.origin, request_purchase.name)
        # Check the purchase order line fields.
        po_line = purchase_order.order_line[0]
        self.assertEqual(po_line.product_qty, 9)
        self.assertEqual(po_line.price_unit, 250)

        # Checks to be sure we created only one purchase order for the seller_1.
        po_for_seller_1 = self.get_purchase_order_for_seller(self.partner_seller_1)
        po_for_seller_2 = self.get_purchase_order_for_seller(self.partner_seller_2)
        self.assertEqual(len(po_for_seller_1), 1)
        self.assertEqual(len(po_for_seller_2), 0)

        # check that the payment term is set
        self.assertEqual(po_for_seller_1.payment_term_id, self.payment_terms)

        # Now, do the same but for 12 computers. The selected seller for the
        # purchase order must be partner_seller_2 because he has better price
        # than partner_seller_1 for 10 units or more.
        request_form = self.create_request_form(approver=self.user_approver)
        # Create a purchase product line.
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_computer
            line.quantity = 12
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()

        # Check we have a purchase order and if it is correclty set.
        self.assertEqual(request_purchase.purchase_order_count, 1)
        purchase_order = self.get_purchase_order(request_purchase, 0)
        self.assertEqual(purchase_order.partner_id.id, self.partner_seller_2.id)
        self.assertEqual(len(purchase_order.order_line), 1)
        self.assertEqual(purchase_order.origin, request_purchase.name)
        # Check the purchase order line fields.
        po_line = purchase_order.order_line[0]
        self.assertEqual(po_line.product_qty, 12)
        self.assertEqual(po_line.price_unit, 230)

        # Checks we created a another purchase order for seller_2 now.
        po_for_seller_1 = self.get_purchase_order_for_seller(self.partner_seller_1)
        po_for_seller_2 = self.get_purchase_order_for_seller(self.partner_seller_2)
        self.assertEqual(len(po_for_seller_1), 1)
        self.assertEqual(len(po_for_seller_2), 1)

    def test_purchase_02_add_order_line(self):
        """ Checks we don't create a new purchase order but modify the existing
        one, creating a new purchase order line if needed. """
        # Create a purchase order for partner_seller_1 without order lines.
        po_origin = 'From an another galaxy'
        purchase_order = self.create_purchase_order(origin=po_origin)

        # Create a new purchase request who will update the purchase order and
        # add into it a new purchase order line.
        request_form = self.create_request_form(approver=self.user_approver)
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_computer
            line.quantity = 4
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()
        # Check we have a purchase order and if it is correclty set.
        self.assertEqual(request_purchase.purchase_order_count, 1)
        request_po = self.get_purchase_order(request_purchase, 0)
        self.assertEqual(
            request_po.id, purchase_order.id,
            "The purchase order linked to the AR must be the existing one."
        )
        self.assertEqual(
            purchase_order.origin, (po_origin + ', ' + request_purchase.name)
        )
        self.assertEqual(len(purchase_order.order_line), 1)
        # Check the purchase order line fields.
        po_line = purchase_order.order_line[0]
        self.assertEqual(po_line.product_qty, 4)
        self.assertEqual(po_line.price_unit, 250)

    def test_purchase_03_edit_order_line(self):
        """ Checks we don't create a new purchase order but modify the existing
        one, increasing the product quantity of the existing order line. """
        # Create a purchase order for partner_seller_1 with an order line.
        po_origin = 'From an another galaxy'
        purchase_order = self.create_purchase_order(
            origin=po_origin,
            lines=[{
                'product': self.product_computer,
                'price': 250,
                'quantity': 10,
            }]
        )

        # Create a new purchase request who will update the purchase order and
        # modify the product quantity of its purchase order line.
        request_form = self.create_request_form(approver=self.user_approver)
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_computer
            line.quantity = 4
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()
        # Check we have a purchase order and if it is correclty set.
        self.assertEqual(request_purchase.purchase_order_count, 1)
        request_po = self.get_purchase_order(request_purchase)
        self.assertEqual(
            request_po.id, purchase_order.id,
            "The purchase order linked to the AR must be the existing one."
        )
        self.assertEqual(
            purchase_order.origin, (po_origin + ', ' + request_purchase.name)
        )
        self.assertEqual(len(purchase_order.order_line), 1)
        # Check the purchase order line fields.
        po_line = purchase_order.order_line[0]
        self.assertEqual(po_line.product_qty, 14)
        self.assertEqual(po_line.price_unit, 250)

    def test_purchase_04_create_multiple_purchase(self):
        """ Checks purchase approval requests with multiple product lines will,
        in function of how they are set, create purchase order, add purchase
        order line or edit the product quantity of the order line. """
        # Add seller for product mouse.
        self.product_mouse.seller_ids = [(0, 0, {
            'partner_id': self.partner_seller_1.id,
            'min_qty': 1,
            'price': 15,
        })]
        # Create a purchase order with a order line for some computers.
        purchase_order_1 = self.create_purchase_order(lines=[{
            'product': self.product_computer,
            'price': 250,
            'quantity': 7
        }])
        # Create and edit an approval request.
        request_form = self.create_request_form(approver=self.user_approver)
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_mouse
            line.quantity = 20
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_computer
            line.quantity = 10
        # Confirm, approves and ask to create purchase orders.
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()

        self.assertEqual(
            request_purchase.purchase_order_count, 2,
            "Must have two purchase orders linked to the approval request."
        )
        request_po = self.get_purchase_order(request_purchase, 0)
        self.assertEqual(
            request_po.id, purchase_order_1.id,
            "The first purchase order must the already existing one."
        )
        self.assertEqual(len(purchase_order_1.order_line), 2)
        self.assertEqual(
            purchase_order_1.order_line[0].product_id.id, self.product_computer.id
        )
        self.assertEqual(purchase_order_1.order_line[0].product_qty, 7)
        self.assertEqual(purchase_order_1.order_line[0].price_unit, 250)
        self.assertEqual(
            purchase_order_1.order_line[1].product_id.id, self.product_mouse.id
        )
        self.assertEqual(purchase_order_1.order_line[1].product_qty, 20)
        self.assertEqual(purchase_order_1.order_line[1].price_unit, 15)

        purchase_order_2 = self.get_purchase_order(request_purchase, 1)
        self.assertEqual(
            purchase_order_2.partner_id.id, self.partner_seller_2.id,
            "The second purchase order must been created with the good seller."
        )
        self.assertEqual(len(purchase_order_2.order_line), 1)
        self.assertEqual(
            purchase_order_2.order_line.product_id.id, self.product_computer.id
        )
        self.assertEqual(purchase_order_2.order_line.product_qty, 10)
        self.assertEqual(purchase_order_2.order_line.price_unit, 230)

    def test_purchase_05_convert_price_currency(self):
        """ Checks the price is correclty set when create a purchase order line
        for a product (currency conversion). """
        date_now = datetime.datetime.now()
        currency_a = self.env['res.currency'].create({
            'name': 'ZEN',
            'symbol': 'Z',
            'rounding': 0.01,
            'currency_unit_label': 'Zenny',
            'rate': 1,
        })
        # Create a partner to use as company owner.
        partner_company_owner = self.env['res.partner'].create({
            'name': 'Joe McKikou'
        })
        current_company = self.env.company
        # Create a new company using the currency_a and set it as current company.
        new_company = self.env['res.company'].create({
            'currency_id': currency_a.id,
            'name': 'Kikou Corp',
            'partner_id': partner_company_owner.id,
        })
        # Change company for the user.
        self.env.user.company_ids += new_company
        self.env.user.company_id = new_company
        currency_b = self.env['res.currency'].create({
            'name': 'RUP',
            'symbol': 'R',
            'rounding': 1,
            'currency_unit_label': 'Rupis',
            'rate_ids': [(0, 0, {
                'rate': 2.5,
                'company_id': new_company.id,
                'name': date_now,
            })],
        })
        # Set price vendor with currency_b.
        self.product_mouse.seller_ids = [(0, 0, {
            'partner_id': self.partner_seller_1.id,
            'min_qty': 1,
            'price': 5,
            'currency_id': currency_b.id,
        })]
        # Define a purchase approval category for the new company.
        approval_category_form = Form(self.env['approval.category'])
        approval_category_form.name = 'Product Request (Kikou Corp)'
        approval_category_form.approval_type = 'purchase'
        purchase_category_2 = approval_category_form.save()
        # Create a new user to use as approver for this company.
        user_approver_2 = self.env['res.users'].create({
            'login': 'big_cheese',
            'name': 'Clément Tall',
        })
        # Create new purchase approval request and create purchase order.
        request_form = self.create_request_form(
            approver=user_approver_2,
            category=purchase_category_2,
        )
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_mouse
            line.quantity = 1
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(user_approver_2).action_approve()
        request_purchase.action_create_purchase_orders()
        # Compare prices.
        purchase_order = self.get_purchase_order(request_purchase, 0)
        self.assertEqual(
            purchase_order.order_line[0].price_unit, 2, "Price must be adapted."
        )
        # Resets the company.
        self.env.user.company_id = current_company
        self.env.user.company_ids -= new_company

    def test_uom_01_create_purchase(self):
        """ Check the amount of product is correctly set, regarding the UoM of
        the approval request and the UoM on the purchase order line. """
        # Set the product UoM on 'fortnight'.
        self.product_earphone.uom_id = self.uom_fortnight
        # Create a request for 2 fortnights of the product.
        request_form = self.create_request_form(approver=self.user_approver)
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_earphone
            line.quantity = 2
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()

        request_product_line = request_purchase.product_line_ids[0]
        purchase_order = self.get_purchase_order(request_purchase, 0)
        self.assertEqual(
            request_product_line.product_uom_id.id, self.uom_fortnight.id
        )
        self.assertEqual(
            purchase_order.order_line[0].product_uom.id, self.uom_unit.id
        )
        self.assertEqual(
            purchase_order.order_line[0].product_qty, 30,
            "Must have 30 units (= 2 fortnights)."
        )

    def test_uom_02_create_purchase(self):
        """ Check the amount of product is correctly set, regarding the UoM of
        the approval request and the UoM on the purchase order line. """
        # Set the product purchase's UoM on 'fortnight'.
        self.product_earphone.uom_po_id = self.uom_fortnight
        # Create a request for 30 units of the product.
        request_form = self.create_request_form(approver=self.user_approver)
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_earphone
            line.quantity = 30
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()

        request_product_line = request_purchase.product_line_ids[0]
        purchase_order = self.get_purchase_order(request_purchase, 0)
        self.assertEqual(
            request_product_line.product_uom_id.id, self.uom_unit.id
        )
        self.assertEqual(
            purchase_order.order_line[0].product_uom.id, self.uom_fortnight.id
        )
        self.assertEqual(
            purchase_order.order_line[0].product_qty, 2,
            "Must have 2 fortnights (= 30 units)."
        )

    def test_uom_03_update_purchase_order_line(self):
        """ Check the approval request will use the right UoM for purchase, even
        if a compatible purchase order already exists with an order line using
        an another UoM. """
        # Create a purchase order for partner_seller_1 with an order line.
        purchase_order = self.create_purchase_order(lines=[{
            'product': self.product_earphone,
            'price': 250,
            'quantity': 7,
            'uom': self.uom_unit.id,
        }])
        # Set the product UoM on 'fortnight'.
        self.product_earphone.uom_po_id = self.uom_fortnight
        # Create a request for 2 fortnights of the product.
        request_form = self.create_request_form(approver=self.user_approver)
        with request_form.product_line_ids.new() as line:
            line.product_id = self.product_earphone
            line.quantity = 30
        request_purchase = request_form.save()
        request_purchase.action_confirm()
        request_purchase.with_user(self.user_approver).action_approve()
        request_purchase.action_create_purchase_orders()

        request_product_line = request_purchase.product_line_ids[0]
        purchase_order = self.get_purchase_order(request_purchase, 0)
        self.assertEqual(
            request_product_line.product_uom_id.id, self.uom_unit.id
        )
        self.assertEqual(len(purchase_order.order_line), 2)
        self.assertEqual(
            purchase_order.order_line[0].product_uom.id, self.uom_unit.id
        )
        self.assertEqual(
            purchase_order.order_line[1].product_uom.id, self.uom_fortnight.id
        )
        self.assertEqual(purchase_order.order_line[0].product_qty, 7)
        self.assertEqual(
            purchase_order.order_line[1].product_qty, 2,
            "Must have 2 fortnights (= 30 units)."
        )
