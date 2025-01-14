# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
from odoo import Command, fields
from odoo.exceptions import UserError


from datetime import timedelta
from freezegun import freeze_time
import pytz


@tagged('-at_install', 'post_install')
class TestPurchase(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

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
        # Also check that the other PO line's date planned is not modified.
        new_date_planned_2 = orig_date_planned - timedelta(hours=72)
        po_form = Form(po)
        with po_form.order_line.edit(1) as po_line:
            po_line.date_planned = new_date_planned_2
        po = po_form.save()
        self.assertAlmostEqual(po.order_line[1].date_planned, po.date_planned, delta=timedelta(seconds=10))
        self.assertAlmostEqual(po.order_line[0].date_planned, new_date_planned, delta=timedelta(seconds=10))

    def test_date_planned_2(self):
        """
        Check that the date_planned of the onchange is correctly applied:
        Create a PO, change its date_planned to tommorow and check that the date_planned of the lines are updated.
        Create a new line (this will update the date_planned of the PO but should not alter the other lines).
        """

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 10,
                'product_uom_id': self.product_a.uom_id.id,
                'price_unit': 1,
            })],
        })
        with Form(po) as po_form:
            po_form.date_planned = fields.Datetime.now() + timedelta(days=1)
        self.assertEqual(po.order_line.date_planned, po.date_planned)

        with Form(po) as po_form:
            with po_form.order_line.new() as new_line:
                new_line.product_id = self.product_b
                new_line.product_qty = 10
                new_line.price_unit = 200
        self.assertEqual(po.order_line[1].date_planned, po.date_planned)
        self.assertNotEqual(po.order_line[0].date_planned, po.date_planned)

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
        self.partner_a.with_company(self.company_data_2['company']).receipt_reminder_email = True
        self.partner_a.with_company(self.company_data_2['company']).reminder_date_before_receipt = 1
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
        self.assertEqual(po.company_id, self.company)
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
        # Ensure that the function get_localized_date_planned can accept a date in string format
        self.assertEqual(localized_date_planned, po.get_localized_date_planned(po.date_planned.strftime('%Y-%m-%d %H:%M:%S')))

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

    def test_with_different_uom(self):
        """ This test ensures that the unit price is correctly computed"""
        # Required for `product_uom_id` to be visibile in the view
        self.env.user.groups_id += self.env.ref('uom.group_uom')
        uom_units = self.env.ref('uom.product_uom_unit')
        uom_dozens = self.env.ref('uom.product_uom_dozen')
        uom_pairs = self.env['uom.uom'].create({
            'name': 'Pairs',
            'relative_factor': 2,
            'relative_uom_id': uom_units.id,
        })
        product_data = {
            'name': 'SuperProduct',
            'type': 'consu',
            'uom_id': uom_units.id,
            'seller_ids': [Command.create({
                'partner_id': self.partner_a.id,
                'product_uom_id': uom_pairs.id,
                'price': 200,
            })]
        }
        product_01 = self.env['product.product'].create(product_data)
        product_02 = self.env['product.product'].create(product_data)

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as po_line:
            po_line.product_id = product_01
        with po_form.order_line.new() as po_line:
            po_line.product_id = product_02
            po_line.product_uom_id = uom_dozens
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
        self.assertEqual(purchase_order_usd.amount_total_cc, purchase_order_usd.amount_total, "Company Total should be 0.14$")

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        po_form.currency_id = currency
        with po_form.order_line.new() as po_line:
            po_line.product_id = product
        purchase_order_coco = po_form.save()
        self.assertEqual(purchase_order_coco.order_line.price_unit, currency_rate.rate * product.standard_price, "Value shouldn't be rounded 🍫")
        self.assertEqual(purchase_order_coco.amount_total_cc, round(purchase_order_coco.amount_total / currency_rate.rate, 2), "Company Total should be 0.14$, since 1$ = 0.5🍫")

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
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            })],
        })

        self.assertEqual(order_b.order_line.price_unit, 10.0, 'The price unit should be 10.0')
        self.assertEqual(order_b.amount_total_cc, order_b.amount_total, 'Company Total should be 10.0$')

    def test_discount_and_price_update_on_quantity_change(self):
        """ Purchase order line price and discount should update accordingly based on quantity
        """
        product = self.env['product.product'].create({
            'name': 'Product',
            'standard_price': 12,
            'seller_ids': [
                Command.create({
                    'partner_id': self.partner_a.id,
                    'min_qty': 10,
                    'price': 10,
                    'discount': 10,
                }),
                Command.create({
                    'partner_id': self.partner_a.id,
                    'min_qty': 20,
                    'price': 10,
                    'discount': 15,
                })
            ]
        })

        purchase_order = self.env['purchase.order'].with_company(self.company_data['company']).create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
            })],
        })
        po_line = purchase_order.order_line

        po_line.product_qty = 10
        self.assertEqual(po_line.discount, 10, "first seller should be selected so discount should be 10")
        self.assertEqual(po_line.price_subtotal, 90, "0.1 discount applied price should be 90")

        po_line.product_qty = 22
        self.assertEqual(po_line.discount, 15, "second seller should be selected so discount should be 15")
        self.assertEqual(po_line.price_subtotal, 187, "0.15 discount applied price should be 187")

        po_line.product_qty = 2
        self.assertEqual(po_line.discount, 0, "no seller should be selected so discount should be 0")
        self.assertEqual(po_line.price_subtotal, 24, "No seller")

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
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
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
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
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

    def test_discount_po_line_vendorpricelist(self):
        """ Set a discount in VendorPriceList and check if that discount comes in po line and if vendor select
            a product which is not present in vendorPriceList then it should be created.
        """
        po = Form(self.env['purchase.order'])
        po.partner_id = self.partner_a
        with po.order_line.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
            po_line.discount = 20
        po = po.save()
        po.button_confirm()

        supplierinfo_id = self.env['product.supplierinfo'].search([
            ('partner_id', '=', self.partner_a.id),
            ('product_tmpl_id', '=', self.product_a.product_tmpl_id.id),
        ], limit=1)

        self.assertTrue(supplierinfo_id)
        self.assertEqual(supplierinfo_id.discount, 20)

        # checking the same discount
        self.env['product.supplierinfo'].create({
            'partner_id': self.partner_b.id,
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'min_qty': 1,
            'price': 100,
            'discount': 30,
        })

        po1 = Form(self.env['purchase.order'])
        po1.partner_id = self.partner_b
        with po1.order_line.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
        po1 = po1.save()

        self.assertEqual(po1.order_line[0].price_unit, 100)
        self.assertEqual(po1.order_line[0].discount, 30)

    def test_orderline_supplierinfo_description(self):
        supplierinfo_vals = {
            'partner_id': self.partner_a.id,
            'min_qty': 1,
            'product_id': self.product_a.id,
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
        }

        self.env["product.supplierinfo"].create([
            {
                **supplierinfo_vals,
                'price': 10,
                'product_name': 'Name 1',
                'product_code': 'Code 1',
            },
            {
                **supplierinfo_vals,
                'price': 20,
                'product_name': 'Name 2',
                'product_code': 'Code 2',
            },
            {
                'partner_id': self.partner_a.id,
                'min_qty': 1,
                'product_id': self.product_b.id,
                'product_tmpl_id': self.product_b.product_tmpl_id.id,
                'price': 5,
                'product_name': 'Name 3',
                'product_code': 'Code 3',
            }
        ])

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as line:
            line.product_id = self.product_a
            line.product_qty = 1
        po = po_form.save()
        self.assertEqual(po.order_line.name, '[Code 1] Name 1')

        with po_form.order_line.edit(0) as line:
            line.product_id = self.product_b
        po = po_form.save()
        self.assertEqual(po.order_line.name, '[Code 3] Name 3')

    def test_purchase_order_line_product_taxes_on_branch(self):
        """ Check taxes populated on PO lines from product on branch company.
            Taxes from the branch company should be taken with a fallback on parent company.
        """
        # create the following branch hierarchy:
        #     Parent company
        #         |----> Branch X
        #                   |----> Branch XX
        company = self.env.company
        branch_x = self.env['res.company'].create({
            'name': 'Branch X',
            'country_id': company.country_id.id,
            'parent_id': company.id,
        })
        branch_xx = self.env['res.company'].create({
            'name': 'Branch XX',
            'country_id': company.country_id.id,
            'parent_id': branch_x.id,
        })
        # create taxes for the parent company and its branches
        tax_groups = self.env['account.tax.group'].create([{
            'name': 'Tax Group',
            'company_id': company.id,
        }, {
            'name': 'Tax Group X',
            'company_id': branch_x.id,
        }, {
            'name': 'Tax Group XX',
            'company_id': branch_xx.id,
        }])
        tax_a = self.env['account.tax'].create({
            'name': 'Tax A',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_b = self.env['account.tax'].create({
            'name': 'Tax B',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 15,
            'tax_group_id': tax_groups[0].id,
            'company_id': company.id,
        })
        tax_x = self.env['account.tax'].create({
            'name': 'Tax X',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 20,
            'tax_group_id': tax_groups[1].id,
            'company_id': branch_x.id,
        })
        tax_xx = self.env['account.tax'].create({
            'name': 'Tax XX',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 25,
            'tax_group_id': tax_groups[2].id,
            'company_id': branch_xx.id,
        })
        # create several products with different taxes combination
        product_all_taxes = self.env['product.product'].create({
            'name': 'Product all taxes',
            'supplier_taxes_id': [Command.set((tax_a + tax_b + tax_x + tax_xx).ids)],
        })
        product_no_xx_tax = self.env['product.product'].create({
            'name': 'Product no tax from XX',
            'supplier_taxes_id': [Command.set((tax_a + tax_b + tax_x).ids)],
        })
        product_no_branch_tax = self.env['product.product'].create({
            'name': 'Product no tax from branch',
            'supplier_taxes_id': [Command.set((tax_a + tax_b).ids)],
        })
        product_no_tax = self.env['product.product'].create({
            'name': 'Product no tax',
            'supplier_taxes_id': [],
        })
        # create a PO from Branch XX
        po_form = Form(self.env['purchase.order'].with_company(branch_xx))
        po_form.partner_id = self.partner_a
        # add 4 PO lines with the different products:
        # - Product all taxes           => tax from Branch XX should be set
        # - Product no tax from XX      => tax from Branch X should be set
        # - Product no tax from branch  => 2 taxes from parent company should be set
        # - Product no tax              => no tax should be set
        with po_form.order_line.new() as line:
            line.product_id = product_all_taxes
        with po_form.order_line.new() as line:
            line.product_id = product_no_xx_tax
        with po_form.order_line.new() as line:
            line.product_id = product_no_branch_tax
        with po_form.order_line.new() as line:
            line.product_id = product_no_tax
        po = po_form.save()
        self.assertRecordValues(po.order_line, [
            {'product_id': product_all_taxes.id, 'taxes_id': tax_xx.ids},
            {'product_id': product_no_xx_tax.id, 'taxes_id': tax_x.ids},
            {'product_id': product_no_branch_tax.id, 'taxes_id': (tax_a + tax_b).ids},
            {'product_id': product_no_tax.id, 'taxes_id': []},
        ])

    @freeze_time('2024-07-08')
    def test_description_price__date_depending_on_vendor(self):
        """
        Test that the description and the price are updated accordingly when the vendor is changed.
        """
        self.product_a.seller_ids = [
            Command.create({
                'partner_id': self.partner_a.id,
                'min_qty': 1,
                'price': 5,
                'product_code': 'Vendor A',
                'delay': 5,
            }),
            Command.create({
                'partner_id': self.partner_b.id,
                'min_qty': 1,
                'price': 10,
                'product_code': 'Vendor B',
                'delay': 6,
            }),
        ]
        self.assertFalse(False)
        # Create PO and set vendor A
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 10
        po = po_form.save()
        self.assertEqual(po.order_line.price_unit, 5)
        self.assertEqual(po.order_line.name, '[Vendor A] product_a')
        self.assertEqual(po.order_line.product_qty, 10)
        self.assertEqual(po.order_line.date_planned, fields.Datetime.now() + timedelta(days=5))
        po.partner_id = self.partner_b
        self.assertEqual(po.order_line.price_unit, 10)
        self.assertEqual(po.order_line.name, '[Vendor B] product_a')
        self.assertEqual(po.order_line.product_qty, 10)
        self.assertEqual(po.order_line.date_planned, fields.Datetime.now() + timedelta(days=6))

    def test_merge_purchase_order(self):
        PurchaseOrder = self.env['purchase.order']
        user_1 = self.env['res.users'].search([])[0]
        user_2 = self.env['res.users'].search([])[1]
        payment_term_id_1 = self.env['account.payment.term'].search([])[0]
        payment_term_id_2 = self.env['account.payment.term'].search([])[1]
        incoterm_id_1 = self.env['account.incoterms'].search([])[0]
        incoterm_id_2 = self.env['account.incoterms'].search([])[1]

        po_1 = Form(PurchaseOrder)
        po_1.partner_id = self.partner_a
        po_1.partner_ref = "azure"
        po_1.origin = "s0003"
        po_1.user_id = user_1
        po_1.payment_term_id = payment_term_id_1
        with po_1.order_line.new() as po_line:
            po_line.product_id = self.product_a
            po_line.product_qty = 1
            po_line.price_unit = 100
        po_1 = po_1.save()
        po_1.incoterm_id = incoterm_id_1

        po_2 = Form(PurchaseOrder)
        po_2.partner_id = self.partner_a
        po_2.partner_ref = "wood corner"
        po_2.origin = "s0004"
        po_2.user_id = user_2
        po_2.payment_term_id = payment_term_id_2

        with po_2.order_line.new() as po_line_1:
            po_line_1.product_id = self.product_a
            po_line_1.product_qty = 5
            po_line_1.price_unit = 100
        with po_2.order_line.new() as po_line_2:
            po_line_2.product_id = self.product_b
            po_line_2.product_qty = 5
            po_line_2.price_unit = 500
        po_2 = po_2.save()
        po_2.incoterm_id = incoterm_id_2

        with self.assertRaises(UserError) as context:
            PurchaseOrder.browse([po_1.id]).action_merge()
        self.assertEqual(context.exception.args[0], "Please select at least two purchase orders with state RFQ and RFQ sent to merge.")

        selected_purchase_orders = po_1 | po_2
        selected_purchase_orders.action_merge()
        self.assertTrue(po_2.state == 'cancel')
        self.assertEqual(po_1.order_line[0].product_qty, 6)
        self.assertEqual(po_1.partner_ref, "azure, wood corner")
        self.assertEqual(po_1.origin, "s0003, s0004")
        self.assertEqual(po_1.user_id, user_1)
        self.assertEqual(po_1.payment_term_id, payment_term_id_1)
        self.assertEqual(po_1.incoterm_id, incoterm_id_1)
