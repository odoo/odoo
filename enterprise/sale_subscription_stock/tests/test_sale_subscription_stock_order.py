# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.sale_subscription_stock.tests.common_sale_subscription_stock import TestSubscriptionStockCommon
from odoo.tests import tagged, Form
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install')
class TestSubscriptionStockOnOrder(TestSubscriptionStockCommon):

    def test_subscription_stock_order_base(self):
        """ Test invoice and picking order creation in case of one or multiple 'on_order'
            storable items in the subscription
        """
        sub = self.subscription_order

        with freeze_time("2022-03-02"):
            self.assertEqual(sub.invoice_count, 0, 'Until the first invoicing, we should not have invoiced anything')
            self.assertEqual(len(sub.picking_ids), 1,
                             'After confirming the subscription, we should have created a delivery order')
            self.env['sale.order']._cron_recurring_create_invoice()
            # Check that the invoice information are correct
            self.assertEqual(sub.invoice_count, 1, 'The automated action should have invoiced the first period')
            self.assertEqual(sub.order_line.qty_invoiced, 1, 'Order line should now be marked as invoiced')
            self.assertEqual(sub.invoice_ids.amount_total, 45)
            invoice_line = sub.invoice_ids.invoice_line_ids
            self.assertEqual(invoice_line.name.split('\n')[1], '1 Months 03/02/2022 to 04/01/2022')
            self.assertEqual(invoice_line.product_id, self.sub_product_order)
            self.assertEqual(invoice_line.quantity, 1)
            self.assertEqual(sub.order_line.qty_invoiced, 1, 'Order line should still be marked as invoiced')
            # Check that the delivery order information are correct
            move = sub.picking_ids.move_ids
            self.assertEqual(len(sub.picking_ids), 1,
                             'Now that the invoice is confirmed, the first picking order should be present')
            self.assertEqual(move.date_deadline.date(), sub.next_invoice_date - relativedelta(days=1),
                             'The delivery deadline should correspond to the current period')
            self.assertEqual(move.product_id, self.sub_product_order)
            self.assertEqual(move.product_uom_qty, 1)
            self.assertEqual(move.quantity, 1, 'Move should be delivered now')
            self.assertEqual(sub.order_line.qty_delivered, 1, 'Order line should be marked as delivered')

    def test_subscription_stock_order_cron(self):

        sub = self.subscription_order.copy()

        # Simulate cron before start_date
        invoice, picking = self.simulate_period(sub, "2022-02-02")
        self.assertEqual(sub.invoice_count, 0, 'Subscription should have 0 invoices before start date')
        self.assertEqual(len(sub.picking_ids), 0, 'Subscription should have 0 delivery order before start date')

        sub.action_confirm()
        sub.picking_ids.move_ids.write({'quantity': sub.order_line.product_uom_qty, 'picked': True})
        sub.picking_ids._action_done()
        for n_iter, date in enumerate(["2022-03-02", "2022-04-02", "2022-05-02", "2022-06-02"], 1):
            invoice, picking = self.simulate_period(sub, date)
            self.assertEqual(sub.invoice_count, n_iter, f'Subscription should have {n_iter} invoices at date {date}')
            self.assertEqual(len(sub.picking_ids), n_iter,
                             f'Subscription should have {n_iter} delivery order at date {date}')
            self.assertEqual(invoice.invoice_line_ids.quantity, 1, 'We should always invoice the same quantity')
            self.assertEqual(invoice.amount_total, 45, 'And the same amount')
            self.assertEqual(invoice.date.isoformat(), date, 'Invoice date should correspond to the current date')
            # For first invoice it does not create a new delivery
            if sub.invoice_count != 1:
                self.assertEqual(picking.move_ids.product_uom_qty, 1, 'We should always invoice the same quantity')
                self.assertEqual((picking.date_deadline.date() - relativedelta(months=1) + relativedelta(days=1)).isoformat(), date,
                                'Delivery deadline should correspond to the date + one more month')

        # End of subscription
        sub.write({'end_date': "2022-07-02"})
        invoice, picking = self.simulate_period(sub, "2022-07-02")
        self.assertEqual(len(invoice), 0, 'We should ont generate new invoices')
        self.assertEqual(len(picking), 0, 'We should ont generate new delivery order')

    def test_subscription_stock_order_close(self):

        sub = self.subscription_order

        invoice, picking = self.simulate_period(sub, "2022-03-02")
        self.assertEqual(len(invoice), 1, 'We should generate a new invoices')
        self.assertEqual(len(picking), 1, 'We should generate a new delivery order')

        sub.set_close()
        invoice, picking = self.simulate_period(sub, "2022-04-02")

        self.assertEqual(len(invoice), 0, 'We should not generate new invoices')
        self.assertEqual(len(picking), 0, 'We should not generate new delivery order')

    def test_subscription_stock_order_update_recurrence(self):
        sub = self.subscription_order

        invoice, picking = self.simulate_period(sub, "2022-03-02")
        self.assertEqual(picking.move_ids.product_uom_qty, 1, 'The delivered quantity is as expected')
        self.assertEqual(invoice.invoice_line_ids.quantity, 1, 'We should invoice the quantity ordered')
        self.assertEqual(sub.order_line.price_unit, 45, 'Price unit should be for the 1 month recurrence')
        self.assertEqual(invoice.amount_total, 45, 'Price in invoice unit should be the same')

        sub.write({
            'plan_id': self.plan_3_months.id,
        })

        self.assertEqual(sub.order_line.price_unit, 45, 'Price unit should not be update for confirmed order')
        self.assertEqual(sub.next_invoice_date.isoformat(), "2022-04-02",
                         'Changing pricing should not affect next order date')
        invoice, picking = self.simulate_period(sub, "2022-04-02")
        self.assertEqual(invoice.amount_total, 45, 'Price unit should not have changed')
        self.assertEqual(sub.next_invoice_date.isoformat(), "2022-07-02",
                         'Next invoice date should be in 3 months')

    def test_subscription_stock_order_update_quantity(self):
        sub = self.subscription_order

        invoice, picking = self.simulate_period(sub, "2022-03-02")
        self.assertEqual(len(invoice), 1, 'We should generate a new invoices')
        self.assertEqual(len(picking), 1, 'We should generate a new delivery order')
        self.assertEqual(picking.move_ids.product_uom_qty, 1, 'The delivered quantity is as expected')
        self.assertEqual(invoice.invoice_line_ids.quantity, 1, 'We should invoice the quantity ordered')

        sub.order_line.product_uom_qty = 2
        self.assertEqual(len(sub.picking_ids), 1, 'Updating the quantity ordered should not create a new delivery')

        invoice, picking = self.simulate_period(sub, "2022-04-02")
        self.assertEqual(picking.move_ids.product_uom_qty, 2, 'The delivered quantity should be the new quantity')
        self.assertEqual(invoice.invoice_line_ids.quantity, 2, 'We should invoice the new quantity')
        self.assertEqual(invoice.amount_total, 45 * 2, 'We should invoice twice the original amount')

    def test_subscription_stock_order_over_deliver(self):
        sub = self.subscription_order

        invoice, picking = self.simulate_period(sub, "2022-03-02", move_qty=2)
        self.assertEqual(len(invoice), 1, 'We should generate a new invoices')
        self.assertEqual(len(picking), 1, 'We should generate a new delivery order')
        self.assertEqual(picking.move_ids.quantity, 2, 'Check that we over_delivered')
        self.assertEqual(invoice.invoice_line_ids.quantity, 1, 'We should invoice the quantity ordered')

        invoice, picking = self.simulate_period(sub, "2022-04-02")
        self.assertEqual(picking.move_ids.quantity, 1, 'Check that we did not over_delivered again')
        self.assertEqual(invoice.invoice_line_ids.quantity, 1, 'We should still invoice the quantity ordered')

    def test_subscription_stock_order_under_deliver(self):
        sub = self.subscription_order.copy()
        sub.order_line.product_uom_qty = 2

        with freeze_time("2022-03-02"):
            sub.write({'start_date': fields.date.today(), 'next_invoice_date': False})
            sub.action_confirm()
            picking_id = sub.picking_ids  # only one picking
            self.assertEqual(len(picking_id), 1, 'After confirming we should create a delivery')
            for move in picking_id.move_ids:
                move.write({'quantity': 1, 'picked': True})
            picking_id._action_done()  # this will create the backorder

            self.assertEqual(picking_id.move_ids.quantity, 1, 'Check that we under_delivered')

        invoice, picking = self.simulate_period(sub, "2022-03-02", move_qty=1)
        self.assertEqual(invoice.invoice_line_ids.quantity, 2, 'We should invoice the quantity ordered')
        self.assertEqual(invoice.amount_total, 45 * 2, 'We should invoice the quantity ordered')

        back_order = sub.picking_ids - picking_id
        self.assertEqual(back_order.move_ids.product_uom_qty, 1, 'We should deliver the remaining quantity')

        invoice, picking = self.simulate_period(sub, "2022-04-02")
        self.assertEqual(invoice.invoice_line_ids.quantity, 2, 'We should invoice the ordered quantity')
        self.assertEqual(back_order.move_ids.mapped('product_uom_qty'), [1.0],
                         'The new delivery should be added to the old one')
        self.assertEqual(picking.move_ids.product_uom_qty, 2,
                         'The new delivery should be added for second invoice')

    def test_subscription_stock_order_multiple_products(self):
        sub = self.env['sale.order'].create({
            'name': 'Order',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                'product_id': self.sub_product_order.id,
                'product_uom_qty': 1,
                'tax_id': [Command.clear()],
                }),
                Command.create({
                'product_id': self.sub_product_order_2.id,
                'product_uom_qty': 2,
                'tax_id': [Command.clear()],
                }),
            ]
        })

        with freeze_time("2022-03-02"):
            sub.write({'start_date': False, 'next_invoice_date': False})
            sub.action_confirm()

        invoice, picking = self.simulate_period(sub, "2022-03-02")
        self.assertEqual(len(invoice), 1, 'We should generate a new invoices')
        self.assertEqual(len(invoice.invoice_line_ids), 2, 'With 2 lines')
        self.assertEqual(invoice.invoice_line_ids.mapped('quantity'), [1, 2], 'And correct quantity')
        self.assertEqual(invoice.amount_total, 45 * 3, 'And the correct amount')
        self.assertEqual(len(picking), 1, 'We should generate a new delivery order')
        self.assertEqual(len(picking.move_ids), 2, 'With 2 move_line')
        self.assertEqual(picking.move_ids.mapped('product_uom_qty'), [1, 2], 'And correct quantity')

    def test_subscription_stock_order_non_recurring_product(self):
        sub = self.env['sale.order'].create({
            'name': 'Order',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                'product_id': self.sub_product_order.id,
                'product_uom_qty': 1,
                'tax_id': [Command.clear()],
                }),
                Command.create({
                'product_id': self.test_product_order.id,
                'price_unit': 1,
                'product_uom_qty': 1,
                'tax_id': [Command.clear()],
                }),
            ]
        })

        with freeze_time("2022-03-01"):
            sub.write({'start_date': False, 'next_invoice_date': False})
            sub.action_confirm()

        self.assertEqual(len(sub.picking_ids), 1, 'We should create a delivery order for the non-recurring product')
        self.assertEqual(sub.picking_ids.move_ids.product_id.ids, [self.sub_product_order.id, self.test_product_order.id])

        # We deliver the non-recurring product
        sub.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        sub.picking_ids._action_done()

        invoice, picking = self.simulate_period(sub, "2022-03-02")
        self.assertEqual(len(invoice.invoice_line_ids), 2, 'We should invoice the 2 lines')
        self.assertEqual(invoice.amount_total, 45 + 1,
                         'Invoice price should be the 1 month pricing + 1$ for the non-recurring product')

        invoice, picking = self.simulate_period(sub, "2022-04-02")
        self.assertEqual(len(invoice.invoice_line_ids), 1, 'We should invoice the recurring line')
        self.assertEqual(invoice.amount_total, 45, 'Invoice price should be the 1 month pricing')
        self.assertEqual(picking.move_ids.product_id, self.sub_product_order,
                         'We should only deliver the recurring product')

    def test_subscription_stock_order_upsell(self):
        sub = self.subscription_order

        dummy, dummy = self.simulate_period(sub, "2022-03-02")

        with freeze_time("2021-03-15"):
            action = sub.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])

            order_line = upsell_so.order_line.filtered(lambda sol: not sol.display_type)
            self.assertEqual(len(order_line), 1, 'There should only be one line')
            self.assertEqual(order_line.price_unit, 45, 'The price_unit should be 45')
            self.assertEqual(order_line.discount, 0, 'The discount should be 0')
            self.assertEqual(order_line.product_uom_qty, 0, 'The upsell order has 0 quantity')

            upsell_so.order_line.filtered('product_id').product_uom_qty = 2
            upsell_so.action_confirm()

            upsell_move = upsell_so.picking_ids.move_ids

            self.assertEqual(len(upsell_move), 1, 'Confirming the SO should create a delivery order in the upsell')
            self.assertEqual(upsell_move.product_qty, 2, 'With a product quantity of 2')

            self.assertEqual(sub.order_line.product_uom_qty, 3, 'Check that the order has the updated quantity')
            self.assertEqual(sub.invoice_count, 1, 'We should not have created another invoice')

            self.assertEqual(len(sub.picking_ids.move_ids), 1, 'We should not have created another delivery order')

        dummy, picking = self.simulate_period(sub, "2022-04-02")

        self.assertEqual(picking.move_ids.product_uom_qty, 3, 'The new period should deliver 3 products')

    def test_subscription_stock_order_upsell_delivery(self):
        sub = self.subscription_order
        sub_consumable_product = self.env['product.template'].create({
            'recurring_invoice': True,
            'sale_ok': True,
            'purchase_ok': True,
            'type': 'consu',
            'list_price': 1.0,
            'invoice_policy': 'order',
            'name': 'Subscription Consumable'
        })

        self.simulate_period(sub, "2022-03-02")

        with freeze_time("2022-03-02"):
            action = sub.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])

            new_line = self.env['sale.order.line'].create({
                'name': sub_consumable_product.name,
                'order_id': upsell_so.id,
                'product_id': sub_consumable_product.product_variant_id.id,
                'product_uom_qty': 10
            })
            upsell_so.order_line = [(6, 0, new_line.ids)]
            self.assertEqual(len(upsell_so.order_line), 1, 'There should only be one line')
            self.assertEqual(upsell_so.order_line.price_unit, 1, 'The price_unit should be 1')
            self.assertEqual(upsell_so.order_line.discount, 0, 'The discount should be 0')
            self.assertEqual(upsell_so.order_line.product_uom_qty, 10, 'The upsell order has 10 quantity')
            upsell_so.action_confirm()

            upsell_move = upsell_so.picking_ids.move_ids

            self.assertEqual(len(upsell_move), 1, 'Confirming the SO should create a delivery order in the upsell')
            self.assertEqual(upsell_move.product_qty, 10, 'With a product quantity of 10')
            upsell_so.picking_ids.button_validate()
            self.assertEqual(upsell_so.order_line.qty_delivered, 10, "Upsell should have delivered 10 items")
            self.assertEqual(upsell_so.order_line.qty_invoiced, 0, "Upsell line should have invoiced 0 items")
            self.assertEqual(upsell_so.order_line.parent_line_id.qty_delivered, 10, "Sub line should have delivered 10 items")
            self.assertEqual(upsell_so.order_line.parent_line_id.qty_invoiced, 10, "Sub line should have invoiced 10 items")
    def test_upsell_stored_product(self):
        sub = self.subscription_order

        dummy, dummy = self.simulate_period(sub, "2022-03-02")
        with freeze_time("2021-03-15"):
            action = sub.prepare_upsell_order()
            upsell_so = self.env['sale.order'].browse(action['res_id'])
            stored_prod = self.env['product.product'].create({
                'name': 'Stored product',
                'is_storable': True,
            })
            upsell_so.write({'order_line': [
                Command.create({
                    'product_id': stored_prod.id,
                    'product_uom_qty': 1,
                }),
            ]})
            upsell_so.action_confirm()
            self.assertEqual(len(upsell_so.picking_ids.move_ids), 1)
            self.assertEqual(upsell_so.picking_ids.move_ids.product_id, stored_prod)
        self.assertEqual(len(sub.picking_ids.move_ids), 1)
        self.assertEqual(sub.picking_ids.move_ids.product_id, self.sub_product_order)

    def test_subscription_product_delivery_creation(self):
        if self.env['ir.module.module']._get('sale_mrp').state != 'installed':
            self.skipTest("If the 'sale_mrp' module isn't installed, we can't test bom!")
        self.additional_kit_product = self.env['product.product'].create({
            'name': 'Mug',
            'is_storable': True,
            'standard_price': 10.0,
            'uom_id': self.uom_unit.id,
            'recurring_invoice': False,
        })

        self.bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.sub_product_order.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1,
            'type': 'phantom',
        })

        self.bom.bom_line_ids.create({
            'bom_id': self.bom.id,
            'product_id': self.additional_kit_product.id,
            'product_qty': 1,
            'product_uom_id': self.uom_unit.id,
        })

        self.inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.additional_kit_product.id,
            'product_tmpl_id': self.additional_kit_product.product_tmpl_id.id,
            'new_quantity': 100.0,
        })
        self.inventory_wizard.change_product_qty()

        self.subscription_order_with_bom = self.env['sale.order'].create({
            'name': 'Order',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [
                Command.create(
                    {'product_id': self.sub_product_order.id, 'product_uom_qty': 1, 'tax_id': [Command.clear()]}
                ),
                Command.create(
                    {'product_id': self.additional_kit_product.id, 'product_uom_qty': 1, 'tax_id': [Command.clear()]}
                )
            ]
        })

        with freeze_time("2024-02-02"):
            self.subscription_order_with_bom.write({'start_date': fields.date.today(), 'next_invoice_date': False})
            self.subscription_order_with_bom.action_confirm()
            self.assertEqual(self.subscription_order_with_bom.invoice_count, 0,
                             'No invoices should be present initially')
            self.assertEqual(
                len(self.subscription_order_with_bom.picking_ids), 1,
                'A delivery order should be created for non-recurring products'
            )
            self.assertEqual(
                len(self.subscription_order_with_bom.picking_ids[0].move_ids), 2,
                'A move should be added to the picking before invoicing for non-recurring product'
            )
            self.assertEqual(self.subscription_order_with_bom.order_line[0].product_id.qty_available, 100)
            first_invoice, picking = self.simulate_period(self.subscription_order_with_bom, "2024-02-02")
            self.assertEqual(self.subscription_order_with_bom.invoice_count, 1, 'The first period should be invoiced')
            self.assertEqual(
                len(self.subscription_order_with_bom.picking_ids[0].move_ids), 2,
                'A move should be added to the picking after invoicing'
            )
            self.assertTrue(
                self.sub_product_order.name in self.subscription_order_with_bom.picking_ids[0].move_ids[0].description_bom_line,
                'The description should contain the bom line name'
            )
            self.assertEqual(self.subscription_order_with_bom.order_line[0].product_id.qty_available, 98)

        # Return the delivery for the first period
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=self.subscription_order_with_bom.picking_ids.ids, active_id=self.subscription_order_with_bom.picking_ids.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_picking.button_validate()
        self.assertEqual(return_picking.state, 'done')
        self.assertEqual(self.subscription_order_with_bom.order_line[0].product_id.qty_available, 100)
        self.assertEqual(
            len(self.subscription_order_with_bom.picking_ids[0].move_ids), len(first_invoice.invoice_line_ids), 'The invoice lines should match the moves'
        )

        # create invoice for the second period
        with freeze_time("2024-03-02"):
            second_invoice, picking_1 = self.simulate_period(self.subscription_order_with_bom, "2024-03-02")

            self.assertEqual(self.subscription_order_with_bom.invoice_count, 2, 'The second period should be invoiced')
            self.assertEqual(
                len(self.subscription_order_with_bom.picking_ids), 3,
                'A new picking order should be created for the order after the second invoicing'
            )
            self.assertEqual(self.subscription_order_with_bom.order_line[0].product_id.qty_available, 99)
            self.assertTrue(
                self.sub_product_order.name in picking_1.move_ids[0].description_bom_line,
                'The description should contain the bom line name'
            )
            self.assertEqual(
                len(self.subscription_order_with_bom.picking_ids[1].move_ids), len(second_invoice.invoice_line_ids),
                'The move lines should match the moves of the second period'
            )

    def test_stock_user_without_sale_permission_can_access_product_form(self):
        stock_manager = new_test_user(
            self.env, 'temp_stock_manager', 'stock.group_stock_manager',
        )
        Form(self.env['product.product'].with_user(stock_manager))

    def test_subscription_stock_delivery_recurring_product(self):
        # make sure we have enough product on hand
        self.test_product_order.invoice_policy = 'delivery'
        self.sub_product_order.invoice_policy = 'delivery'
        warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.test_product_order.id,
            'location_id': warehouse.lot_stock_id.id,
            'inventory_quantity': 100,
        })._apply_inventory()
        sub = self.env['sale.order'].create({
            'name': 'Order',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                    'product_id': self.sub_product_order.id,
                    'product_uom_qty': 1,
                    'tax_id': [Command.clear()],
                }),
            ]
        })

        with freeze_time("2022-03-01"):
            sub.write({'start_date': False, 'next_invoice_date': False})
            sub.action_confirm()
            self.assertEqual(len(sub.picking_ids), 1, 'One picking should be created')

            self.assertEqual(sub.order_line.mapped('qty_delivered'), [0])
            self.assertEqual(sub.order_line.mapped('qty_to_deliver'), [1])
            self.assertEqual(sub.next_invoice_date, datetime.date(2022, 4, 1))
            rec_line = sub.order_line
            inv = sub._create_recurring_invoice()
            self.assertEqual(rec_line.invoice_status, 'no', 'Invoice status should be no')
            self.assertEqual(len(rec_line.move_ids), 1, 'One move should remain (same as before)')
            self.assertFalse(inv, 'no invoice should be created')
            self.assertTrue(rec_line.move_ids)

        with freeze_time("2022-03-15"):
            self.validate_picking_moves(sub.picking_ids)
            self.assertEqual(rec_line.qty_invoiced, 0, 'Nothing should be invoiced')
            self.assertEqual(rec_line.qty_delivered, 1)

        with freeze_time("2022-04-02"):
            inv = sub._create_recurring_invoice()
            self.assertTrue(inv)
            self.assertEqual(sub.next_invoice_date, datetime.date(2022, 5, 1))
            self.assertEqual(rec_line.invoice_lines.deferred_start_date, datetime.date(2022, 3, 1))
            self.assertEqual(rec_line.invoice_lines.deferred_end_date, datetime.date(2022, 3, 31))
            self.assertEqual(rec_line.last_invoiced_date, datetime.date(2022, 3, 31))
            self.assertEqual(rec_line.qty_invoiced, 0, 'One product should be invoiced in the previous period')
            self.assertEqual(len(rec_line.move_ids), 2, 'One move should be created')
            self.assertEqual(len(inv), 1)
            self.assertEqual(len(sub.picking_ids), 2)

        with freeze_time("2022-04-15"):
            self.validate_picking_moves(sub.picking_ids)
            self.assertEqual(sub.order_line.qty_delivered, 1)
            self.assertEqual(sub.order_line.qty_to_deliver, 0)

        invoice, picking = self.simulate_period(sub, "2022-05-2")
        self.assertTrue(picking)
        self.assertTrue(invoice)
        self.assertEqual(len(invoice.invoice_line_ids), 1, 'We should invoice the recurring line lines')
        self.assertEqual(invoice.amount_total, 45,
                         'Invoice price should be the 1 month pricing')
        self.assertEqual(picking.move_ids.product_id, self.sub_product_order,
                         'We should only deliver the recurring product')

        invoice, picking = self.simulate_period(sub, "2022-06-03")
        self.assertTrue(invoice)
        self.assertTrue(picking)
        self.assertEqual(len(invoice.invoice_line_ids), 1, 'We should invoice the recurring line')
        self.assertEqual(invoice.amount_total, 45, 'Invoice price should be the 1 month pricing')
        self.assertEqual(picking.move_ids.product_id, self.sub_product_order,
                         'We should only deliver the recurring product')

        invoice, picking = self.simulate_period(sub, "2022-07-04")

        self.assertEqual(len(invoice.invoice_line_ids), 1, 'We should invoice the recurring line')
        self.assertEqual(invoice.amount_total, 45, 'Invoice price should be the 1 month pricing')
        self.assertEqual(picking.move_ids.product_id, self.sub_product_order,
                         'We should only deliver the recurring product')

    def test_prepaid_qty_computation(self):
        """
        Several cases:
        1) Today is in the middle of the 1st INVOICED period
            a) The product is already delivered
            b) The product is still not delivered
        2) Today is in the 2nd period that is NOT YET invoiced
            a) The 1st period product was delivered after the invoicing period but before today
            b) The 1st period product is still not delivered
        3) Today is in the 2nd INVOICED period
            a) The 1st and 2nd period products have been delivered (both in the 2nd period)
            b) The 1st and 2nd period products are still not delivered
        """

        with freeze_time("2023-01-01"):
            self.product.invoice_policy = 'order'
            self.product.type = 'service'
            self.sub_product_order.invoice_policy = 'order'
            self.sub_product_order.type = 'consu'
            sub_temp = self.env['sale.order'].create({
                'name': 'Order',
                'is_subscription': True,
                'partner_id': self.user_portal2.partner_id.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1,
                        'tax_id': [Command.clear()],
                    }),
                    Command.create({
                        'product_id': self.sub_product_order.id,
                        'product_uom_qty': 1,
                        'tax_id': [Command.clear()],
                    }),
                ]
            })

            # --------- Start Case 1 --------- #
            sub = sub_temp.copy()
            sub.action_confirm()
            self.env['sale.order']._create_recurring_invoice()

        with freeze_time("2023-01-05"):
            # case 1.b
            res = self._get_quantities(sub.order_line)
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [0, 0])
            self.assertEqual(res['invoiced'], [1, 1])
            self.assertEqual(res['to_invoice'], [0, 0])

        with freeze_time("2023-01-10"):
            self.validate_picking_moves(sub.picking_ids)
            sub.order_line[0].qty_delivered = 1
            # case 1.a
            res = self._get_quantities(sub.order_line)
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [1, 1])
            self.assertEqual(res['invoiced'], [1, 1])
            self.assertEqual(res['to_invoice'], [0, 0])

        # --------- Start Case 2 --------- #

        with freeze_time("2023-01-1"):
            sub = sub_temp.copy()
            sub.action_confirm()
            self.env['sale.order']._create_recurring_invoice()
            self.assertTrue(sub.next_invoice_date, datetime.date(2023, 2, 1))

        with freeze_time("2023-02-15"):
            # case 2.b
            res = self._get_quantities(sub.order_line)  # February was NOT invoiced, `res` represents January's data
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [0, 0])
            # self.assertEqual(res['invoiced'], [0, 0]) # --> Impossible
            # self.assertEqual(res['to_invoice'], [1, 1]) # --> Impossible

        with freeze_time("2023-02-25"):
            # case 2.a
            self.validate_picking_moves(sub.picking_ids)
            sub.order_line[0].qty_delivered = 1

            res = self._get_quantities(sub.order_line)  # February was NOT invoiced, `res` represents January's data
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [1, 1])
            self.assertEqual(res['invoiced'], [1, 1])
            self.assertEqual(res['to_invoice'], [0, 0])

        # --------- Start Case 3 --------- #

        with freeze_time("2023-01-01"):
            sub = sub_temp.copy()
            sub.action_confirm()
            self.env['sale.order']._create_recurring_invoice()
            self.assertTrue(sub.next_invoice_date, datetime.date(2023, 2, 1))

        with freeze_time("2023-02-01"):
            self.env['sale.order']._create_recurring_invoice()

        with freeze_time("2023-02-15"):
            # case 3.b
            res = self._get_quantities(sub.order_line)  # February has been invoiced, `res` represents February's data
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [0, 0], "products are not yet delivered")
            self.assertEqual(res['invoiced'], [1, 1])
            self.assertEqual(res['to_invoice'], [0, 0])

        with freeze_time("2023-02-25"):
            # case 3.a
            self.validate_picking_moves(sub.picking_ids)  # Deliver January's and February's products
            sub.order_line[0].qty_delivered = 1

            res = self._get_quantities(sub.order_line)  # February has been invoiced, `res` represents February's data
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [1, 1])
            self.assertEqual(res['invoiced'], [1, 1])
            self.assertEqual(res['to_invoice'], [0, 0])

    def test_postpaid_qty_computation(self):
        """"
        Several cases:
        1) Today is at the next invoice date. Previous period was already invoiced but we need to invoice today
            a) The product has been delivered during the period to invoice
            b) The product has not been delivered yet
        2) Today is The next invoice date but we are are 2 recurrence away from the last invoiced period.
           a) Product were delivered during last period but it was not invoiced
           b) Product were not delivered during last period and it was not invoiced
        """
        with freeze_time("2023-01-01"):
            self.product.invoice_policy = 'delivery'
            self.sub_product_order.invoice_policy = 'delivery'
            sub_temp = self.env['sale.order'].create({
                'name': 'Order',
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'plan_id': self.plan_month.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product.id,
                        'product_uom_qty': 1,
                        'tax_id': [Command.clear()],
                    }),
                    Command.create({
                        'product_id': self.sub_product_order.id,
                        'product_uom_qty': 1,
                        'tax_id': [Command.clear()],
                    }),
                ]
            })
            sub = sub_temp.copy()
            sub.action_confirm()
            self.env['sale.order']._create_recurring_invoice()
            # SETUP
            res = self._get_quantities(sub.order_line)
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [0, 0])
            self.assertEqual(res['invoiced'], [0, 0])
            self.assertEqual(res['to_invoice'], [0, 0])

        with freeze_time("2023-01-10"):
            self.validate_picking_moves(sub.picking_ids)
            sub.order_line[0].qty_delivered = 1
            # SETUP
            res = self._get_quantities(sub.order_line)
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [1, 1])
            self.assertEqual(res['invoiced'], [0, 0])
            self.assertEqual(res['to_invoice'], [1, 1])

        with freeze_time("2023-02-10"):
            res = self._get_quantities(sub.order_line)
            self.assertEqual(res['ordered'], [1, 1])
            self.assertEqual(res['delivered'], [1, 1])
            self.assertEqual(res['invoiced'], [0, 0])
            self.assertEqual(res['to_invoice'], [1, 1])

    def test_sale_order_with_downpayment_and_picking(self):
        """
        Test case to verify the creation of downpayment and full invoices for a sale order with pickings.
        This test ensures that pickings are created when the sale order is confirmed. It also validates the creation of a 50%
        downpayment invoice and a full invoice for the sale order. The test checks the absence of new pickings for the downpayment invoice.
        """

        sub = self.subscription_order
        with freeze_time("2022-03-02"):
            self.assertTrue(sub.picking_ids, "Pickings should be created when the sale order is confirmed")
            initial_picking_count = len(sub.picking_ids)

            self.assertEqual(sub.picking_ids.state, 'done', "Initial picking should be in 'done' state")

            # Create a 50% downpayment invoice
            downpayment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
                'advance_payment_method': 'percentage',
                'amount': 50,
            })
            downpayment.create_invoices()

            self.assertEqual(len(sub.invoice_ids), 1, "Downpayment invoice should be created")
            downpayment_invoice = sub.invoice_ids

            self.assertAlmostEqual(downpayment_invoice.amount_total, sub.amount_total * 0.5, places=2,
                                    msg="Downpayment invoice amount should be 50% of the sale order total")

            # Post the downpayment invoice
            downpayment_invoice.action_post()
            self.assertEqual(downpayment_invoice.state, 'posted', "Downpayment invoice should be in 'posted' state")
            self.assertEqual(len(sub.picking_ids), initial_picking_count,
                            "No new picking should be created for the downpayment invoice")

            # Create a full invoice
            payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({})
            payment.create_invoices()

            self.assertEqual(len(sub.invoice_ids), 2, "Full invoice should be created")

            full_invoice = sub.invoice_ids.filtered(lambda inv: inv.state == 'draft')
            self.assertEqual(len(full_invoice), 1, "There should be one draft invoice")
            self.assertAlmostEqual(
                    full_invoice.amount_total, sub.amount_total - downpayment_invoice.amount_total, places=2,
                    msg="Full invoice amount should be the remaining 50% of the sale order total")

            # Post the full invoice
            full_invoice.action_post()
            self.assertEqual(full_invoice.state, 'posted', "Full invoice should be in 'posted' state")
            self.assertEqual(len(sub.picking_ids), initial_picking_count, "No new picking should be created for the full invoice")
            self.assertTrue(sub.invoice_status == 'invoiced', "The sale order should be fully invoiced")

    def test_sale_order_with_deliveries_and_invoices(self):
        """
        Test case to verify the creation of invoices and pickings for a sale order with deliveries.
        This test ensures that pickings are created when the sale order is confirmed. It validates the creation
        of the first and second invoices, along with their states. The test also confirms the creation of a new picking
        for the second invoice.
        """

        sub = self.subscription_order
        with freeze_time("2022-03-02"):
            self.assertTrue(sub.picking_ids, "Pickings should be created when the sale order is confirmed")
            initial_picking_count = len(sub.picking_ids)
            self.assertEqual(sub.picking_ids.state, 'done', "Initial picking should be in 'done' state")

            # Create the first invoice
            first_invoice, picking = self.simulate_period(sub, "2022-03-02")

            self.assertEqual(first_invoice.state, 'posted', "First invoice should be in 'posted' state")
            self.assertEqual(len(sub.picking_ids), initial_picking_count, "No new picking should be created for the first invoice")

            # Create the second invoice
            second_invoice, picking = self.simulate_period(sub, "2022-04-02")
            self.assertEqual(len(sub.invoice_ids), 2, "Second invoice should be created")
            self.assertEqual(second_invoice.state, 'posted', "Second invoice should be in 'posted' state")

            # Ensure a new picking is created for the second invoice
            self.assertEqual(len(sub.picking_ids), initial_picking_count + 1, "A new picking should be created for the second invoice")
            self.assertEqual(picking.state, 'done', "New picking should be in 'done' state")

    def test_forecast_renewed_subscription_stock(self):
        product = self.env['product.product'].create({
            'name': "Storable product",
            'standard_price': 0.0,
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'invoice_policy': 'order',
            'recurring_invoice': True,
        })

        subscription = self.env['sale.order'].create({
            'name': 'Original Subscription',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 1,
            })]
        })

        subscription.action_confirm()
        subscription._cron_recurring_create_invoice()
        action = subscription.prepare_renewal_order()
        renewal_so = self.env['sale.order'].browse(action['res_id'])
        renewal_so.action_confirm()

        forecast_data = self.env['stock.forecasted_product_product']._get_report_data(product_ids=[product.id])
        self.assertEqual(forecast_data['subscription_qty'], 1, 'Renewed subscription should no longer require stock')

    def test_cron_product_multiple_delivery_creation(self):
        """This check ensures that the cron creates the deliveries for all subscriptions """
        self.storable_product = self.env['product.product'].create({
            'name': 'Storable Product',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'recurring_invoice': True,
        })

        def create_subscription(name):
            sub = self.env['sale.order'].create({
                'name': name,
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'plan_id': self.plan_month.id,
                'start_date': "2024-10-01",
                'next_invoice_date': False,
                'order_line': [Command.create({'product_id': self.storable_product.id, 'product_uom_qty': 1})]
            })
            sub.action_confirm()
            return sub

        subscription_order_1 = create_subscription("Order 1")
        subscription_order_2 = create_subscription("Order 2")

        # Use freeze_time to not rely in "today's" date.
        with freeze_time("2024-11-15"):
            self.env["sale.order"]._create_recurring_invoice()

        move_1 = subscription_order_1.order_line.move_ids
        move_2 = subscription_order_2.order_line.move_ids
        self.assertTrue(bool(move_1))
        self.assertTrue(bool(move_2))

    def test_picking_done_in_another_period(self):
        """ In this test, we trigger 2 periods the same day.
            The goal is to ensure that the picking of the first period does not interfere with the second period.
            It happened when the first period picking was validated in the second period.
            Then, when you triggered the second period, it would find one picking already done,
            and skip the picking creation.
        """

        self.storable_product = self.env['product.product'].create({
            'name': 'Storable Product',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'recurring_invoice': True,
        })
        self.inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.storable_product.id,
            'product_tmpl_id': self.storable_product.product_tmpl_id.id,
            'new_quantity': 100.0,
        })
        self.inventory_wizard.change_product_qty()

        sub = self.env['sale.order'].create({
            'name': "Order",
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'start_date': "2024-10-01",
            'next_invoice_date': False,
            'order_line': [Command.create({'product_id': self.storable_product.id, 'product_uom_qty': 1})]
        })
        self.assertEqual(self.storable_product.invoice_policy, "order", "The product is invoiced on ordered quantity")
        self.assertFalse(sub.order_line._is_postpaid_line(), "The line is invoiced at the beginning of the period")

        with freeze_time("2024-11-15"):
            sub.action_confirm()
            self.assertEqual(sub.next_invoice_date, datetime.date(2024, 10, 1))
            # Period = "2024-10-01" -> "2024-10-31"
            first_picking = sub.picking_ids
            self.assertTrue(first_picking)
            first_picking.move_ids.write({'quantity': 1, 'picked': True})
            first_picking.button_validate()
            quantity_delivered = sum(sub.order_line.move_ids.mapped("quantity"))
            self.assertEqual(quantity_delivered, 1)
            # start the cron once, it will increment the next invoice date but no new picking is created
            self.env["sale.order"]._create_recurring_invoice()
            self.assertEqual(sub.next_invoice_date, datetime.date(2024, 11, 1))
            other_picking = sub.picking_ids - first_picking
            self.assertFalse(other_picking, "No new picking should be created for the first period")

        with freeze_time("2024-11-16"):
            # the next day, the cron run again and as the next invoice_date is passed, we process the order
            self.env["sale.order"]._create_recurring_invoice()
            self.assertEqual(sub.next_invoice_date, datetime.date(2024, 12, 1))

            # Period = "2024-11-01" -> "2024-11-30"
            second_picking = sub.picking_ids - first_picking
            self.assertTrue(second_picking, "new picking should be created")
            second_picking.move_ids.write({'quantity': 1, 'picked': True})
            second_picking.button_validate()
            quantity_delivered = sum(sub.order_line.move_ids.mapped("quantity"))
            self.assertEqual(quantity_delivered, 2)

    def test_sale_order_with_passed_start_date(self):
        self.storable_product = self.env['product.product'].create({
            'name': 'Storable Product',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'recurring_invoice': True,
        })
        self.inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.storable_product.id,
            'product_tmpl_id': self.storable_product.product_tmpl_id.id,
            'new_quantity': 100.0,
        })
        self.inventory_wizard.change_product_qty()

        sub = self.env['sale.order'].create({
            'name': "Order",
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'start_date': "2024-10-01",
            'next_invoice_date': False,
            'order_line': [Command.create({'product_id': self.storable_product.id, 'product_uom_qty': 1})]
        })

        with freeze_time("2024-10-05"):
            sub.action_confirm()

            picking = sub.picking_ids
            self.assertTrue(bool(picking))
            self.assertEqual(picking.date_deadline, datetime.datetime(2024, 10, 31), "The delivery deadline should be set to the end of the period.")

    def test_sale_order_with_future_start_date(self):
        self.storable_product = self.env['product.product'].create({
            'name': 'Storable Product',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'recurring_invoice': True,
        })
        self.inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.storable_product.id,
            'product_tmpl_id': self.storable_product.product_tmpl_id.id,
            'new_quantity': 100.0,
        })
        self.inventory_wizard.change_product_qty()

        sub = self.env['sale.order'].create({
            'name': "Order",
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'start_date': "2024-11-06",
            'next_invoice_date': False,
            'order_line': [Command.create({'product_id': self.storable_product.id, 'product_uom_qty': 1})]
        })

        with freeze_time("2024-10-05"):
            sub.action_confirm()

            picking = sub.picking_ids
            self.assertTrue(bool(picking))
            self.assertEqual(picking.date_deadline, datetime.datetime(2024, 12, 5), "The delivery deadline should be set to the end of the period.")

    def test_sale_order_with_different_start_and_invoice_dates(self):
        self.storable_product = self.env['product.product'].create({
            'name': 'Storable Product',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'recurring_invoice': True,
        })
        self.inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.storable_product.id,
            'product_tmpl_id': self.storable_product.product_tmpl_id.id,
            'new_quantity': 100.0,
        })
        self.inventory_wizard.change_product_qty()

        sub = self.env['sale.order'].create({
            'name': "Order",
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'start_date': "2024-10-01",
            'next_invoice_date': "2024-10-02",
            'order_line': [Command.create({'product_id': self.storable_product.id, 'product_uom_qty': 1})]
        })

        with freeze_time("2024-10-05"):
            sub.action_confirm()

            picking = sub.picking_ids
            self.assertTrue(bool(picking))
            self.assertEqual(picking.date_deadline.date(), datetime.date(2024, 10, 1), "The delivery deadline should be set to the end of the period.")

    def test_qty_delivered_with_respect_to_first_delivery(self):
        """
        Check that the qty delivered is correctly computed with respect
        to the delivery generated at confirmation of the subscription.
        """
        subscription = self.subscription_delivery
        self.assertEqual(subscription.order_line.qty_delivered, 1.0)
        # create the related invoice manually
        account_move = subscription._create_invoices()
        self.assertRecordValues(account_move, [{'invoice_origin': 'Delivery', 'amount_total': subscription.order_line.price_total, 'state': 'draft'}])

    def test_post_invoice_hook_exception_handler(self):
        """Check that the _handle_post_invoice_hook_exception correctly creates a warning activity
        for the subscription with stock to deliver, and do nothing for the others.
        """
        self.storable_product = self.env['product.product'].create({
            'name': 'Storable Product',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'recurring_invoice': True,
        })
        self.service_product = self.env['product.product'].create({
            'name': 'Service Product',
            'type': 'service',
            'recurring_invoice': True,
        })

        with freeze_time("2024-10-01"):
            sub_stock_invoiced = self.env['sale.order'].create({
                'name': "Order With Delivery",
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'plan_id': self.plan_month.id,
                'start_date': "2024-10-01",
                'next_invoice_date': False,
                'order_line': [Command.create({'product_id': self.storable_product.id, 'product_uom_qty': 1})]
            })
            sub_service = self.env['sale.order'].create({
                'name': "Order",
                'is_subscription': True,
                'partner_id': self.user_portal.partner_id.id,
                'plan_id': self.plan_month.id,
                'start_date': "2024-10-01",
                'next_invoice_date': False,
                'order_line': [Command.create({'product_id': self.service_product.id, 'product_uom_qty': 1})]
            })

            (sub_stock_invoiced | sub_service).action_confirm()
            self.env["sale.order"]._create_recurring_invoice()
            # Trigger the exception handler as no exception really happened
            (sub_stock_invoiced | sub_service)._handle_post_invoice_hook_exception()

        # Subscription was invoiced, and a delivery should be created,
        # so a warning activity should have been created by the handler
        self.assertEqual(len(sub_stock_invoiced.activity_ids), 1)
        self.assertEqual(sub_stock_invoiced.activity_type_id.id, self.env.ref('mail.mail_activity_data_warning').id)

        # The subscription only has service product, no delivery needed to be created anyway,
        # no activity should have been created
        self.assertEqual(len(sub_service.activity_ids), 0)

    def test_subscription_return_qty_delivered(self):
        sub = self.subscription_order

        _invoice1, picking1 = self.simulate_period(sub, "2022-03-02", move_qty=3)
        self.assertEqual(sub.order_line.qty_delivered, 3)

        # return 2 qty
        stock_return_picking_form = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=picking1.ids,
                active_id=picking1.ids[0],
                active_model='stock.picking'
            )
        )
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 2.0
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        self.assertEqual(sub.order_line.qty_delivered, 3)
        return_picking.button_validate()

        self.assertEqual(return_picking.state, 'done')
        self.assertEqual(sub.order_line.qty_delivered, 1, 'Qty delivered for the period should be reduced')

        # reverse part of the return
        stock_return_picking_form_2 = Form(
            self.env['stock.return.picking'].with_context(
                active_ids=return_picking.ids,
                active_id=return_picking.ids[0],
                active_model='stock.picking'
            )
        )
        stock_return_picking_2 = stock_return_picking_form_2.save()
        stock_return_picking_2.product_return_moves.quantity = 1.0
        stock_return_picking_action_2 = stock_return_picking_2.action_create_returns()
        return_picking_2 = self.env['stock.picking'].browse(stock_return_picking_action_2['res_id'])
        return_picking_2.button_validate()
        self.assertEqual(sub.order_line.qty_delivered, 2, 'Qty delivered for the period should be increased')
