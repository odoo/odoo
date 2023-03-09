# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import Form, tagged


@freeze_time("2021-01-14 09:12:15")
@tagged('post_install', '-at_install')
class TestPurchaseOrder(ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.product_id_1 = cls.env['product.product'].create({'name': 'Large Desk', 'purchase_method': 'purchase'})
        cls.product_id_2 = cls.env['product.product'].create({'name': 'Conference Chair', 'purchase_method': 'purchase'})

        cls.po_vals = {
            'partner_id': cls.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': cls.product_id_1.name,
                    'product_id': cls.product_id_1.id,
                    'product_qty': 5.0,
                    'product_uom': cls.product_id_1.uom_po_id.id,
                    'price_unit': 500.0,
                    'date_planned': datetime.today().replace(hour=9).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
                (0, 0, {
                    'name': cls.product_id_2.name,
                    'product_id': cls.product_id_2.id,
                    'product_qty': 5.0,
                    'product_uom': cls.product_id_2.uom_po_id.id,
                    'price_unit': 250.0,
                    'date_planned': datetime.today().replace(hour=9).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        }

    def test_00_purchase_order_flow(self):
        # Ensure product_id_2 doesn't have res_partner_1 as supplier
        if self.partner_a in self.product_id_2.seller_ids.mapped('name'):
            id_to_remove = self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_a).ids[0] if self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_a) else False
            if id_to_remove:
                self.product_id_2.write({
                    'seller_ids': [(2, id_to_remove, False)],
                })
        self.assertFalse(self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_a), 'Purchase: the partner should not be in the list of the product suppliers')

        self.po = self.env['purchase.order'].create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')
        self.assertEqual(self.po.invoice_status, 'no', 'Purchase: PO invoice_status should be "Not purchased"')
        self.assertEqual(self.po.order_line.mapped('qty_received'), [0.0, 0.0], 'Purchase: no product should be received"')
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [0.0, 0.0], 'Purchase: no product should be invoiced"')

        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase"')
        self.assertEqual(self.po.invoice_status, 'to invoice', 'Purchase: PO invoice_status should be "Waiting Invoices"')

        self.assertTrue(self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_a), 'Purchase: the partner should be in the list of the product suppliers')

        seller = self.product_id_2._select_seller(partner_id=self.partner_a, quantity=2.0, date=self.po.date_planned, uom_id=self.product_id_2.uom_po_id)
        price_unit = seller.price if seller else 0.0
        if price_unit and seller and self.po.currency_id and seller.currency_id != self.po.currency_id:
            price_unit = seller.currency_id._convert(price_unit, self.po.currency_id, self.po.company_id, self.po.date_order)
        self.assertEqual(price_unit, 250.0, 'Purchase: the price of the product for the supplier should be 250.0.')

        self.assertEqual(self.po.incoming_picking_count, 1, 'Purchase: one picking should be created"')
        self.picking = self.po.picking_ids[0]
        self.picking.move_line_ids.write({'qty_done': 5.0})
        self.picking.button_validate()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [5.0, 5.0], 'Purchase: all products should be received"')

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.partner_id = self.partner_a
        move_form.purchase_id = self.po
        self.invoice = move_form.save()

        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [5.0, 5.0], 'Purchase: all products should be invoiced"')

    def test_02_po_return(self):
        """
        Test a PO with a product on Incoming shipment. Validate the PO, then do a return
        of the picking with Refund.
        """
        # Draft purchase order created
        self.po = self.env['purchase.order'].create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')
        self.assertEqual(self.po.order_line.mapped('qty_received'), [0.0, 0.0], 'Purchase: no product should be received"')
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [0.0, 0.0], 'Purchase: no product should be invoiced"')

        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase"')
        self.assertEqual(self.po.invoice_status, 'to invoice', 'Purchase: PO invoice_status should be "Waiting Invoices"')

        # Confirm the purchase order
        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase')
        self.assertEqual(self.po.incoming_picking_count, 1, 'Purchase: one picking should be created"')
        self.picking = self.po.picking_ids[0]
        self.picking.move_line_ids.write({'qty_done': 5.0})
        self.picking.button_validate()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [5.0, 5.0], 'Purchase: all products should be received"')

        #After Receiving all products create vendor bill.
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = self.partner_a
        move_form.purchase_id = self.po
        self.invoice = move_form.save()
        self.invoice.action_post()

        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [5.0, 5.0], 'Purchase: all products should be invoiced"')

        # Check quantity received
        received_qty = sum(pol.qty_received for pol in self.po.order_line)
        self.assertEqual(received_qty, 10.0, 'Purchase: Received quantity should be 10.0 instead of %s after validating incoming shipment' % received_qty)

        # Create return picking
        pick = self.po.picking_ids
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=pick.ids, active_id=pick.ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.write({'quantity': 2.0, 'to_refund': True})  # Return only 2
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Validate picking
        return_pick.move_line_ids.write({'qty_done': 2})

        return_pick.button_validate()

        # Check Received quantity
        self.assertEqual(self.po.order_line[0].qty_received, 3.0, 'Purchase: delivered quantity should be 3.0 instead of "%s" after picking return' % self.po.order_line[0].qty_received)
        #Create vendor bill for refund qty
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_refund'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = self.partner_a
        move_form.purchase_id = self.po
        self.invoice = move_form.save()
        move_form = Form(self.invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 2.0
        with move_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 2.0
        self.invoice = move_form.save()
        self.invoice.action_post()

        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [3.0, 3.0], 'Purchase: Billed quantity should be 3.0')

    def test_03_po_return_and_modify(self):
        """Change the picking code of the delivery to internal. Make a PO for 10 units, go to the
        picking and return 5, edit the PO line to 15 units.
        The purpose of the test is to check the consistencies across the received quantities and the
        procurement quantities.
        """
        # Change the code of the picking type delivery
        self.env['stock.picking.type'].search([('code', '=', 'outgoing')]).write({'code': 'internal'})

        # Sell and deliver 10 units
        item1 = self.product_id_1
        uom_unit = self.env.ref('uom.product_uom_unit')
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': item1.name,
                    'product_id': item1.id,
                    'product_qty': 10,
                    'product_uom': uom_unit.id,
                    'price_unit': 123.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking = po1.picking_ids
        wiz_act = picking.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        # Return 5 units
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=picking.ids,
            active_id=picking.ids[0],
            active_model='stock.picking'
        ))
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({
                'quantity': 5,
                'to_refund': True
            })
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])
        wiz_act = return_pick.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        self.assertEqual(po1.order_line.qty_received, 5)

        # Deliver 15 instead of 10.
        po1.write({
            'order_line': [
                (1, po1.order_line[0].id, {'product_qty': 15}),
            ]
        })

        # A new move of 10 unit (15 - 5 units)
        self.assertEqual(po1.order_line.qty_received, 5)
        self.assertEqual(po1.picking_ids[-1].move_lines.product_qty, 10)

    def test_04_update_date_planned(self):
        today = datetime.today().replace(hour=9, microsecond=0)
        tomorrow = datetime.today().replace(hour=9, microsecond=0) + timedelta(days=1)
        po = self.env['purchase.order'].create(self.po_vals)
        po.button_confirm()

        # update first line
        po._update_date_planned_for_lines([(po.order_line[0], tomorrow)])
        self.assertEqual(po.order_line[0].date_planned, tomorrow)
        activity = self.env['mail.activity'].search([
            ('summary', '=', 'Date Updated'),
            ('res_model_id', '=', 'purchase.order'),
            ('res_id', '=', po.id),
        ])
        self.assertTrue(activity)
        self.assertEqual(
            '<p>partner_a modified receipt dates for the following products:</p>\n'
            '<p> - Large Desk from %s to %s</p>\n'
            '<p>Those dates have been updated accordingly on the receipt %s.</p>' % (today.date(), tomorrow.date(), po.picking_ids.name),
            activity.note,
        )

        # receive products
        wiz_act = po.picking_ids.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        # update second line
        old_date = po.order_line[1].date_planned
        po._update_date_planned_for_lines([(po.order_line[1], tomorrow)])
        self.assertEqual(po.order_line[1].date_planned, old_date)
        self.assertEqual(
            '<p>partner_a modified receipt dates for the following products:</p>\n'
            '<p> - Large Desk from %s to %s</p>\n'
            '<p> - Conference Chair from %s to %s</p>\n'
            '<p>Those dates couldn’t be modified accordingly on the receipt %s which had already been validated.</p>' % (
                today.date(), tomorrow.date(), today.date(), tomorrow.date(), po.picking_ids.name),
            activity.note,
        )

    def test_05_multi_company(self):
        company_a = self.env.user.company_id
        company_b = self.env['res.company'].create({
            "name": "Test Company",
            "currency_id": self.env['res.currency'].with_context(active_test=False).search([
                ('id', '!=', company_a.currency_id.id),
            ], limit=1).id
        })
        self.env.user.write({
            'company_id': company_b.id,
            'company_ids': [(4, company_b.id), (4, company_a.id)],
        })
        po = self.env['purchase.order'].create(dict(company_id=company_a.id, partner_id=self.partner_a.id))

        self.assertEqual(po.company_id, company_a)
        self.assertEqual(po.picking_type_id.warehouse_id.company_id, company_a)
        self.assertEqual(po.currency_id, po.company_id.currency_id)

    def test_06_on_time_rate(self):
        company_a = self.env.user.company_id
        company_b = self.env['res.company'].create({
            "name": "Test Company",
            "currency_id": self.env['res.currency'].with_context(active_test=False).search([
                ('id', '!=', company_a.currency_id.id),
            ], limit=1).id
        })

        # Create a purchase order with 90% qty received for company A
        self.env.user.write({
            'company_id': company_a.id,
            'company_ids': [(6, 0, [company_a.id])],
        })
        po = self.env['purchase.order'].create(self.po_vals)
        po.order_line.write({'product_qty': 10})
        po.button_confirm()
        picking = po.picking_ids[0]
        # Process 9.0 out of the 10.0 ordered qty
        picking.move_line_ids.write({'qty_done': 9.0})
        res_dict = picking.button_validate()
        # No backorder
        self.env['stock.backorder.confirmation'].with_context(res_dict['context']).process_cancel_backorder()
        # `on_time_rate` should be equals to the ratio of quantity received against quantity ordered
        expected_rate = sum(picking.move_line_ids.mapped("qty_done")) / sum(po.order_line.mapped("product_qty")) * 100
        self.assertEqual(expected_rate, po.on_time_rate)

        # Create a purchase order with 80% qty received for company B
        # The On-Time Delivery Rate shouldn't be shared across multiple companies
        self.env.user.write({
            'company_id': company_b.id,
            'company_ids': [(6, 0, [company_b.id])],
        })
        po = self.env['purchase.order'].create(self.po_vals)
        po.order_line.write({'product_qty': 10})
        po.button_confirm()
        picking = po.picking_ids[0]
        # Process 8.0 out of the 10.0 ordered qty
        picking.move_line_ids.write({'qty_done': 8.0})
        res_dict = picking.button_validate()
        # No backorder
        self.env['stock.backorder.confirmation'].with_context(res_dict['context']).process_cancel_backorder()
        # `on_time_rate` should be equal to the ratio of quantity received against quantity ordered
        expected_rate = sum(picking.move_line_ids.mapped("qty_done")) / sum(po.order_line.mapped("product_qty")) * 100
        self.assertEqual(expected_rate, po.on_time_rate)

        # Tricky corner case
        # As `purchase.order.on_time_rate` is a related to `partner_id.on_time_rate`
        # `on_time_rate` on the PO should equals `on_time_rate` on the partner.
        # Related fields are by default computed as sudo
        # while non-stored computed fields are not computed as sudo by default
        # If the computation of the related field (`purchase.order.on_time_rate`) was asked
        # and `res.partner.on_time_rate` was not yet in the cache
        # the `sudo` requested for the computation of the related `purchase.order.on_time_rate`
        # was propagated to the computation of `res.partner.on_time_rate`
        # and therefore the multi-company record rules were ignored.
        # 1. Compute `res.partner.on_time_rate` regular non-stored comptued field
        partner_on_time_rate = po.partner_id.on_time_rate
        # 2. Invalidate the cache for that record and field, so it's not reused in the next step.
        po.partner_id.invalidate_cache(fnames=["on_time_rate"], ids=po.partner_id.ids)
        # 3. Compute the related field `purchase.order.on_time_rate`
        po_on_time_rate = po.on_time_rate
        # 4. Check both are equals.
        self.assertEqual(partner_on_time_rate, po_on_time_rate)

    def test_04_multi_uom(self):
        yards_uom = self.env['uom.uom'].create({
            'category_id': self.env.ref('uom.uom_categ_length').id,
            'name': 'Yards',
            'factor_inv': 0.9144,
            'uom_type': 'bigger',
        })
        self.product_id_2.write({
            'uom_id': self.env.ref('uom.product_uom_meter').id,
            'uom_po_id': yards_uom.id,
        })
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_id_2.name,
                    'product_id': self.product_id_2.id,
                    'product_qty': 4.0,
                    'product_uom': self.product_id_2.uom_po_id.id,
                    'price_unit': 1.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })
            ],
        })
        po.button_confirm()
        picking = po.picking_ids[0]
        picking.move_line_ids.write({'qty_done': 3.66})
        picking.button_validate()
        self.assertEqual(po.order_line.mapped('qty_received'), [4.0], 'Purchase: no conversion error on receipt in different uom"')

    def test_05_po_update_qty_stock_move_merge(self):
        """ This test ensures that changing product quantity when unit price has high decimal precision
            merged with the original instead of creating a new return
        """

        unit_price_precision = self.env['decimal.precision'].search([('name', '=', 'Product Price')])
        unit_price_precision.digits = 6

        tax = self.env["account.tax"].create({
            "name": "Dummy Tax",
            "amount": "5.00",
            "type_tax_use": "purchase",
        })

        super_product = self.env['product.product'].create({
            'name': 'Super Product',
            'type': 'product',
            'categ_id': self.stock_account_product_categ.id,
            'standard_price': 9.876543,
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.env.ref('base.res_partner_3').id,
            'order_line': [(0, 0, {
                'name': super_product.name,
                'product_id': super_product.id,
                'product_qty': 7,
                'product_uom': super_product.uom_id.id,
                'price_unit': super_product.standard_price,
                'taxes_id': [(4, tax.id)],
            })],
        })

        purchase_order.button_confirm()
        self.assertEqual(purchase_order.state, 'purchase')
        self.assertEqual(len(purchase_order.picking_ids), 1)
        self.assertEqual(len(purchase_order.picking_ids.move_line_ids), 1)
        self.assertEqual(purchase_order.picking_ids.move_line_ids.product_qty, 7)


        purchase_order.order_line.product_qty = 4
        # updating quantity shouldn't create a seperate stock move
        # the new stock move (-3) should be merged with the previous
        purchase_order.button_confirm()
        self.assertEqual(len(purchase_order.picking_ids), 1)
        self.assertEqual(len(purchase_order.picking_ids.move_line_ids), 1)
        self.assertEqual(purchase_order.picking_ids.move_line_ids.product_qty, 4)

    def test_message_qty_already_received(self):
        _product = self.env['product.product'].create({
            'name': 'TempProduct',
            'type': 'consu',
            'company_id': self.env.user.company_id.id,
        })

        _purchase_order = self.env['purchase.order'].create({
            'company_id': self.env.user.company_id.id,
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': _product.name,
                    'product_id': _product.id,
                    'product_qty': 25.0,
                    'price_unit': 250.0,
                })],
        })

        _purchase_order.button_confirm()

        first_picking = _purchase_order.picking_ids[0]
        first_picking.move_lines.quantity_done = 5
        backorder_wizard_dict = first_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        second_picking = _purchase_order.picking_ids[1]
        second_picking.move_lines.quantity_done = 5
        backorder_wizard_dict = second_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        third_picking = _purchase_order.picking_ids[2]
        third_picking.move_lines.quantity_done = 5
        backorder_wizard_dict = third_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        _message_content = _purchase_order.message_ids.mapped("body")[0]
        self.assertIsNotNone(re.search(r"Received Quantity: 5.0 -&gt; 10.0", _message_content), "Already received quantity isn't correctly taken into consideration")

    def test_pol_description(self):
        """
        Suppose a product with several sellers, all with the same partner. On the purchase order, the product
        description should be based on the correct seller
        """
        self.env.user.write({'company_id': self.company_data['company'].id})

        product = self.env['product.product'].create({
            'name': 'Super Product',
            'seller_ids': [(0, 0, {
                'name': self.partner_a.id,
                'min_qty': 1,
                'price': 10,
                'product_code': 'C01',
                'product_name': 'Name01',
                'sequence': 1,
            }), (0, 0, {
                'name': self.partner_a.id,
                'min_qty': 20,
                'price': 2,
                'product_code': 'C02',
                'product_name': 'Name02',
                'sequence': 2,
            })]
        })

        orderpoint_form = Form(self.env['stock.warehouse.orderpoint'])
        orderpoint_form.product_id = product
        orderpoint_form.product_min_qty = 1
        orderpoint_form.product_max_qty = 0.000
        order_point = orderpoint_form.save()

        self.env['procurement.group'].run_scheduler()

        pol = self.env['purchase.order.line'].search([('product_id', '=', product.id)])
        self.assertEqual(pol.name, "[C01] Name01")

        with Form(pol.order_id) as po_form:
            with po_form.order_line.edit(0) as pol_form:
                pol_form.product_qty = 25
        self.assertEqual(pol.name, "[C02] Name02")

    def test_packaging_and_qty_decrease(self):
        packaging = self.env['product.packaging'].create({
            'name': "Super Packaging",
            'product_id': self.product_a.id,
            'qty': 10.0,
        })

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_a
        with po_form.order_line.new() as line:
            line.product_id = self.product_a
            line.product_qty = 10
        po = po_form.save()
        po.button_confirm()

        self.assertEqual(po.order_line.product_packaging_id, packaging)

        with Form(po) as po_form:
            with po_form.order_line.edit(0) as line:
                line.product_qty = 8

        self.assertEqual(po.picking_ids.move_lines.product_uom_qty, 8)

    def test_packaging_propagation(self):
        """
        Editing the packaging on an purchase.order.line
        should propagate to the delivery order, so that
        when we are editing the packaging, the lines can be merged
        with the new packaging and quantity.
        """
        # set the 3 step route
        warehouse = self.company_data['default_warehouse']
        warehouse.reception_steps = 'three_steps'
        packOf10 = self.env['product.packaging'].create({
            'name': 'PackOf10',
            'product_id': self.product_a.id,
            'qty': 10
        })

        packOf20 = self.env['product.packaging'].create({
            'name': 'PackOf20',
            'product_id': self.product_a.id,
            'qty': 20
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_uom_qty': 10.0,
                    'product_uom': self.product_a.uom_id.id,
                    'product_packaging_id': packOf10.id,
                })],
        })
        po.button_confirm()
        # the 3 moves for the 3 steps
        step_1 = po.order_line.move_ids
        step_2 = step_1.move_dest_ids
        step_3 = step_2.move_dest_ids
        self.assertEqual(step_1.product_packaging_id, packOf10)
        self.assertEqual(step_2.product_packaging_id, packOf10)
        self.assertEqual(step_3.product_packaging_id, packOf10)

        po.order_line[0].write({
            'product_packaging_id': packOf20.id,
            'product_uom_qty': 20
        })
        self.assertEqual(step_1.product_packaging_id, packOf20)
        self.assertEqual(step_2.product_packaging_id, packOf20)
        self.assertEqual(step_3.product_packaging_id, packOf20)

        po.order_line[0].write({'product_packaging_id': False})
        self.assertFalse(step_1.product_packaging_id)
        self.assertFalse(step_2.product_packaging_id)
        self.assertFalse(step_3.product_packaging_id)

    def test_putaway_strategy_in_backorder(self):
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        sub_loc_01 = self.env['stock.location'].create([{
            'name': 'Sub Location 1',
            'usage': 'internal',
            'location_id': stock_location.id,
        }])
        self.env["stock.putaway.rule"].create({
            "location_in_id": stock_location.id,
            "location_out_id": sub_loc_01.id,
            "product_id": self.product_a.id,
        })
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'product_qty': 2.0,
                })],
        })
        po.button_confirm()
        picking = po.picking_ids
        self.assertEqual(po.state, "purchase")
        self.assertEqual(picking.move_line_ids_without_package.location_dest_id.id, sub_loc_01.id)
        picking.move_line_ids_without_package.write({'qty_done': 1})
        res_dict = picking.button_validate()
        self.env[res_dict['res_model']].with_context(res_dict['context']).process()
        backorder = picking.backorder_ids
        self.assertEqual(backorder.move_line_ids_without_package.location_dest_id.id, sub_loc_01.id)
