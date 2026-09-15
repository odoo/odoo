# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo import fields, Command
from odoo.tests import Form, tagged
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from .common import PurchaseTestCommon


@tagged('post_install', '-at_install')
class TestStockValuationWithCOA(PurchaseTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product1, cls.product2 = cls.env['product.product'].create([{
            'name': 'product1',
            'is_storable': True,
            'categ_id': cls.category_fifo_auto.id,
        }, {
            'name': 'product2',
            'is_storable': True,
            'categ_id': cls.category_fifo_auto.id,
        }])

    def test_anglosaxon_valuation_price_total_diff_discount(self):
        """
        PO:  price unit: 110
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 110.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-order.id)
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100.0
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # The bill revalues the FIFO receipt move down to its net billed price (110 - 20).
        self.assertEqual(receipt.move_ids.value, 90.0)
        self.assertEqual(self.product1.total_value, 90.0)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 90.0)

    def test_anglosaxon_valuation_discount(self):
        """
        PO:  price unit: 100
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 100.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-order.id)
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.tax_ids.clear()
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # The 10% discount revalues the FIFO receipt move from 100 down to 90.
        self.assertEqual(receipt.move_ids.value, 90.0)
        self.assertEqual(self.product1.total_value, 90.0)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 90.0)

    def test_anglosaxon_valuation_price_unit_diff_discount(self):
        """
        PO:  price unit:  90
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 90.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-order.id)
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100.0
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # PO 90 then bill net 90 (100 - 10%): the receipt value is unchanged at 90.
        self.assertEqual(receipt.move_ids.value, 90.0)
        self.assertEqual(self.product1.total_value, 90.0)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 90.0)

    def test_pdiff_and_aml_labels(self):
        """
        When posting the bill, if an AML has a pdiff, it should not change any
        label of the bill
        """
        self._use_price_diff()
        self.product1.type = 'consu'
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product2
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.move_line_ids.quantity = 1
        receipt01.button_validate()

        action = po.action_create_invoice()
        bill = self.env["account.move"].browse(action["res_id"])
        bill.invoice_date = fields.Date.today()
        label01, label02 = bill.invoice_line_ids.mapped('name')
        self.assertTrue(label01)
        self.assertTrue(label02)

        bill.invoice_line_ids.price_unit = 11.0
        bill.action_post()
        self.assertEqual(bill.invoice_line_ids.mapped('name'), [label01, label02])

    def test_pdiff_lot_valuation(self):
        """
        A serial-tracked product valued per lot is received across several
        lots, then billed above the purchase-order price; the higher price
        re-values each lot and the product's on-hand inventory value.
        """
        product = self.env['product.product'].create({
            'name': 'product_lot',
            'is_storable': True,
            'tracking': 'serial',
            'categ_id': self.category_avco_auto.id,
            'lot_valuated': True,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [
                Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': 3.0,
                    'product_uom_id': product.uom_id.id,
                    'price_unit': 100.0,
                    'tax_ids': False,
                }),
            ],
        })
        po.button_confirm()

        receipt = po.picking_ids
        for i, line in enumerate(receipt.move_ids.move_line_ids, start=1):
            line.write({'lot_name': 'lot_%s' % i, 'quantity': 1})
        receipt.move_ids.picked = True
        receipt.button_validate()

        lots = receipt.move_line_ids.lot_id
        self.assertEqual(receipt.state, 'done')
        self.assertEqual(lots.mapped('standard_price'), [100.0, 100.0, 100.0])
        self.assertEqual(product.total_value, 300.0)

        action = po.action_create_invoice()
        bill = self.env['account.move'].browse(action['res_id'])
        bill.invoice_date = fields.Date.today()
        bill.invoice_line_ids.price_unit = 150.0
        bill.action_post()

        # The bill above the purchase price re-values each lot and the total.
        self.assertEqual(lots.mapped('standard_price'), [150.0, 150.0, 150.0])
        self.assertRecordValues(product, [{
            'standard_price': 150.0,
            'total_value': 450.0,
        }])
        self.assertEqual(receipt.move_ids.value, 450.0)

    def test_purchase_with_backorders_and_return_and_price_changes(self):
        """
        A purchase order is received in several partial deliveries, each billed
        at a different price. Correcting the price on a bill revalues only the
        goods it covers, and once several bills exist the received goods are
        valued at their running average cost. Returning part of a delivery, so
        that more units end up billed than are on hand, must not make a later
        delivery inherit a billed price: goods that have not been billed yet stay
        valued at the purchase-order price.
        """
        self.product1.categ_id = self.category_avco_auto
        self.product1.purchase_method = 'receive'

        po = self._create_purchase(self.product1, quantity=100, price_unit=10.0)

        receipt01 = self._receive(po, quantity=30)
        self.assertEqual(receipt01.value, 300.0)
        self._create_bill(purchase_order=po, price_unit=12)
        # The bill revalues the goods it covers (30 at 12).
        self.assertEqual(receipt01.value, 360.0)

        receipt02 = self._receive(po, quantity=30)
        # The first bill only covers the first delivery, so the second delivery
        # is still valued at the purchase-order price.
        self.assertEqual(receipt02.value, 300.0)
        self._create_bill(purchase_order=po, price_unit=13)
        # With both deliveries billed, the received goods share the running
        # average cost of 12.5 (30 at 12 and 30 at 13).
        self.assertEqual(receipt01.value, 375.0)
        self.assertEqual(receipt02.value, 375.0)

        # Returning part of the second delivery leaves more units billed than on hand.
        self._make_return(receipt02, 10)

        receipt03 = self._receive(po, quantity=30)
        # The third delivery is not billed, so it keeps the purchase-order price
        # instead of inheriting a billed price.
        self.assertEqual(receipt03.value, 300.0)
        self.assertRecordValues(self.product1, [{
            'total_value': 925.0,
            'standard_price': 11.5625,
        }])

    def test_invoice_on_ordered_qty_with_backorder_and_different_currency_automated(self):
        """Create a PO with currency different from the company currency. Set the
        product to be invoiced on ordered quantities. Receive partially the products
        and create a backorder. Create an invoice for the ordered quantity. Then
        receive the backorder. Check if the valuation layer is correctly created.
        """
        usd_currency = self.env.ref('base.USD')
        self.env.company.currency_id = usd_currency.id
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.purchase_method = 'purchase'

        price_unit_EUR = 100
        price_unit_USD = self.env.ref('base.EUR')._convert(price_unit_EUR, usd_currency, self.env.company, fields.Date.today(), round=False)
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'currency_id': self.env.ref('base.EUR').id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 12.0,
                    'product_uom_id': self.product1.uom_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po.button_confirm()
        picking = po.picking_ids[0]
        move = picking.move_ids[0]
        move.quantity = 10
        move.picked = True
        res_dict = picking.button_validate()
        self.assertEqual(res_dict['res_model'], 'stock.backorder.confirmation')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id')).with_context(res_dict['context'])
        wizard.process()
        self.assertAlmostEqual(move.value, 10 * price_unit_USD, places=2)

        po.action_create_invoice()

        picking2 = po.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_ids[0]
        move2.quantity = 2
        move2.picked = True
        picking2.button_validate()
        self.assertAlmostEqual(move2.value, 2 * price_unit_USD, places=2)

    def test_invoice_on_ordered_qty_with_backorder_and_different_currency_manual(self):
        """Same test as test_invoice_on_ordered_qty_with_backorder_and_different_currency_automated with periodic valuation
        Ensure that periodic valuation (no accounting entry at receipt) does not generate an Exception
        """
        usd_currency = self.env.ref('base.USD')
        self.env.company.currency_id = usd_currency.id
        self.product1.categ_id = self.category_fifo
        self.product1.purchase_method = 'purchase'

        price_unit_EUR = 100
        price_unit_USD = self.env.ref('base.EUR')._convert(price_unit_EUR, usd_currency, self.env.company, fields.Date.today(), round=False)
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'currency_id': self.env.ref('base.EUR').id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 12.0,
                    'product_uom_id': self.product1.uom_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po.button_confirm()
        picking = po.picking_ids[0]
        move = picking.move_ids[0]
        move.quantity = 10
        move.picked = True
        res_dict = picking.button_validate()
        self.assertEqual(res_dict['res_model'], 'stock.backorder.confirmation')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id')).with_context(res_dict['context'])
        wizard.process()
        self.assertAlmostEqual(move.value, 10 * price_unit_USD, places=2)

        po.action_create_invoice()

        picking2 = po.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_ids[0]
        move2.quantity = 2
        move2.picked = True
        picking2.button_validate()
        self.assertAlmostEqual(move2.value, 2 * price_unit_USD, places=2)

    def test_bill_with_zero_qty(self):
        """
        FIFO standard
        Receive two different product
        Bill them, but:
            Set the quantity of the first AML to zero
        Bill again the PO (for the "canceled" line in the first bill)
        """
        product1 = self.product1
        product2 = self.product2

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        with po_form.order_line.new() as po_line:
            po_line.product_id = product2
            po_line.product_qty = 1
            po_line.price_unit = 20.0
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 1
        receipt.button_validate()

        action = po.action_create_invoice()
        bill01 = self.env["account.move"].browse(action["res_id"])
        bill01.invoice_date = fields.Date.today()
        bill01.invoice_line_ids.filtered(lambda l: l.product_id == product2).quantity = 0
        bill01.action_post()

        self.assertEqual(bill01.state, 'posted')
        self.assertRecordValues(po.order_line, [
            {'product_id': product1.id, 'qty_invoiced': 1.0},
            {'product_id': product2.id, 'qty_invoiced': 0.0},
        ])

        bill02 = self._create_bill(purchase_order=po)
        self.assertEqual(bill02.state, 'posted')
        self.assertRecordValues(po.order_line, [
            {'product_id': product1.id, 'qty_invoiced': 1.0},
            {'product_id': product2.id, 'qty_invoiced': 1.0},
        ])

        self.assertRecordValues(receipt.move_ids, [
            {'product_id': product1.id, 'value': 10.0},
            {'product_id': product2.id, 'value': 20.0},
        ])

    def _test_fifo_and_returns_common(self):
        """
        FIFO auto
        Receive & Bill 1 @ 10
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 1
        receipt.button_validate()

        self._create_bill(purchase_order=po)

    def test_fifo_return_and_receive_all_on_backorder(self):
        """
        FIFO auto
        Receive & Bill 1 @ 10
        PO 4 @ 25
        Receive one with backorder
        Return it
        Receive 4 thanks to the backorder
        Bill them
        """
        self._test_fifo_and_returns_common()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 4
            po_line.price_unit = 25.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        action = receipt01.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action['context'])).save()
        backorder_wizard.process()

        self._make_return(receipt01.move_ids, receipt01.move_ids.quantity)

        receipt02 = receipt01.backorder_ids
        receipt02.move_ids.quantity = 4
        receipt02.button_validate()

        self._create_bill(purchase_order=po)

        self.assertRecordValues(self.product1, [{
            'qty_available': 5,
            'total_value': 125.0,
            'standard_price': 25.0,
        }])
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 110.0)

    def test_fifo_return_twice_and_bill(self):
        """
        FIFO auto
        Receive & Bill 1 @ 10
        Receive 1 @ 25
        Return
        Receive it again
        Bill
        """
        self._test_fifo_and_returns_common()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 25.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        receipt01.button_validate()

        receipt01_return = self._make_return(receipt01.move_ids, receipt01.move_ids.quantity)
        self._make_return(receipt01_return, receipt01_return.quantity)
        self._create_bill(purchase_order=po)

        # The return of the return brings the @25 unit back on hand next to the @10 one.
        self.assertRecordValues(self.product1, [{
            'qty_available': 2,
            'total_value': 50.0,
            'standard_price': 25.0,
        }])
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 35.0)

    def test_fifo_bill_return_refund(self):
        """
        FIFO auto
        Receive & Bill 1 @ 10
        Receive 1 @ 25
        Bill
        Return
        Refund
        """
        self._test_fifo_and_returns_common()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 25.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        receipt01.button_validate()

        self._create_bill(purchase_order=po)
        self._make_return(receipt01.move_ids, receipt01.move_ids.quantity)
        self._create_bill(purchase_order=po)  # Refund

        # The FIFO return consumes the oldest layer (the @10 one), leaving the @25 unit on hand.
        self.assertRecordValues(self.product1, [{
            'qty_available': 1,
            'total_value': 25.0,
            'standard_price': 25.0,
        }])
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 10.0)

    def test_incoming_with_negative_qty(self):
        """
                FIFO/AVCO Auto
                Purchase one Product with negative qty
                Conform PO,
                It will create outgoing shipment
                        this transfer is neither returned nor received but it will be a delivery(outgoing).
                """
        product1 = self.product1
        shipping_partner = self.env["res.partner"].create({
            'name': "Shipping Partner",
            'street': "234 W 18th Ave",
            'city': "Columbus",
            'state_id': self.env.ref("base.state_us_30").id,  # Ohio
            'country_id': self.env.ref("base.us").id,
            'zip': "43210",
        })
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor
        with po_form.order_line.new() as po_line:
            po_line.product_id = product1
            po_line.product_qty = -2
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()
        delivery = po.picking_ids
        # it is negative qty transfer so Odoo will create delivery instead of receipt.
        delivery.partner_id = shipping_partner
        move_line_vals = delivery.move_ids._prepare_move_line_vals()
        move_line = self.env['stock.move.line'].create(move_line_vals)
        move_line.quantity = 2.
        delivery.button_validate()
        self.assertEqual(delivery.state, 'done')

    def test_return_a_return_avco_prod_with_exchange_diff(self):
        """ When there is some return of a return, we expect `_generate_price_difference_vals` to
        assume any pdiff existing in the relevant transfers has already been
        compensated for. This should remain true in the case where the underlying purchase order
        has some currency exchange diff.
        """
        self.product1.categ_id.property_cost_method = 'average'
        avco_prod = self.product1
        (self.env.ref('base.EUR') + self.env.ref('base.CHF')).active = True
        euro_id = self.env.ref('base.EUR').id
        franc_id = self.env.ref('base.CHF').id
        self.env['res.currency.rate'].create([
            {'currency_id': euro_id, 'rate': 0.95},
            {'currency_id': franc_id, 'rate': 0.8},
        ])
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'currency_id': euro_id,
            'order_line': [Command.create({
                'product_id': avco_prod.id,
                'product_uom_qty': 5,
                'price_unit': 10,
            })],
        })
        purchase_order.button_confirm()
        receipt1 = purchase_order.picking_ids
        receipt1.button_validate()

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.owner.id,
            'currency_id': franc_id,
            'order_line': [Command.create({
                'product_id': avco_prod.id,
                'product_uom_qty': 5,
            })],
        })
        purchase_order.button_confirm()
        receipt2 = purchase_order.picking_ids
        receipt2.button_validate()

        receipt2_return1 = self._make_return(receipt2.move_ids, receipt2.move_ids.quantity)
        # return the initial return
        self._make_return(receipt2_return1, receipt2_return1.quantity)
        pre_bill_cost = avco_prod.standard_price
        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        self.assertEqual(avco_prod.standard_price, pre_bill_cost)

    def test_manual_non_standard_cost_bill_post(self):
        """ With manual valuation (+ continental accounting), receiving some product with a
        non-standard cost method, consuming the available qty, and then invoicing that product at
        different `price_unit` than the receipt should not create pdiff AccountMoveLines.
        """
        self.env.company.anglo_saxon_accounting = False
        self.product1.categ_id = self.category_avco
        product = self.product1
        tax = self.company.account_purchase_tax_id
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': 10,
                'price_unit': 100,
                'tax_ids': [Command.set(tax.ids)],
            })],
        })
        purchase_order.button_confirm()
        purchase_order.picking_ids.button_validate()
        with Form(self.env['stock.scrap']) as scrap_form:
            scrap_form.product_id = product
            scrap_form.scrap_qty = 10
            scrap = scrap_form.save()
        scrap.action_validate()
        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_line_ids.price_unit = 120
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        tax_account = tax.invoice_repartition_line_ids.account_id
        self.assertRecordValues(
            bill.line_ids,
            [
                {'account_id': self.account_expense.id, 'debit': 1200.0, 'credit': 0.0},
                {'account_id': tax_account.id,          'debit': 180.0,  'credit': 0.0},
                {'account_id': self.account_payable.id, 'debit': 0.0,    'credit': 1380.0},
            ]
        )

    def test_100_percent_discount(self):
        product = self.product1
        product.categ_id = self.category_avco_auto
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': 2,
                'discount': 100,
            })],
        })
        purchase_order.button_confirm()
        receipt = purchase_order.picking_ids
        receipt.button_validate()
        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        move = receipt.move_ids
        self.assertEqual(move.value, 0)
        self.assertEqual(move.quantity, 2)

    def test_standard_valuation_return_credit_note(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id = self.category_standard_auto
        # Set the cost in the past so its manual valuation predates the moves.
        with freeze_time('2020-01-01'):
            self.product1.standard_price = 100

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line': [
                Command.create({
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po.button_confirm()
        receipt_po = po.picking_ids[0]
        receipt_po.button_validate()

        self._create_bill(purchase_order=po)  # Bill
        self._make_return(receipt_po.move_ids, receipt_po.move_ids.quantity)
        self._create_bill(purchase_order=po)  # Refund

        # Everything received has been returned: no quantity nor value remains on hand.
        self.assertRecordValues(self.product1, [{
            'qty_available': 0,
            'total_value': 0.0,
        }])
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 0.0)

    def test_move_value_invoice_manual_rate(self):
        """Check that if a rate is manually set on a bill, this rate
        is used for the valuation of the move.
        """
        grp_currencies = self.env.ref('base.group_multi_currency')
        self.env.user.write({'group_ids': [(4, grp_currencies.id)]})
        product = self.env['product.product'].create({
            'name': 'product_a',
            'standard_price': 100.0,
        })
        partner = self.env['res.partner'].create({'name': 'testpartner'})
        eur_currency = self.env.ref('base.EUR')
        eur_currency.active = True
        eur_currency.write({
            'rate_ids': [Command.create({
                'rate': 2,
            })]
        })
        product.product_tmpl_id.categ_id.property_cost_method = 'average'
        product.product_tmpl_id.categ_id.property_valuation = 'real_time'

        po = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'currency_id': eur_currency.id,
            'order_line': [
                Command.create({
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': 1.0,
                    'price_unit': 100.0,
                }),
            ],
        })
        po.button_confirm()
        receipt_po = po.picking_ids[0]
        receipt_po.button_validate()
        self.assertEqual(po.picking_ids.move_ids.value, 50)

        action = po.action_create_invoice()
        bill = self.env["account.move"].browse(action["res_id"])
        bill.invoice_date = fields.Date.today()
        with Form(bill) as move_form:
            move_form.invoice_currency_rate = 4
        bill.action_post()
        self.assertEqual(po.picking_ids.move_ids.value, 25)

    def test_price_diff_with_partial_bills_and_delivered_qties(self):
        """
        Part of a purchase order is delivered to a customer before the vendor
        bill arrives above the purchase-order price. Billing above the order
        price revalues the whole received quantity to the billed price, so the
        units still on hand are worth the billed price.
        """
        product = self.product1  # fifo, real_time
        po = self._create_purchase(product, quantity=10, price_unit=50.0)
        receipt = self._receive(po)
        self.assertEqual(receipt.value, 500.0)

        # Deliver half of the goods to a customer before any bill.
        self._make_out_move(product, 5)
        self.assertEqual(product.total_value, 250.0)

        # Bill the order above its price, in two parts.
        self._create_bill(purchase_order=po, quantity=5, price_unit=60.0)
        self.assertEqual(product.total_value, 275.0)
        self._create_bill(purchase_order=po, quantity=5, price_unit=60.0)

        # The whole receipt is revalued to the billed price; the 5 units left
        # on hand are worth the billed price.
        self.assertEqual(receipt.value, 600.0)
        self.assertRecordValues(product, [{
            'qty_available': 5.0,
            'total_value': 300.0,
            'standard_price': 60.0,
        }])
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 600.0)

    def test_pdiff_and_credit_notes(self):
        """
        Goods received in several deliveries are billed across several vendor
        bills at different prices, some of which are then partially refunded.
        Each bill and refund revalues the goods on hand, so the inventory value
        tracks the net billed price of the received quantity.
        """
        product = self.product1  # fifo, real_time
        po = self._create_purchase(product, quantity=12, price_unit=10.0)
        self._receive(po, quantity=4)
        self._receive(po, quantity=3)
        self._receive(po, quantity=5)
        self.assertEqual(product.total_value, 120.0)

        bill01 = self._create_bill(purchase_order=po, quantity=3, price_unit=12.0)
        bill02 = self._create_bill(purchase_order=po, quantity=2, price_unit=11.0)
        self._create_bill(purchase_order=po, quantity=1, price_unit=15.0)
        bill04 = self._create_bill(purchase_order=po, quantity=4, price_unit=9.0)
        bill05 = self._create_bill(purchase_order=po, quantity=2, price_unit=10.0)
        self.assertEqual(product.total_value, 129.0)

        self._refund(bill01, 1.0)
        self._refund(bill02)
        self._refund(bill04, 2.0)
        self._refund(bill05, 1.0)
        self.assertEqual(product.total_value, 127.0)

        self._create_bill(purchase_order=po, price_unit=18.0)

        # All 12 units are still on hand, valued at their net billed price.
        self.assertRecordValues(product, [{
            'qty_available': 12.0,
            'total_value': 175.0,
        }])
        self.assertAlmostEqual(product.standard_price, 175 / 12)
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 175.0)

    def test_pdiff_with_credit_notes_and_delivered_qties(self):
        """
        Goods received in one delivery are billed above the purchase-order
        price and partly delivered to a customer, then the bill is fully
        refunded. Fully refunding a price-difference bill returns the goods
        still on hand to the order price, even though part of the receipt was
        already delivered. The cycle is repeated, and a final bill at the order
        price leaves the inventory valued at that price.
        """
        product = self.product1  # fifo, real_time
        po = self._create_purchase(product, quantity=10, price_unit=10.0)
        self._receive(po, quantity=10)
        self.assertEqual(product.total_value, 100.0)

        bill01 = self._create_bill(purchase_order=po, price_unit=12.0)
        # Billed above the order price: the goods on hand are revalued up.
        self.assertRecordValues(product, [{
            'total_value': 120.0,
            'standard_price': 12.0,
        }])

        self._make_out_move(product, 3)
        self.assertRecordValues(product, [{
            'qty_available': 7.0,
            'total_value': 84.0,
        }])

        self._refund(bill01)
        # Fully refunded: the units still on hand revert to the order price.
        self.assertRecordValues(product, [{
            'total_value': 70.0,
            'standard_price': 10.0,
        }])

        bill02 = self._create_bill(purchase_order=po, price_unit=9.0)
        self.assertRecordValues(product, [{
            'total_value': 63.0,
            'standard_price': 9.0,
        }])

        self._make_out_move(product, 1)
        self.assertEqual(product.qty_available, 6.0)

        self._refund(bill02)
        self.assertRecordValues(product, [{
            'total_value': 60.0,
            'standard_price': 10.0,
        }])

        self._create_bill(purchase_order=po, price_unit=10.0)
        # Billed at the order price: the 6 units on hand stay at that price.
        self.assertRecordValues(product, [{
            'qty_available': 6.0,
            'total_value': 60.0,
            'standard_price': 10.0,
        }])

    def test_pdiff_with_returns_and_credit_notes(self):
        """
        Goods received in one delivery are returned and then received again
        before being billed above the purchase-order price. Billing above the
        order price only revalues the goods still tracked to that receipt; the
        goods that were returned and received again keep the order price.
        Further returns and credit notes then unwind the value as the goods
        leave stock.
        """
        product = self.product1  # fifo, real_time
        po = self._create_purchase(product, quantity=10, price_unit=10.0)
        receipt = self._receive(po, quantity=10)
        self.assertEqual(product.total_value, 100.0)

        return01 = self._make_return(receipt, 3)
        self.assertRecordValues(product, [{
            'qty_available': 7.0,
            'total_value': 70.0,
        }])

        self._make_return(return01, 3)
        self.assertRecordValues(product, [{
            'qty_available': 10.0,
            'total_value': 100.0,
        }])

        bill = self._create_bill(purchase_order=po, quantity=10, price_unit=12.0)
        # Only the 7 units still tracked to the receipt are revalued to the
        # billed price; the 3 returned-and-received-again units keep the order price.
        self.assertEqual(product.total_value, 114.0)
        self.assertAlmostEqual(product.standard_price, 11.4)

        self._make_return(receipt, 1)
        self.assertRecordValues(product, [{
            'qty_available': 9.0,
            'total_value': 102.0,
        }])

        refund = self._create_bill(purchase_order=po, price_unit=12.0)
        self.assertEqual(refund.move_type, 'in_refund')
        self.assertAlmostEqual(product.total_value, 100.8)

        self._make_return(receipt, 5)
        self.assertEqual(product.qty_available, 4.0)
        self.assertAlmostEqual(product.total_value, 41.8)

        self._refund(bill, quantity=5)
        # The 4 units left on hand keep the value they were billed at.
        self.assertEqual(product.qty_available, 4.0)
        self.assertAlmostEqual(product.total_value, 40.8)
        self.assertAlmostEqual(product.standard_price, 10.2)

    def test_pdiff_multi_curr_and_rates(self):
        """
        A foreign-currency purchase is billed with a bill date and an
        accounting date that fall on days with different exchange rates. The
        received goods are valued using the exchange rate of the bill date.
        """
        product = self.product1
        product.categ_id = self.category_avco_auto
        eur = self.env.ref('base.EUR')
        eur.active = True
        self.env.company.currency_id = self.env.ref('base.USD').id

        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        self.env['res.currency.rate'].search([('currency_id', '=', eur.id)]).unlink()
        self.env['res.currency.rate'].create([{
            'name': day,
            'rate': 1 / rate,
            'currency_id': eur.id,
            'company_id': self.env.company.id,
        } for (day, rate) in [(today, 1.5), (yesterday, 1.3), (two_days_ago, 1.25)]])

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'currency_id': eur.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': 1.0,
                'price_unit': 100.0,
                'tax_ids': False,
            })],
        })
        po.button_confirm()
        receipt = self._receive(po)
        # Received today: valued at today's rate (100 EUR = 150 USD).
        self.assertEqual(receipt.value, 150.0)
        self.assertEqual(product.total_value, 150.0)

        bill = self.env['account.move'].browse(po.action_create_invoice()['res_id'])
        bill.invoice_date = two_days_ago
        bill.date = yesterday
        bill.action_post()

        # The bill values the goods at the bill-date rate (100 EUR = 125 USD),
        # not the accounting-date (130) nor the receipt-date (150) rate.
        self.assertEqual(receipt.value, 125.0)
        self.assertRecordValues(product, [{
            'total_value': 125.0,
            'standard_price': 125.0,
        }])
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 125.0)

    def test_multicurrency_bill_before_receipt_values_at_bill_rate(self):
        """A foreign-currency purchase billed before its goods are received
        values the received goods at the exchange rate of the bill date, not
        the rate of the later receipt date.
        """
        product = self.product1  # fifo, real_time
        product.purchase_method = 'purchase'
        eur = self.env.ref('base.EUR')
        eur.active = True
        self.env.company.currency_id = self.env.ref('base.USD').id

        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        self.env['res.currency.rate'].search([('currency_id', '=', eur.id)]).unlink()
        self.env['res.currency.rate'].create([{
            'name': day,
            'rate': 1 / rate,
            'currency_id': eur.id,
            'company_id': self.env.company.id,
        } for (day, rate) in [(today, 0.4), (yesterday, 0.5)]])

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'currency_id': eur.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': 1.0,
                'price_unit': 100.0,
                'tax_ids': False,
            })],
        })
        po.button_confirm()

        # Bill the order before the goods are received, dated one day ago.
        bill = self.env['account.move'].browse(po.action_create_invoice()['res_id'])
        bill.invoice_date = bill.date = yesterday
        bill.action_post()

        # Receive the goods afterwards, on a day with a different rate.
        receipt = self._receive(po)

        # Valued at the bill-date rate (100 EUR = 50 USD), not the receipt-date
        # rate (100 EUR = 40 USD).
        self.assertEqual(receipt.value, 50.0)
        self.assertRecordValues(product, [{
            'total_value': 50.0,
            'standard_price': 50.0,
            'qty_available': 1.0,
        }])
        self.assertEqual(sum(self._get_stock_valuation_move_lines().mapped('balance')), 50.0)

    def test_multicurrency_bill_after_delivery_revalues_at_bill_rate(self):
        """A foreign-currency purchase billed after its goods have been received
        and delivered still revalues the received goods at the bill-date
        exchange rate; the delivery keeps the rate at which it was made.
        """
        product = self.product1
        product.categ_id = self.category_avco_auto
        eur = self.env.ref('base.EUR')
        eur.active = True
        self.env.company.currency_id = self.env.ref('base.USD').id

        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        self.env['res.currency.rate'].search([('currency_id', '=', eur.id)]).unlink()
        self.env['res.currency.rate'].create([{
            'name': day,
            'rate': 1 / rate,
            'currency_id': eur.id,
            'company_id': self.env.company.id,
        } for (day, rate) in [(today, 2.5), (yesterday, 2.0)]])

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'currency_id': eur.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_qty': 1.0,
                'price_unit': 1000.0,
                'tax_ids': False,
            })],
        })
        po.button_confirm()

        # Received today: valued at today's rate (1000 EUR = 2500 USD).
        receipt = self._receive(po)
        self.assertEqual(receipt.value, 2500.0)
        self.assertEqual(product.total_value, 2500.0)

        # Deliver the goods to a customer.
        out_move = self._make_out_move(product, 1)
        self.assertEqual(product.total_value, 0.0)
        self.assertEqual(out_move.value, 2500.0)

        # Bill the order dated one day ago, on a day with a different rate.
        bill = self.env['account.move'].browse(po.action_create_invoice()['res_id'])
        bill.invoice_date = bill.date = yesterday
        bill.action_post()

        # The bill revalues the receipt to the bill-date rate (1000 EUR = 2000
        # USD); the delivery keeps the rate it was made at.
        self.assertEqual(receipt.value, 2000.0)
        self.assertEqual(out_move.value, 2500.0)
        self.assertEqual(product.total_value, 0.0)
