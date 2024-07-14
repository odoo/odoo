# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command, fields
from odoo.addons.sale_subscription_stock.tests.common_sale_subscription_stock import TestSubscriptionStockCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestSubscriptionStockOnOrder(TestSubscriptionStockCommon):

    def test_subscription_stock_order_base(self):
        """ Test invoice and picking order creation in case of one or multiple 'on_order'
            storable items in the subscription
        """
        sub = self.subscription_order

        with freeze_time("2022-03-02"):
            self.assertEqual(sub.invoice_count, 0, 'Until the first invoicing, we should not have invoiced anything')
            self.assertEqual(len(sub.picking_ids), 0,
                             'Until the first invoicing, we should not have created delivery for anything')
            self.env['sale.order']._cron_recurring_create_invoice()
            # Check that the invoice information are correct
            self.assertEqual(sub.invoice_count, 1, 'The automated action should have invoiced the first period')
            self.assertEqual(sub.order_line.qty_invoiced, 1, 'Order line should now be marked as invoiced')
            self.assertEqual(sub.invoice_ids.amount_total, 45)
            invoice_line = sub.invoice_ids.invoice_line_ids
            self.assertEqual(invoice_line.name.split('\n')[1], '03/02/2022 to 04/01/2022')
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
            self.assertEqual(move.quantity, 1)
            self.assertEqual(sub.order_line.qty_delivered, 0, 'Nothing should be delivered now')
            # Fulfil the delivery order
            move.write({'quantity': 1, 'picked': True})
            sub.picking_ids._action_done()
            self.assertEqual(move.quantity, 1, 'Move should be delivered now')
            self.assertEqual(sub.order_line.qty_delivered, 1, 'Order line should be marked as delivered')

    def test_subscription_stock_order_cron(self):

        sub = self.subscription_order

        # Simulate cron before start_date
        invoice, picking = self.simulate_period(sub, "2022-02-02")
        self.assertEqual(sub.invoice_count, 0, 'Subscription should have 0 invoices before start date')
        self.assertEqual(len(sub.picking_ids), 0, 'Subscription should have 0 delivery order before start date')

        for n_iter, date in enumerate(["2022-03-02", "2022-04-02", "2022-05-02", "2022-06-02"], 1):
            invoice, picking = self.simulate_period(sub, date)
            self.assertEqual(sub.invoice_count, n_iter, f'Subscription should have {n_iter} invoices at date {date}')
            self.assertEqual(len(sub.picking_ids), n_iter,
                             f'Subscription should have {n_iter} delivery order at date {date}')
            self.assertEqual(invoice.invoice_line_ids.quantity, 1, 'We should always invoice the same quantity')
            self.assertEqual(invoice.amount_total, 45, 'And the same amount')
            self.assertEqual(invoice.date.isoformat(), date, 'Invoice date should correspond to the current date')
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
        sub = self.subscription_order
        sub.order_line.product_uom_qty = 2
        self.assertEqual(len(sub.picking_ids), 0, 'Updating the quantity should not create a new delivery')

        invoice, picking = self.simulate_period(sub, "2022-03-02", move_qty=1)
        self.assertEqual(picking.move_ids.quantity, 1, 'Check that we under_delivered')
        self.assertEqual(invoice.invoice_line_ids.quantity, 2, 'We should invoice the quantity ordered')
        self.assertEqual(invoice.amount_total, 45 * 2, 'We should invoice the quantity ordered')

        back_order = sub.picking_ids - picking
        self.assertEqual(back_order.move_ids.product_uom_qty, 1, 'We should invoice the quantity ordered')

        invoice, picking = self.simulate_period(sub, "2022-04-02")
        self.assertEqual(invoice.invoice_line_ids.quantity, 2, 'We should invoice the ordered quantity')
        self.assertEqual(back_order.move_ids.mapped('product_uom_qty'), [1, 2],
                         'The new delivery should be added to the old one')

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
        self.assertEqual(sub.picking_ids.move_ids.product_id, self.test_product_order)

        # We deliver the non-recurring product
        sub.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        sub.picking_ids._action_done()

        invoice, picking = self.simulate_period(sub, "2022-03-02")
        self.assertEqual(len(invoice.invoice_line_ids), 2, 'We should invoice the 2 lines')
        self.assertEqual(invoice.amount_total, 45 + 1,
                         'Invoice price should be the 1 month pricing + 1$ for the non-recurring product')
        self.assertEqual(picking.move_ids.product_id, self.sub_product_order,
                         'We should only deliver the recurring product')

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
            'detailed_type': 'consu',
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
                'type': 'product',
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
            'type': 'product',
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
                len(self.subscription_order_with_bom.picking_ids[0].move_ids), 1,
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
                picking.move_ids[1].description_bom_line.__contains__(self.sub_product_order.name),
                'The description should contain the bom line name'
            )
            self.assertEqual(self.subscription_order_with_bom.order_line[0].product_id.qty_available, 98)

        # Return the delivery for the first period
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_picking.button_validate()
        self.assertEqual(return_picking.state, 'done')
        self.assertEqual(self.subscription_order_with_bom.order_line[0].product_id.qty_available, 100)
        self.assertEqual(
            len(picking.move_ids), len(first_invoice.invoice_line_ids), 'The invoice lines should match the moves'
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
                picking_1.move_ids[0].description_bom_line.__contains__(self.sub_product_order.name),
                'The description should contain the bom line name'
            )
            self.assertEqual(
                len(self.subscription_order_with_bom.picking_ids[1].move_ids), len(second_invoice.invoice_line_ids),
                'The move lines should match the moves of the second period'
            )
