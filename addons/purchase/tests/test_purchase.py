# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
from odoo import Command, fields


from datetime import timedelta
import pytz


@tagged('-at_install', 'post_install')
class TestPurchase(AccountTestInvoicingCommon):

    def test_date_planned(self):
        """Set a date planned on 2 PO lines. Check that the PO date_planned is the earliest PO line date
        planned. Change one of the dates so it is even earlier and check that the date_planned is set to
        this earlier date.
        """
        po = Form(self.env['purchase.order'])
        po.partner_id = self.partner_a
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
        po = po.save()

        # Check that the same date is planned on both PO lines.
        self.assertNotEqual(po.order_line[0].date_planned, False)
        self.assertAlmostEqual(po.order_line[0].date_planned, po.order_line[1].date_planned, delta=timedelta(seconds=10))
        self.assertAlmostEqual(po.order_line[0].date_planned, po.date_planned, delta=timedelta(seconds=10))

        orig_date_planned = po.order_line[0].date_planned

        # Set an earlier date planned on a PO line and check that the PO expected date matches it.
        new_date_planned = orig_date_planned - timedelta(hours=1)
        po.order_line[0].date_planned = new_date_planned
        self.assertAlmostEqual(po.order_line[0].date_planned, po.date_planned, delta=timedelta(seconds=10))

        # Set an even earlier date planned on the other PO line and check that the PO expected date matches it.
        new_date_planned = orig_date_planned - timedelta(hours=72)
        po.order_line[1].date_planned = new_date_planned
        self.assertAlmostEqual(po.order_line[1].date_planned, po.date_planned, delta=timedelta(seconds=10))

    def test_purchase_order_sequence(self):
        PurchaseOrder = self.env['purchase.order'].with_context(tracking_disable=True)
        company = self.env.user.company_id
        self.env['ir.sequence'].search([
            ('code', '=', 'purchase.order'),
        ]).write({
            'use_date_range': True, 'prefix': 'PO/%(range_year)s/',
        })
        vals = {
            'partner_id': self.partner_a.id,
            'company_id': company.id,
            'currency_id': company.currency_id.id,
            'date_order': '2019-01-01',
        }
        purchase_order = PurchaseOrder.create(vals.copy())
        self.assertTrue(purchase_order.name.startswith('PO/2019/'))
        vals['date_order'] = '2020-01-01'
        purchase_order = PurchaseOrder.create(vals.copy())
        self.assertTrue(purchase_order.name.startswith('PO/2020/'))
        # In EU/BXL tz, this is actually already 01/01/2020
        vals['date_order'] = '2019-12-31 23:30:00'
        purchase_order = PurchaseOrder.with_context(tz='Europe/Brussels').create(vals.copy())
        self.assertTrue(purchase_order.name.startswith('PO/2020/'))

    def test_reminder_1(self):
        """Set to send reminder tomorrow, check if a reminder can be send to the
        partner.
        """
        # set partner to send reminder in Company 2
        self.partner_a.with_company(self.env.companies[1]).receipt_reminder_email = True
        self.partner_a.with_company(self.env.companies[1]).reminder_date_before_receipt = 1
        # Create the PO in Company 1
        self.env.user.tz = 'Europe/Brussels'
        po = Form(self.env['purchase.order'])
        po.partner_id = self.partner_a
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
        # set to send reminder today
        date_planned = fields.Datetime.now().replace(hour=23, minute=0) + timedelta(days=2)
        po.date_planned = date_planned
        po = po.save()
        po.button_confirm()
        # Check that reminder is not set in Company 1 and the mail will not be sent
        self.assertEqual(po.company_id, self.env.companies[0])
        self.assertFalse(po.receipt_reminder_email)
        self.assertEqual(po.reminder_date_before_receipt, 1, "The default value should be taken from the company")
        old_messages = po.message_ids
        po._send_reminder_mail()
        messages_send = po.message_ids - old_messages
        self.assertFalse(messages_send)
        # Set to send reminder in Company 1
        self.partner_a.receipt_reminder_email = True
        self.partner_a.reminder_date_before_receipt = 2
        # Invalidate the cache to ensure that the computed fields are recomputed
        self.env.invalidate_all()
        self.assertTrue(po.receipt_reminder_email)
        self.assertEqual(po.reminder_date_before_receipt, 2)

        # check date_planned is correctly set
        self.assertEqual(po.date_planned, date_planned)
        po_tz = pytz.timezone(po.user_id.tz)
        localized_date_planned = po.date_planned.astimezone(po_tz)
        self.assertEqual(localized_date_planned, po.get_localized_date_planned())

        # check vendor is a message recipient
        self.assertTrue(po.partner_id in po.message_partner_ids)

        # check reminder send
        old_messages = po.message_ids
        po._send_reminder_mail()
        messages_send = po.message_ids - old_messages
        self.assertTrue(messages_send)
        self.assertTrue(po.partner_id in messages_send.mapped('partner_ids'))

        # check confirm button + date planned localized in message
        old_messages = po.message_ids
        po.confirm_reminder_mail()
        messages_send = po.message_ids - old_messages
        self.assertTrue(po.mail_reminder_confirmed)
        self.assertEqual(len(messages_send), 1)
        self.assertIn(str(localized_date_planned.date()), messages_send.body)

    def test_reminder_2(self):
        """Set to send reminder tomorrow, check if no reminder can be send.
        """
        po = Form(self.env['purchase.order'])
        po.partner_id = self.partner_a
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
        # set to send reminder tomorrow
        po.date_planned = fields.Datetime.now() + timedelta(days=2)
        po = po.save()
        self.partner_a.receipt_reminder_email = True
        self.partner_a.reminder_date_before_receipt = 1
        po.button_confirm()

        # check vendor is a message recipient
        self.assertTrue(po.partner_id in po.message_partner_ids)

        old_messages = po.message_ids
        po._send_reminder_mail()
        messages_send = po.message_ids - old_messages
        # check no reminder send
        self.assertFalse(messages_send)

    def test_update_date_planned(self):
        po = Form(self.env['purchase.order'])
        po.partner_id = self.partner_a
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
            po_line.date_planned = '2020-06-06 00:00:00'
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 10
            po_line.price_unit = 200
            po_line.date_planned = '2020-06-06 00:00:00'
        po = po.save()
        po.button_confirm()

        # update first line
        po._update_date_planned_for_lines([(po.order_line[0], fields.Datetime.today())])
        self.assertEqual(po.order_line[0].date_planned, fields.Datetime.today())
        activity = self.env['mail.activity'].search([
            ('summary', '=', 'Date Updated'),
            ('res_model_id', '=', 'purchase.order'),
            ('res_id', '=', po.id),
        ])
        self.assertTrue(activity)
        self.assertIn(
            '<p>partner_a modified receipt dates for the following products:</p>\n'
            '<p> - product_a from 2020-06-06 to %s</p>' % fields.Date.today(),
            activity.note,
        )

        # update second line
        po._update_date_planned_for_lines([(po.order_line[1], fields.Datetime.today())])
        self.assertEqual(po.order_line[1].date_planned, fields.Datetime.today())
        self.assertIn(
            '<p>partner_a modified receipt dates for the following products:</p>\n'
            '<p> - product_a from 2020-06-06 to %(today)s</p>\n'
            '<p> - product_b from 2020-06-06 to %(today)s</p>' % {'today': fields.Date.today()},
            activity.note,
        )

    def test_compute_packaging_00(self):
        """Create a PO and use packaging. Check we suggested suitable packaging
        according to the product_qty. Also check product_qty or product_packaging
        are correctly calculated when one of them changed.
        """
        # Required for `product_packaging_qty` to be visible in the view
        self.env.user.groups_id += self.env.ref('product.group_stock_packaging')
        packaging_single = self.env['product.packaging'].create({
            'name': "I'm a packaging",
            'product_id': self.product_a.id,
            'qty': 1.0,
        })
        packaging_dozen = self.env['product.packaging'].create({
            'name': "I'm also a packaging",
            'product_id': self.product_a.id,
            'qty': 12.0,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
        })
        po_form = Form(po)
        with po_form.order_line.new() as line:
            line.product_id = self.product_a
            line.product_qty = 1.0
        po_form.save()
        self.assertEqual(po.order_line.product_packaging_id, packaging_single)
        self.assertEqual(po.order_line.product_packaging_qty, 1.0)
        with po_form.order_line.edit(0) as line:
            line.product_packaging_qty = 2.0
        po_form.save()
        self.assertEqual(po.order_line.product_qty, 2.0)


        with po_form.order_line.edit(0) as line:
            line.product_qty = 24.0
        po_form.save()
        self.assertEqual(po.order_line.product_packaging_id, packaging_dozen)
        self.assertEqual(po.order_line.product_packaging_qty, 2.0)
        with po_form.order_line.edit(0) as line:
            line.product_packaging_qty = 1.0
        po_form.save()
        self.assertEqual(po.order_line.product_qty, 12)

        # Do the same test but without form, to check the `product_packaging_id` and `product_packaging_qty` are set
        # without manual call to compute
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'product_id': self.product_a.id, 'product_qty': 1.0}),
            ]
        })
        self.assertEqual(po.order_line.product_packaging_id, packaging_single)
        self.assertEqual(po.order_line.product_packaging_qty, 1.0)
        po.order_line.product_packaging_qty = 2.0
        self.assertEqual(po.order_line.product_qty, 2.0)

        po.order_line.product_qty = 24.0
        self.assertEqual(po.order_line.product_packaging_id, packaging_dozen)
        self.assertEqual(po.order_line.product_packaging_qty, 2.0)
        po.order_line.product_packaging_qty = 1.0
        self.assertEqual(po.order_line.product_qty, 12)

    def test_compute_packaging_01(self):
        """Create a PO and use packaging in a multicompany environment.
        Ensure any suggested packaging matches the PO's.
        """
        company1 = self.company_data['company']
        company2 = self.company_data_2['company']
        generic_single_pack = self.env['product.packaging'].create({
            'name': "single pack",
            'product_id': self.product_a.id,
            'qty': 1.0,
            'company_id': False,
        })
        company2_pack_of_10 = self.env['product.packaging'].create({
            'name': "pack of 10 by Company 2",
            'product_id': self.product_a.id,
            'qty': 10.0,
            'company_id': company2.id,
        })

        po1 = self.env['purchase.order'].with_company(company1).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'product_id': self.product_a.id, 'product_qty': 10.0}),
            ]
        })
        self.assertEqual(po1.order_line.product_packaging_id, generic_single_pack)
        self.assertEqual(po1.order_line.product_packaging_qty, 10.0)

        # verify that with the right company, we can get the other packaging
        po2 = self.env['purchase.order'].with_company(company2).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'product_id': self.product_a.id, 'product_qty': 10.0}),
            ]
        })
        self.assertEqual(po2.order_line.product_packaging_id, company2_pack_of_10)
        self.assertEqual(po2.order_line.product_packaging_qty, 1.0)

    def test_with_different_uom(self):
        """ This test ensures that the unit price is correctly computed"""
        # Required for `product_uom` to be visibile in the view
        self.env.user.groups_id += self.env.ref('uom.group_uom')
        uom_units = self.env.ref('uom.product_uom_unit')
        uom_dozens = self.env.ref('uom.product_uom_dozen')
        uom_pairs = self.env['uom.uom'].create({
            'name': 'Pairs',
            'category_id': uom_units.category_id.id,
            'uom_type': 'bigger',
            'factor_inv': 2,
            'rounding': 1,
        })
        product_data = {
            'name': 'SuperProduct',
            'type': 'consu',
            'uom_id': uom_units.id,
            'uom_po_id': uom_pairs.id,
            'standard_price': 100
        }
        product_01 = self.env['product.product'].create(product_data)
        product_02 = self.env['product.product'].create(product_data)

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as po_line:
            po_line.product_id = product_01
        with po_form.order_line.new() as po_line:
            po_line.product_id = product_02
            po_line.product_uom = uom_dozens
        po = po_form.save()

        self.assertEqual(po.order_line[0].price_unit, 200)
        self.assertEqual(po.order_line[1].price_unit, 1200)

    def test_on_change_quantity_description(self):
        """
        When a user changes the quantity of a product in a purchase order it
        should not change the description if the descritpion was changed by
        the user before
        """
        self.env.user.write({'company_id': self.company_data['company'].id})

        po = Form(self.env['purchase.order'])
        po.partner_id = self.partner_a
        with po.order_line.new() as pol:
            pol.product_id = self.product_a
            pol.product_qty = 1

        pol.name = "New custom description"
        pol.product_qty += 1
        self.assertEqual(pol.name, "New custom description")

    def test_purchase_multicurrency(self):
        """
        Purchase order lines should keep unit price precision of products
        Also the products having prices in different currencies should be
        correctly handled when creating a purchase order i-e product having a price of 100 usd
        and when purchasing in EUR company the correct conversion should be applied
        """
        self.env['decimal.precision'].search([
            ('name', '=', 'Product Price'),
        ]).digits = 5
        product = self.env['product.product'].create({
            'name': 'product_test',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 10.0,
            'standard_price': 0.12345,
        })
        currency = self.env['res.currency'].create({
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'rounding': 0.001,
            'position': 'after',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        })
        currency_rate = self.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': 2,
            'currency_id': currency.id,
            'company_id': self.env.company.id,
        })

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as po_line:
            po_line.product_id = product
        purchase_order_usd = po_form.save()
        self.assertEqual(purchase_order_usd.order_line.price_unit, product.standard_price, "Value shouldn't be rounded $")

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        po_form.currency_id = currency
        with po_form.order_line.new() as po_line:
            po_line.product_id = product
        purchase_order_coco = po_form.save()
        self.assertEqual(purchase_order_coco.order_line.price_unit, currency_rate.rate * product.standard_price, "Value shouldn't be rounded 🍫")

        #check if the correct currency is set on the purchase order by comparing the expected price and actual price

        company_a = self.company_data['company']
        company_b = self.company_data_2['company']

        company_b.currency_id = currency

        self.env['res.currency.rate'].create({
            'name': '2023-01-01',
            'rate': 2,
            'currency_id': currency.id,
            'company_id': company_b.id,
        })

        product_b = self.env['product.product'].with_company(company_a).create({
            'name': 'product_2',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'standard_price': 0.0,
        })

        self.assertEqual(product_b.cost_currency_id, company_a.currency_id, 'The cost currency should be the one set on'
                                                                            ' the company')

        product_b = product_b.with_company(company_b)

        self.assertEqual(product_b.cost_currency_id, currency, 'The cost currency should be the one set on the company,'
                                                               ' as the product is now opened in another company')

        product_b.supplier_taxes_id = False
        product_b.update({'standard_price': 10.0})

        #create a purchase order with the product from company B
        order_b = self.env['purchase.order'].with_company(company_b).create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': product_b.id,
                'product_qty': 1,
                'product_uom': self.env.ref('uom.product_uom_unit').id,
            })],
        })

        self.assertEqual(order_b.order_line.price_unit, 10.0, 'The price unit should be 10.0')

    def test_purchase_not_creating_useless_product_vendor(self):
        """ This test ensures that the product vendor is not created when the
        product is not set on the purchase order line.
        """

        #create a contact of type contact
        contact = self.env['res.partner'].create({
            'name': 'Contact',
            'type': 'contact',
        })

        #create a contact of type Delivery Address lnked to the contact
        delivery_address = self.env['res.partner'].create({
            'name': 'Delivery Address',
            'type': 'delivery',
            'parent_id': contact.id,
        })

        #create a product that use the delivery address as vendor
        product = self.env['product.product'].create({
            'name': 'Product A',
            'seller_ids': [(0, 0, {
                'partner_id': delivery_address.id,
                'min_qty': 1.0,
                'price': 1.0,
            })]
        })

        #create a purchase order with the delivery address as partner
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = delivery_address
        with po_form.order_line.new() as po_line:
            po_line.product_id = product
            po_line.product_qty = 1.0
        po = po_form.save()
        po.button_confirm()

        self.assertEqual(po.order_line.product_id.seller_ids.mapped('partner_id'), delivery_address)

    def test_supplier_list_in_product_with_multicompany(self):
        """
        Check that a different supplier list can be added to a product for each company.
        """
        company_a = self.company_data['company']
        company_b = self.company_data_2['company']
        product = self.env['product.product'].create({
            'name': 'product_test',
        })
        # create a purchase order in the company A
        self.env['purchase.order'].with_company(company_a).create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_qty': 1,
                'product_uom': self.env.ref('uom.product_uom_unit').id,
                'price_unit': 1,
            })],
        }).button_confirm()

        self.assertEqual(product.seller_ids[0].partner_id, self.partner_a)
        self.assertEqual(product.seller_ids[0].company_id, company_a)

        # switch to the company B
        self.env['purchase.order'].with_company(company_b).create({
            'partner_id': self.partner_b.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_qty': 1,
                'product_uom': self.env.ref('uom.product_uom_unit').id,
                'price_unit': 2,
            })],
        }).button_confirm()
        product = product.with_company(company_b)
        self.assertEqual(product.seller_ids[0].partner_id, self.partner_b)
        self.assertEqual(product.seller_ids[0].company_id, company_b)

        # Switch to the company A and check that the vendor list is still the same
        product = product.with_company(company_a)
        self.assertEqual(product.seller_ids[0].partner_id, self.partner_a)
        self.assertEqual(product.seller_ids[0].company_id, company_a)

        product._invalidate_cache()
        self.assertEqual(product.seller_ids[0].partner_id, self.partner_a)
        self.assertEqual(product.seller_ids[0].company_id, company_a)
