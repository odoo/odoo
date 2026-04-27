# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.fields import Command, Datetime, Date
from odoo.tests import Form, tagged

from odoo.addons.sale_stock_renting.tests.test_rental_common import TestRentalCommon


@tagged('post_install', '-at_install')
class TestRentalWizard(TestRentalCommon):

    def test_unavailable_qty_only_considers_active_rentals(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        # Ends before interval
        self._create_so_with_sol(
            rental_start_date=from_date - relativedelta(days=2),
            rental_return_date=from_date - relativedelta(days=1),
            product_uom_qty=1,
        )
        # Starts after interval
        self._create_so_with_sol(
            rental_start_date=to_date + relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=2),
            product_uom_qty=1,
        )
        # Ends during interval
        self._create_so_with_sol(
            rental_start_date=from_date - relativedelta(days=1),
            rental_return_date=to_date - relativedelta(days=1),
            product_uom_qty=1,
        )
        # Starts during interval
        self._create_so_with_sol(
            rental_start_date=from_date + relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=1),
            product_uom_qty=1,
        )
        # Covers interval
        self._create_so_with_sol(
            rental_start_date=from_date - relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=1),
            product_uom_qty=1,
        )
        # Doesn't increase unavailable.
        self._create_so_with_sol(
            rental_start_date=to_date - relativedelta(days=1),
            rental_return_date=to_date,
            product_uom_qty=1,
        )

        self.assertEqual(self.product_id._get_unavailable_qty(from_date, to_date), 3)

    def test_unavailable_qty_with_to_date_exclude_pickup_at_to_date(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        # Starts at to_date
        self._create_so_with_sol(
            rental_start_date=to_date,
            rental_return_date=to_date + relativedelta(days=1),
            product_uom_qty=1,
        )

        self.assertEqual(self.product_id._get_unavailable_qty(from_date, to_date), 0)

    def test_unavailable_qty_without_to_date_include_pickup_at_from_date(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        # Starts at from_date == to_date
        self._create_so_with_sol(
            rental_start_date=from_date,
            rental_return_date=from_date + relativedelta(days=1),
            product_uom_qty=1,
        )

        self.assertEqual(self.product_id._get_unavailable_qty(from_date), 1)

    def test_unavailable_qty_early_pickup(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        # Starts after interval
        so = self._create_so_with_sol(
            rental_start_date=to_date + relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=2),
            product_uom_qty=1,
        )
        self._pickup_so(so)

        self.assertEqual(self.product_id._get_unavailable_qty(from_date, to_date), 1)

    def test_unavailable_qty_early_return(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        # Ends during interval
        so = self._create_so_with_sol(
            rental_start_date=from_date - relativedelta(days=1),
            rental_return_date=to_date - relativedelta(days=1),
            product_uom_qty=1,
        )
        self._pickup_so(so)
        self._return_so(so)

        self.assertEqual(self.product_id._get_unavailable_qty(from_date, to_date), 0)

    def test_unavailable_lots_only_considers_active_rentals(self):
        self._set_product_quantity(10)
        from_date = Datetime.now() + relativedelta(days=1)
        to_date = Datetime.now() + relativedelta(days=5)
        lot1, lot2, lot3, lot4 = self.env['stock.lot'].create([{
            'product_id': self.tracked_product_id.id,
            'company_id': self.env.company.id,
        } for _i in range(4)])

        # Active
        self._create_so_with_sol(
            rental_start_date=from_date,
            rental_return_date=to_date,
            product_uom_qty=1,
            pickedup_lot_ids=[Command.set([lot1.id, lot2.id])],
            returned_lot_ids=[Command.set([lot2.id])],
            reserved_lot_ids=[Command.set([lot3.id])],
        )
        # Inactive
        self._create_so_with_sol(
            rental_start_date=to_date + relativedelta(days=1),
            rental_return_date=to_date + relativedelta(days=2),
            product_uom_qty=1,
            pickedup_lot_ids=[Command.set([lot4.id])],
        )

        self.assertEqual(self.product_id._get_unavailable_lots(from_date, to_date), lot1 + lot3)

    def test_rental_product_flow(self):

        self.assertEqual(
            self.product_id.qty_available,
            4
        )

        self.order_line_id1.write({
            'product_uom_qty': 3
        })

        """
            Total Pickup
        """

        self.order_line_id1.write({
            'qty_delivered': 3
        })

        """ In sale order warehouse """
        self.assertEqual(
            self.product_id.with_context(
                warehouse_id=self.order_line_id1.order_id.warehouse_id.id,
                from_date=self.order_line_id1.reservation_begin,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            1
        )

        self.env.invalidate_all()
        """ In company internal rental location (in stock valuation but not in available qty) """
        self.assertEqual(
            self.product_id.with_context(
                location=self.env.company.rental_loc_id.id,
                from_date=self.order_line_id1.start_date,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            3
        )

        """ In company warehouses """
        self.assertEqual(
            self.product_id.qty_available,
            1
        )

        """ In company stock valuation """
        self.assertEqual(
            self.product_id.quantity_svl,
            4
        )

        ####################################
        # Cancel deliver then re-apply
        ####################################

        self.order_line_id1.write({'qty_delivered': 0})
        self.assertEqual(self.product_id.qty_available, 4)
        self.order_line_id1.write({'qty_delivered': 3})

        """
            Partial Return
        """

        self.order_line_id1.write({
            'qty_returned': 2
        })

        """ In sale order warehouse """
        self.assertEqual(
            self.product_id.with_context(
                warehouse_id=self.order_line_id1.order_id.warehouse_id.id
            ).qty_available,
            3
        )

        """ In company internal rental location (in stock valuation but not in available qty) """
        self.assertEqual(
            self.product_id.with_context(
                location=self.env.company.rental_loc_id.id,
                from_date=self.order_line_id1.start_date,
                to_date=self.order_line_id1.return_date,
            ).qty_available,
            1
        )

        """ In company warehouses """
        self.assertEqual(
            self.product_id.qty_available,
            3
        )

        """ In company stock valuation """
        self.assertEqual(
            self.product_id.quantity_svl,
            4
        )

        """
            Total Return
        """

        self.order_line_id1.write({
            'qty_returned': 3
        })

        self.assertEqual(
            self.product_id.qty_available,
            4.0
        )

    def test_rental_lot_flow(self):
        self.lots_rental_order.action_confirm()

        lots = self.env['stock.lot'].search([('product_id', '=', self.tracked_product_id.id)])
        rentable_lots = self.env['stock.lot']._get_available_lots(self.tracked_product_id)
        self.assertEqual(set(lots.ids), set(rentable_lots.ids))  # set is here to ensure that order wont break test

        self.order_line_id2.reserved_lot_ids += self.lot_id1
        self.order_line_id2.product_uom_qty = 1.0

        self.order_line_id2.pickedup_lot_ids += self.lot_id2

        # Ensure lots are unreserved if other lots are picked up in their place
        # and qty pickedup = product_uom_qty (qty reserved)
        self.assertEqual(self.order_line_id2.reserved_lot_ids, self.order_line_id2.pickedup_lot_ids)

    def test_rental_lot_concurrent(self):
        """The purpose of this test is to mimmic a concurrent picking of a rental product.
        As the same lot is applied to the sol twice, its qty_delivered should be 1.
        """
        so = self.lots_rental_order
        sol = self.order_line_id2
        lot = self.lot_id2

        sol.product_uom_qty = 1.0
        so.action_confirm()

        wizard_vals = so.action_open_pickup()
        for _i in range(2):
            wizard = self.env[wizard_vals['res_model']].with_context(wizard_vals['context']).create({
                'rental_wizard_line_ids': [
                    (0, 0, {
                        'order_line_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty_delivered': 1.0,
                        'pickedup_lot_ids':[Command.set([lot.id])],
                    })
                ]
            })
            wizard.apply()

        self.assertEqual(sol.qty_delivered, len(sol.pickedup_lot_ids), "The quantity delivered should not exceed the number of picked up lots")

        for _i in range(2):
            wizard = self.env[wizard_vals['res_model']].with_context(wizard_vals['context']).create({
                'rental_wizard_line_ids': [
                    (0, 0, {
                        'order_line_id': sol.id,
                        'product_id': sol.product_id.id,
                        'qty_returned': 1.0,
                        'returned_lot_ids':[Command.set([lot.id])],
                    })
                ]
            })
            wizard.apply()

        self.assertEqual(sol.qty_returned, len(sol.returned_lot_ids), "The quantity returned should not exceed the number of returned lots")

    def test_schedule_report(self):
        """Verify sql scheduling view consistency.

        One sale.order.line with 3 different lots (reserved/pickedup/returned)
        is represented by 3 sale.rental.schedule to allow grouping reservation information
        by stock.lot .

        Note that a lot can be pickedup (sol.pickedup_lot_ids) even if not reserved (sol.reserved_lot_ids).
        """
        self.order_line_id2.reserved_lot_ids = self.lot_id1
        # Avoid magic setting pickedup lots as reserved when full quantity has been pickedup
        self.order_line_id2.product_uom_qty = 2.0

        # Lot pickedup but not reserved.
        self.order_line_id2.pickedup_lot_ids = self.lot_id2

        self.assertEqual(
            self.env["sale.rental.schedule"].search_count([('lot_id', '=', self.lot_id2.id)]),
            1,
        )
        scheduling_recs = self.env["sale.rental.schedule"].search([
            ('order_line_id', '=', self.order_line_id2.id),
        ])
        self.assertEqual(
            len(scheduling_recs),
            2, # 1 reserved, 1 pickedup
        )
        self.assertEqual(
            scheduling_recs.mapped('report_line_status'),
            ["reserved", "pickedup"],
        )

        # More generic behavior:
        # 2 reserved, 2 pickedup, 1 returned
        self.order_line_id2.returned_lot_ids = self.lot_id2
        self.order_line_id2.pickedup_lot_ids += self.lot_id1
        self.env.invalidate_all()
        scheduling_recs = self.env["sale.rental.schedule"].search([
            ('order_line_id', '=', self.order_line_id2.id)
        ])
        self.assertEqual(
            len(scheduling_recs),
            2,
        )
        self.assertEqual(
            scheduling_recs.lot_id,
            self.lot_id1 + self.lot_id2,
        )
        self.assertEqual(
            scheduling_recs.mapped('report_line_status'),
            ["pickedup", "returned"],
        )

    def test_lot_accuracy_in_schedule(self):
        """ Schedule should only display lots that are associated with rental order lines """
        self.env.user.groups_id = [Command.link(self.env.ref('sale_stock_renting.group_rental_stock_picking').id)]
        self.env['res.company'].create_missing_rental_location()
        if self.env['ir.module.module'].search([('name', '=', 'purchase_stock'), ('state', '=', 'installed')], limit=1):
            self.env.user._get_default_warehouse_id().buy_to_resupply = False

        rental_schedule = self.env['sale.rental.schedule']
        so = self.lots_rental_order
        self.order_line_id2.product_uom_qty = 1.0
        so.order_line = [(6, 0, self.order_line_id2.id)]
        so.action_confirm()

        # Rental schedule should have 1 out of the 3 total lots for `self.tracked_product_id`
        self.assertEqual(
            rental_schedule.search_count([('product_id', '=', self.tracked_product_id.id)]),
            1
        )

    def test_lot_accuracy_in_schedule_multiple_rentals(self):
        """
            With rental transfers enabled, we check if the schedule shows
            all rentals after renting the same serial numbers multiple times.
        """
        rental_schedule = self.env['sale.rental.schedule']
        self.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()
        self.assertTrue(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        so = self.lots_rental_order
        so.company_id._create_rental_location()
        self.order_line_id2.product_uom_qty = 3.0
        so.write({'order_line': [self.order_line_id2.id]})
        so.action_confirm()
        so.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id).button_validate()

        # Rental schedule should have all 3 serial numbers appear for the current order
        self.assertEqual(
            rental_schedule.search_count([
                ('product_id', '=', self.tracked_product_id.id),
                ('order_line_id', 'in', so.order_line.ids)]),
            3
        )

        so.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.in_type_id).button_validate()
        so = so.copy()
        so.action_confirm()
        so.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id).button_validate()

        # Rental schedule should have all 3 serial numbers for both orders (6 total)
        self.assertEqual(
            rental_schedule.search_count([
                ('product_id', '=', self.tracked_product_id.id)]),
            6
        )

    @freeze_time('2025-01-01 09:10:15')
    def test_rental_forecast_with_rental_transfers(self):
        """
            With rental transfers enable, we check if the forecast rentable quantity takes
            incoming and outgoing moves happening prior to the rental period and other
            rental orders in its computation.
        """
        # Enable "rental transfers" and rely on the qty_in_rent fot the forecast
        self.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()
        self.assertTrue(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        product = self.env['product.product'].create({
            'name': 'Lovely Product',
            'is_storable': True,
            'rent_ok': True,
        })
        # Put 100 units in stock
        self.env['stock.quant']._update_available_quantity(product, self.warehouse_id.lot_stock_id, 101)

        delivery = self.env['stock.picking'].create({
            'name': "Lovely Delivery",
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'scheduled_date': Datetime.today() + timedelta(days=2),
            'move_ids': [Command.create({
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id':  self.ref('stock.stock_location_customers'),
                'name': 'Lovely product move',
                'product_id': product.id,
                'product_uom_qty': 20,
            })]
        })
        delivery.action_confirm()
        # Create 2 rental orders: one to confirmed
        sale_orders = self.env['sale.order'].create([
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=1),
                'rental_return_date': Datetime.today() + timedelta(days=2),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 8.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=4),
                'rental_return_date': Datetime.today() + timedelta(days=6),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 10.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=5),
                'rental_return_date': Datetime.today() + timedelta(days=7),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 20.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=6),
                'rental_return_date': Datetime.today() + timedelta(days=8),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 30.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=1),
                'rental_return_date': Datetime.today() + timedelta(days=10),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 1.0,
                })],
            },
        ])

        """
        The last SO is here to create a rental order covering the entire renting periods.
        In a picture the delivery and the other rental orders are intertwined as follows:

        |    1    |    2    |    3    |    4    |    5    |    6    |    7    |    8    |    9    |    10    |

                   -20[-----------------------------------------------------------------------------------

                                       -10[-----------------]

                                                -20[------------------]

                                                            -30[----------------]

        """

        sale_orders.order_line.update({'is_rental': True})
        so = sale_orders[0]
        (sale_orders - so).action_confirm()
        self.assertEqual(so.order_line.virtual_available_at_date, 100)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        # We need to invalidate the cache after each change since the qty_in_rent does not have
        # any dependence and hence will only be recomputed if it was not already set in cache
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 80)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4) + timedelta(hours=1),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 70)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=5),
        })
        product.invalidate_recordset()

        self.assertEqual(so.order_line.virtual_available_at_date, 70)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 50)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=6),
            'rental_return_date': Datetime.today() + timedelta(days=8),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)
        so.action_confirm()
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)
        so.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id).button_validate()
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)

    @freeze_time('2025-01-01 00:00:00')
    def test_rental_forecast_with_rental_transfers_and_preparation_time(self):
        """
            With rental transfers enable, we check if the forecast rentable quantity takes
            incoming and outgoing moves happening prior to the rental period as well as
            preparation_time.
        """
        # Enable "rental transfers" and rely on the qty_in_rent fot the forecast
        self.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()
        self.assertTrue(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        product = self.env['product.product'].create({
            'name': 'Lovely Product',
            'is_storable': True,
            'rent_ok': True,
            'preparation_time': 24.0,  # Add one day of preparation_time
        })
        # Put 100 units in stock
        self.env['stock.quant']._update_available_quantity(product, self.warehouse_id.lot_stock_id, 101)

        delivery = self.env['stock.picking'].create({
            'name': "Lovely Delivery",
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'scheduled_date': Datetime.today() + timedelta(days=1),
            'move_ids': [Command.create({
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id':  self.ref('stock.stock_location_customers'),
                'name': 'Lovely product move',
                'product_id': product.id,
                'product_uom_qty': 20,
            })]
        })
        delivery.action_confirm()
        # Create 2 rental orders: one to confirmed
        sale_orders = self.env['sale.order'].create([
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=1),
                'rental_return_date': Datetime.today() + timedelta(days=2),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 8.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=4),
                'rental_return_date': Datetime.today() + timedelta(days=6),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 10.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=5),
                'rental_return_date': Datetime.today() + timedelta(days=7),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 20.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=6),
                'rental_return_date': Datetime.today() + timedelta(days=8),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 30.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=1),
                'rental_return_date': Datetime.today() + timedelta(days=10),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 1.0,
                })],
            },
        ])
        sale_orders.order_line.update({'is_rental': True})

        """
        The last SO is here to create a rental order covering the entire renting periods.
        In a picture the delivery and the other rental orders are intertwined as follows:

        |    1    |    2    |    3    |    4    |    5    |    6    |    7    |    8    |    9    |    10    |

        -20[-------------------------------------------------------------------------------------------------

                            [~~~~ -10[--------------------]

                                      [~~~~ -20[-------------------]

                                                [~~~~ -30[-------------------]

        """

        so = sale_orders[0]
        (sale_orders - so).action_confirm()
        self.assertEqual(so.order_line.virtual_available_at_date, 100)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=2),
            'rental_return_date': Datetime.today() + timedelta(days=3),
        })
        # We need to invalidate the cache after each change since the qty_in_rent does not have
        # any dependence and hence will only be recomputed if it was not already set in cache
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 80)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=2),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        product.invalidate_recordset()

        self.assertEqual(so.order_line.virtual_available_at_date, 70)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=4),
            'rental_return_date': Datetime.today() + timedelta(days=5),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 50)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=6),
            'rental_return_date': Datetime.today() + timedelta(days=8),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 20)
        so.write({
            'rental_start_date': Datetime.today() + timedelta(days=7),
            'rental_return_date': Datetime.today() + timedelta(days=8),
        })
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)
        so.action_confirm()
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)
        so.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id).button_validate()
        product.invalidate_recordset()
        self.assertEqual(so.order_line.virtual_available_at_date, 30)

    def test_rental_forecast_without_rental_transfers(self):
        """
            With rental transfers disabled, we check if the forecast rentable quantity takes
            incoming and outgoing moves happening prior to the rental period and other
            rental orders in its computation.
        """
        # Disable "rental transfers" and rely on the qty_in_rent fot the forecast
        self.env['res.config.settings'].create({'group_rental_stock_picking': False}).execute()
        self.assertFalse(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        product = self.env['product.product'].create({
            'name': 'Lovely Product',
            'is_storable': True,
            'rent_ok': True,
        })
        # Put 100 units in stock
        self.env['stock.quant']._update_available_quantity(product, self.warehouse_id.lot_stock_id, 100)

        delivery = self.env['stock.picking'].create({
            'name': "Lovely Delivery",
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'scheduled_date': Datetime.today() + timedelta(days=3),
            'move_ids': [Command.create({
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id':  self.ref('stock.stock_location_customers'),
                'name': 'Lovely product move',
                'product_id': product.id,
                'product_uom_qty': 20,
            })]
        })
        delivery.action_confirm()
        # Create 2 rental orders: one to confirmed
        so1, so2 = self.env['sale.order'].create([
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=1),
                'rental_return_date': Datetime.today() + timedelta(days=2),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 5.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': Datetime.today() + timedelta(days=5),
                'rental_return_date': Datetime.today() + timedelta(days=6),
                'order_line': [Command.create({
                    'product_id': product.id,
                    'product_uom_qty': 10.0,
                })],
            },
        ])

        (so1 | so2).order_line.update({'is_rental': True})
        so2.action_confirm()
        self.assertFalse(so2.picking_ids)
        self.assertEqual(so1.order_line.virtual_available_at_date, 100)
        so1.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        # We need to invalidate the cache after each change since the qty_in_rent does not have
        # any dependence and hence will only be recomputed if it was not already set in cache
        product.invalidate_recordset()
        self.assertEqual(so1.order_line.virtual_available_at_date, 80)
        so1.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        product.invalidate_recordset()
        self.assertEqual(so1.order_line.virtual_available_at_date, 70)
        so1.write({
            'rental_start_date': Datetime.today() + timedelta(days=7),
            'rental_return_date': Datetime.today() + timedelta(days=8),
        })
        product.invalidate_recordset()
        self.assertEqual(so1.order_line.virtual_available_at_date, 80)

    def test_rental_forecast_without_rental_transfers_and_with_pickup(self):
        """Ensure correct virtual availability calculation when
        'Rental Transfers' are disabled.
        Scenario:
        - Create a storable rental product with 10 units in stock.
        - Disable the 'Rental Transfer' setting.
        - Create two rental orders for the same period:
            * Order A: 9 units
            * Order B: 1 unit
        - Confirm and pick up Order A.
        - Check that Order B still shows 1 unit available.
        Expected:
        - Virtual availability before any confirmation: 10
        - After confirming and picking up Order A: Order B should still show 1 available unit.
        """
        # Disable rental transfers
        self.env['res.config.settings'].create({'group_rental_stock_picking': False}).execute()
        self.assertFalse(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        self.env['stock.quant']._update_available_quantity(self.product_id, self.warehouse_id.lot_stock_id, 6)
        # Create 2 rental orders for the same period
        start = Datetime.today() + timedelta(days=1)
        end = start + timedelta(days=1)
        so1, so2 = self.env['sale.order'].create([
            {
                'partner_id': self.cust1.id,
                'rental_start_date': start,
                'rental_return_date': end,
                'order_line': [Command.create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': 9.0,
                })],
            },
            {
                'partner_id': self.cust1.id,
                'rental_start_date': start,
                'rental_return_date': end,
                'order_line': [Command.create({
                    'product_id': self.product_id.id,
                    'product_uom_qty': 1.0,
                })],
            },
        ])
        (so1 | so2).order_line.update({'is_rental': True})
        self.assertEqual(so2.order_line.virtual_available_at_date, 10)
        # Confirm Order A (9 units)
        so1.action_confirm()
        self.assertFalse(so1.picking_ids)
        self.assertTrue(so1.has_pickable_lines)
        # Check availability for Order B after confirming Order A
        so2.order_line.invalidate_recordset()
        self.assertEqual(so2.order_line.virtual_available_at_date, 1)
        # Simulate pickup of Order A
        pickup_action = so1.action_open_pickup()
        wizard = Form(self.env['rental.order.wizard'].with_context(pickup_action['context'])).save()
        with freeze_time(so1.order_line.start_date):
            wizard.apply()
        so2.order_line.invalidate_recordset()
        self.assertFalse(so1.has_pickable_lines)
        # Virtual availability should remain correct for Order B
        self.assertEqual(so2.order_line.virtual_available_at_date, 1)

    @freeze_time('2020-01-01')
    def test_reschedule_rental_order_with_rental_transfers(self):
        """
        Ensures that rescheduling a rental order will propagate the new
        schedule to the associated rental pickings.
        """
        # Enable "rental transfers" and rely on the qty_in_rent fot the forecast
        self.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()
        self.assertTrue(self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'))
        self.warehouse_id.write({
            'reception_steps': 'two_steps',
            'delivery_steps': 'pick_ship',
        })
        self.product_id.preparation_time = 24  # Add one day of preparation_time
        self.env['stock.quant']._update_available_quantity(self.product_id, self.warehouse_id.lot_stock_id, 10)
        today = Datetime.today()
        rental_order = self.env['sale.order'].with_context(in_rental_app=True).create({
            'partner_id': self.cust1.id,
            'rental_start_date': today,
            'rental_return_date': today + timedelta(days=5),
            'order_line': [Command.create({
                'product_id': self.product_id.id,
                'product_uom_qty': 5.0,
            })],
            'warehouse_id': self.warehouse_id.id,
        })
        rental_order.action_confirm()
        start_date, return_date = rental_order.rental_start_date, rental_order.rental_return_date
        self.assertRecordValues(rental_order.picking_ids.move_ids.sorted('date'), [
            {'location_id': self.warehouse_id.lot_stock_id.id, 'date': start_date, 'date_deadline': start_date},
            {'location_id': self.warehouse_id.company_id.rental_loc_id.id, 'date': return_date, 'date_deadline': return_date},
        ])
        pick_picking = rental_order.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.pick_type_id)
        pick_picking.move_ids.quantity = 3.0
        self.warehouse_id.pick_type_id.create_backorder = "always"
        pick_picking.button_validate()
        self.assertRecordValues(rental_order.picking_ids.move_ids.sorted(lambda m: (m.date, m.location_id.id, m.id)), [
            {'location_id': self.warehouse_id.lot_stock_id.id, 'date': start_date, 'date_deadline': start_date, 'state': 'done'},  # done pick for 3 units
            {'location_id': self.warehouse_id.lot_stock_id.id, 'date': start_date, 'date_deadline': start_date, 'state': 'assigned'},  # pick for 2 units
            {'location_id': self.warehouse_id.wh_output_stock_loc_id.id, 'date': start_date, 'date_deadline': start_date, 'state': 'assigned'},  # ship for 3 units
            {'location_id': self.warehouse_id.company_id.rental_loc_id.id, 'date': return_date, 'date_deadline': return_date, 'state': 'waiting'},  # return for 5 units
        ])
        new_start_date = rental_order.rental_start_date + timedelta(days=8)
        new_return_date = rental_order.rental_return_date + timedelta(days=10)
        rental_order.write({
            'rental_start_date': new_start_date,
            'rental_return_date': new_return_date,
        })
        self.assertRecordValues(rental_order.picking_ids.move_ids.sorted(lambda m: (m.date, m.location_id.id, m.id)), [
            {'location_id': self.warehouse_id.lot_stock_id.id, 'date': start_date, 'date_deadline': start_date, 'state': 'done'},  # done pick for 3 units
            {'location_id': self.warehouse_id.lot_stock_id.id, 'date': new_start_date, 'date_deadline': new_start_date, 'state': 'assigned'},  # pick for 2 units
            {'location_id': self.warehouse_id.wh_output_stock_loc_id.id, 'date': new_start_date, 'date_deadline': new_start_date, 'state': 'assigned'},  # ship for 3 units
            {'location_id': self.warehouse_id.company_id.rental_loc_id.id, 'date': new_return_date, 'date_deadline': new_return_date, 'state': 'waiting'},  # return for 5 units
        ])

    ###############################
    #       PRIVATE METHODS       #
    ###############################

    def _set_product_quantity(self, quantity):
        quant = self.env['stock.quant'].create({
            'product_id': self.product_id.id,
            'inventory_quantity': quantity,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        quant.action_apply_inventory()

    def _create_so_with_sol(self, rental_start_date, rental_return_date, **sol_values):
        so = self.env['sale.order'].with_context(in_rental_app=True).create({
            'partner_id': self.cust1.id,
            'rental_start_date': rental_start_date,
            'rental_return_date': rental_return_date,
            'order_line': [
                Command.create({
                    'product_id': self.product_id.id,
                    **sol_values,
                })
            ]
        })
        so.action_confirm()
        return so

    def _pickup_so(self, so):
        pickup_action = so.action_open_pickup()
        Form(self.env['rental.order.wizard'].with_context(pickup_action['context'])).save().apply()

    def _return_so(self, so):
        return_action = so.action_open_return()
        Form(self.env['rental.order.wizard'].with_context(return_action['context'])).save().apply()


class TestRentalPicking(TestRentalCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['res.config.settings'].create({'group_rental_stock_picking': True}).execute()

    def test_disable_reenable(self):
        """ When disabling rental picking then re-enabling it, make sure that
        the route AND the rule(s) are unarchived. """
        warehouse_rental_route = self.env.ref('sale_stock_renting.route_rental')
        self.assertTrue(warehouse_rental_route.active)
        self.assertTrue(warehouse_rental_route.rule_ids)
        # disable setting
        self.env.user.groups_id -= self.env.ref('sale_stock_renting.group_rental_stock_picking')
        settings = self.env['res.config.settings'].with_user(self.env.user).create({})
        settings.group_rental_stock_picking = False
        settings.set_values()
        self.assertFalse(warehouse_rental_route.active)
        self.assertFalse(warehouse_rental_route.rule_ids)
        # re-enable setting
        settings.group_rental_stock_picking = True
        settings.with_context(active_test=False).set_values()
        self.assertTrue(warehouse_rental_route.active)
        self.assertTrue(warehouse_rental_route.rule_ids)

    def test_flow_1(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual(incoming_picking.return_id.id, outgoing_picking.id, "The return picking should be the return of the delivery picking")
        self.assertEqual([d.date() for d in (outgoing_picking | incoming_picking).mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [3.0, 3.0])

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')

        outgoing_picking.move_ids.quantity = 2
        Form.from_action(self.env, outgoing_picking.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 2)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 3)
        self.assertEqual(incoming_picking.move_ids.quantity, 2)

        incoming_picking.move_ids.quantity = 1
        Form.from_action(self.env, incoming_picking.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 4)

        outgoing_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'assigned')
        incoming_picking_2 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming' and p.state == 'assigned')
        self.assertEqual(outgoing_picking_2.scheduled_date.date(), rental_order_1.rental_start_date.date())
        self.assertEqual(incoming_picking_2.scheduled_date.date(), rental_order_1.rental_return_date.date())
        self.assertEqual(outgoing_picking_2.move_ids.quantity, 1)
        self.assertEqual(incoming_picking_2.move_ids.quantity, 1)

        rental_order_1.order_line.write({'product_uom_qty': 5})
        self.assertEqual(outgoing_picking_2.move_ids.product_uom_qty, 3)
        self.assertEqual(incoming_picking_2.move_ids.product_uom_qty, 4)

        outgoing_picking_2.move_ids.quantity = 1
        Form.from_action(self.env, outgoing_picking_2.button_validate()).save().process()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 3)
        self.assertEqual(rental_order_1.rental_status, 'pickup')
        self.assertEqual(len(rental_order_1.picking_ids), 5)
        self.assertEqual(incoming_picking_2.move_ids.quantity, 2)

        rental_order_1.order_line.write({'product_uom_qty': 4})
        outgoing_picking_3 = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing' and p.state == 'assigned')
        self.assertEqual(outgoing_picking_3.scheduled_date.date(), rental_order_1.rental_start_date.date())
        self.assertEqual(outgoing_picking_3.move_ids.product_uom_qty, 1)
        self.assertEqual(incoming_picking_2.move_ids.product_uom_qty, 3)

        outgoing_picking_3.button_validate()
        self.assertEqual(incoming_picking_2.move_ids.quantity, 3)
        self.assertEqual(rental_order_1.order_line.qty_delivered, 4)
        self.assertEqual(rental_order_1.rental_status, 'return')

        incoming_picking_2.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 4)
        self.assertEqual(rental_order_1.rental_status, 'returned')

    def test_flow_multisteps(self):
        self.warehouse_id.delivery_steps = 'pick_pack_ship'
        self.warehouse_id.reception_steps = 'three_steps'

        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual([d.date() for d in rental_order_1.picking_ids.mapped('scheduled_date')],
                         [rental_order_1.rental_start_date.date(), rental_order_1.rental_return_date.date()])
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [3.0, 3.0])

        rental_order_1.order_line.write({'product_uom_qty': 4})
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        self.assertEqual(rental_order_1.picking_ids.move_ids.mapped('product_uom_qty'), [4.0, 4.0])

        pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(pick_picking.location_dest_id, self.warehouse_id.wh_pack_stock_loc_id)
        pick_picking.button_validate()
        rental_order_1.order_line.write({'product_uom_qty': 1})
        self.assertEqual(len(rental_order_1.picking_ids), 4)

        return_pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.location_id == self.warehouse_id.wh_pack_stock_loc_id and p.location_dest_id == self.warehouse_id.lot_stock_id)
        all_other_pickings = rental_order_1.picking_ids.filtered(lambda p: p.state != 'done' and p.id != return_pick_picking.id)
        self.assertEqual(return_pick_picking.move_ids.product_uom_qty, 3.0)
        self.assertEqual(return_pick_picking.state, 'assigned')
        self.assertEqual(all_other_pickings.move_ids.mapped('product_uom_qty'), [1.0, 1.0])

        return_pick_picking.move_ids.picked = True
        return_pick_picking.button_validate()
        self.assertEqual(return_pick_picking.state, 'done')

        pack_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        pack_picking.move_ids.quantity = 1
        pack_picking.move_ids.picked = True
        self.assertEqual(pack_picking.location_dest_id, self.warehouse_id.wh_output_stock_loc_id)
        pack_picking.with_context(skip_backorder=True, picking_ids_not_to_backorder=pack_picking.ids).button_validate()

        out_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(out_picking.move_ids.location_dest_id, self.env.company.rental_loc_id)
        out_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 1)

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.location_dest_id, self.warehouse_id.wh_input_stock_loc_id)
        incoming_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 1)

        qc_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(qc_picking.location_dest_id, self.warehouse_id.wh_qc_stock_loc_id)
        qc_picking.button_validate()

        final_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(final_picking.location_dest_id, self.warehouse_id.lot_stock_id)
        final_picking.button_validate()

    def test_flow_multisteps_2(self):
        """ Checks that if a rental SO line quantity is changed multiple times, the expected return stays correct
        """
        self.warehouse_id.delivery_steps = 'pick_ship'
        self.warehouse_id.reception_steps = 'two_steps'

        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 4, 'is_rental': True})
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()

        # Validate the PICK, so it will create a return when reducing the quantity
        self.assertEqual(len(rental_order_1.picking_ids), 2)
        pick_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        pick_picking.button_validate()
        self.assertEqual(len(rental_order_1.picking_ids), 3)

        # Reduce then increase the rental quantity and checks that the expected qty to return remains correct
        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'incoming')
        rental_order_1.order_line.product_uom_qty = 2
        self.assertEqual(incoming_picking.move_ids.product_uom_qty, 2)
        rental_order_1.order_line.product_uom_qty = 3
        self.assertEqual(incoming_picking.move_ids.product_uom_qty, 3)

    def test_flow_serial(self):
        empty_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dofus Ocre",
            'company_id': self.env.company.id,
        })
        available_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dofawa",
            'company_id': self.env.company.id,
        })
        available_quant = self.env['stock.quant'].create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': available_lot.id,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        reserved_lot = self.env['stock.lot'].create({
            'product_id': self.tracked_product_id.id,
            'name': "Dolmanax",
            'company_id': self.env.company.id,
        })
        reserved_quant = self.env['stock.quant'].create({
            'product_id': self.tracked_product_id.id,
            'inventory_quantity': 1.0,
            'lot_id': reserved_lot.id,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id
        })
        (available_quant + reserved_quant).action_apply_inventory()

        # Reserve 1 serial
        reserved_rental = self.sale_order_id.copy()
        reserved_rental.order_line.write({'product_id': self.tracked_product_id.id, 'reserved_lot_ids': reserved_lot, 'product_uom_qty': 1})
        reserved_rental.order_line.is_rental = True
        reserved_rental.rental_start_date = self.rental_start_date
        reserved_rental.rental_return_date = self.rental_return_date
        reserved_rental.action_confirm()

        # Test with 3 serials: 1 available, 1 reserved and 1 empty
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({
            'product_id': self.tracked_product_id.id,
            'reserved_lot_ids': [Command.set((available_lot + reserved_lot + empty_lot).ids)],
            'product_uom_qty': 3,
        })
        rental_order_1.order_line.is_rental = True
        rental_order_1.rental_start_date = self.rental_start_date
        rental_order_1.rental_return_date = self.rental_return_date
        rental_order_1.action_confirm()
        self.assertEqual(len(rental_order_1.picking_ids), 2)

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(len(outgoing_picking.move_ids.move_line_ids), 3)
        self.assertEqual(outgoing_picking.move_ids.move_line_ids.lot_id, self.lot_id2 + self.lot_id3 + available_lot)

        outgoing_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_delivered, 3)
        self.assertEqual(available_lot.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)
        self.assertEqual(self.lot_id2.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)
        self.assertEqual(self.lot_id3.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.env.company.rental_loc_id)

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(len(incoming_picking.move_ids.move_line_ids), 3)
        self.assertEqual(incoming_picking.move_ids.move_line_ids.lot_id, self.lot_id2 + self.lot_id3 + available_lot)

        incoming_picking.button_validate()
        self.assertEqual(rental_order_1.order_line.qty_returned, 3)
        self.assertEqual(available_lot.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)
        self.assertEqual(self.lot_id2.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)
        self.assertEqual(self.lot_id3.quant_ids.filtered(lambda q: q.quantity == 1).location_id, self.warehouse_id.lot_stock_id)

    def test_late_fee(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.rental_start_date = Datetime.now() - timedelta(days=7)
        rental_order_1.rental_return_date = Datetime.now() - timedelta(days=3)
        rental_order_1.action_confirm()

        outgoing_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(outgoing_picking.scheduled_date.date(), rental_order_1.rental_start_date.date())
        outgoing_picking.button_validate()

        incoming_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        self.assertEqual(incoming_picking.scheduled_date.date(), rental_order_1.rental_return_date.date())
        incoming_picking.button_validate()

        self.assertEqual(len(rental_order_1.order_line), 2)
        late_fee_order_line = rental_order_1.order_line.filtered(lambda l: l.product_id.type == 'service')
        self.assertEqual(late_fee_order_line.price_unit, 30)

    def test_buttons(self):
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order_1.action_confirm()
        picking_out = rental_order_1.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        picking_in = rental_order_1.picking_ids - picking_out
        action_open_pickup = rental_order_1.action_open_pickup()
        action_open_return = rental_order_1.action_open_return()
        self.assertEqual(action_open_pickup.get('res_id'), picking_out.id)
        self.assertEqual(action_open_pickup.get('domain'), '')
        self.assertEqual(action_open_pickup.get('xml_id'), 'stock.action_picking_tree_all')
        self.assertEqual(action_open_return.get('res_id'), 0)
        self.assertEqual(action_open_return.get('domain'), [('id', 'in', rental_order_1.picking_ids.ids)])
        self.assertEqual(action_open_return.get('xml_id'), 'stock.action_picking_tree_all')

        ready_picking = rental_order_1.picking_ids.filtered(lambda p: p.state == 'assigned')
        ready_picking.button_validate()
        self.assertEqual(rental_order_1.rental_status, 'return')
        action_open_return_2 = rental_order_1.action_open_return()
        self.assertEqual(action_open_return_2.get('res_id'), picking_in.id)
        self.assertEqual(action_open_return_2.get('domain'), '')
        self.assertEqual(action_open_return_2.get('xml_id'), 'stock.action_picking_tree_all')

    def test_create_rental_transfers(self):
        """ E.g., a public/portal user signs & pays for an order via the portal
        """
        public_user = self.env.ref('base.public_user')
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.with_user(public_user).sudo().action_confirm()
        self.assertTrue(rental_order_1.picking_ids)

    def test_reordering_rule_forecast(self):
        """ Test the rental orders will only consider outgoing rental move in the forecast
        computation. """
        # Set a fixed visibility_days
        self.product_id.stock_quant_ids.sudo().unlink()
        date = Date.today() + timedelta(days=7)
        self.partner_1 = self.env['res.partner'].create({
            'name': 'Julia Agrolait',
            'email': 'julia@agrolait.example.com',
        })

        self.product_id.write({
            'seller_ids': [Command.create({'partner_id': self.partner_1.id, 'delay': 0})],
        })
        rental_order_1 = self.sale_order_id.copy()
        rental_order_1.order_line.write({'product_uom_qty': 1, 'is_rental': True})
        rental_order_1.rental_start_date = Datetime.now() + timedelta(days=2)
        rental_order_2 = self.sale_order_id.copy()
        rental_order_2.order_line.write({'product_uom_qty': 2, 'is_rental': True})
        rental_order_2.rental_start_date = Datetime.now() + timedelta(days=4)
        rental_order_2.rental_return_date = Datetime.now() + timedelta(days=5)
        self.assertEqual(self.product_id.with_context(date=date).qty_available, 0)
        (rental_order_1 | rental_order_2).action_confirm()
        self.env['stock.warehouse.orderpoint'].with_context(global_visibility_days=7).action_open_orderpoints()
        self.assertEqual(self.product_id.orderpoint_ids.with_context(global_visibility_days=7).lead_days_date, date)
        self.assertEqual(self.product_id.orderpoint_ids.with_context(global_visibility_days=7).qty_forecast, -2)

    def test_rental_available_reserved_lots(self):
        """
            The aim is to check if the `available_reserved_lots` compute
            field correctly determines whether a batch we want to reserve
            will be available or not.
        """
        # Create a sale order to reserve a lot.
        sale_order_id1 = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id1 = self.env['sale.order.line'].create({
            'order_id': sale_order_id1.id,
            'product_id': self.tracked_product_id.id,
            'reserved_lot_ids': [Command.set(self.lot_id1.ids)],
            'product_uom_qty': 1.0,
        })
        order_line_id1.update({'is_rental': True})
        sale_order_id1.action_confirm()

        # Create a second sale order and modify reserved lots, start date
        # and return date to check if `available_reserved_lots` is correct.
        sale_order_id = self.env['sale.order'].create({
            'partner_id': self.cust1.id,
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id = self.env['sale.order.line'].create({
            'order_id': sale_order_id.id,
            'product_id': self.tracked_product_id.id,
            'product_uom_qty': 1.0,
        })
        order_line_id.update({'is_rental': True})

        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids = self.lot_id2
        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids += self.lot_id1
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=1),
            'rental_return_date': Datetime.today() + timedelta(days=2),
        })
        self.assertEqual(order_line_id.available_reserved_lots, True)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        # will return in stock in time
        self.assertEqual(order_line_id.available_reserved_lots, True)

        # Validate the delivery of the first order to test the flow
        # when the product is not in stock
        delivery = sale_order_id1.picking_ids.filtered(lambda p: p.picking_type_id == self.warehouse_id.out_type_id)
        delivery.button_validate()
        self.assertEqual(delivery.state, 'done')
        self.assertEqual(delivery.move_ids.lot_ids, self.lot_id1)
        self.assertEqual(order_line_id1.available_reserved_lots, True)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=3),
            'rental_return_date': Datetime.today() + timedelta(days=4),
        })
        order_line_id.reserved_lot_ids = self.lot_id2
        self.assertEqual(order_line_id.available_reserved_lots, True)
        order_line_id.reserved_lot_ids += self.lot_id1
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=1),
            'rental_return_date': Datetime.today() + timedelta(days=2),
        })
        self.assertEqual(order_line_id.available_reserved_lots, False)
        sale_order_id.write({
            'rental_start_date': Datetime.today() + timedelta(days=5),
            'rental_return_date': Datetime.today() + timedelta(days=6),
        })
        self.assertEqual(order_line_id.available_reserved_lots, True)

    def test_disable_rental_transfer(self):
        """
        Check that the rental transfers setting can be disabled
        """
        warehouse_rental_route = self.env.ref('sale_stock_renting.route_rental')
        self.env['res.config.settings'].write({
            "group_rental_stock_picking": True,
        })
        rental_stock_rules = warehouse_rental_route.rule_ids
        rental_order = self.sale_order_id.copy()
        rental_order.order_line.write({'product_uom_qty': 3, 'is_rental': True})
        rental_order.action_confirm()
        picking_out = rental_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        picking_in = rental_order.picking_ids - picking_out
        self.assertEqual([len(picking_out), len(picking_in)], [1, 1])
        picking_out.button_validate()
        self.assertRecordValues(picking_out.move_ids, [{'state': 'done', 'quantity': 3.0}])
        picking_in.button_validate()
        self.assertRecordValues(picking_in.move_ids, [{'state': 'done', 'quantity': 3.0}])
        # disable the setting
        self.env.user.groups_id -= self.env.ref('sale_stock_renting.group_rental_stock_picking')
        settings = self.env['res.config.settings'].with_user(self.env.user).create({})
        settings.group_rental_stock_picking = False
        settings.set_values()
        # check that the rules of the rental route have been updated
        self.assertFalse(rental_stock_rules & warehouse_rental_route.rule_ids)

    def test_multi_step_route_revised_order_correct_transfer_amount(self):
        """ Ensure correct quantities are encoded on stock moves for rental transfers when an order
        gets revised and a multi-step route is used whose pick action sources product from a child
        location of lot_stock.
        """
        product = self.product_id
        warehouse = self.warehouse_id
        warehouse.delivery_steps = 'pick_ship'
        store_location = self.env['stock.location'].create({
            'name': 'storage location',
            'usage': 'internal',
            'location_id': warehouse.lot_stock_id.id,
        })
        warehouse.route_ids.filtered(
            lambda r: '2 steps' in r.name).rule_ids.filtered(
            lambda r: r.location_src_id == warehouse.lot_stock_id
        ).location_src_id = store_location.id

        rental_order = self.env['sale.order'].create({
            'is_rental_order': True,
            'partner_id': self.cust1.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': 1,
                'is_rental': True,
            })],
        })
        rental_order.action_confirm()
        rental_order.order_line[0].product_uom_qty = 2
        self.assertEqual(
            rental_order.picking_ids.move_ids.mapped('product_uom_qty'),
            [rental_order.order_line.product_uom_qty] * len(rental_order.picking_ids.move_ids)
        )

    def test_rental_transfer_custom_route(self):
        """
        Check that custom rental routes are used if set on the orde line.
        """
        # Enable rental transfers -> nrachive rental route
        self.env['res.config.settings'].write({
            "group_rental_stock_picking": True,
        })
        warehouse = self.warehouse_id
        warehouse_rental_route = self.env.ref('sale_stock_renting.route_rental')
        custom_rental_route = warehouse_rental_route.copy()
        custom_rental_route.sale_selectable = True
        custom_location = self.env['stock.location'].create({
            'name': 'Lovely location',
            'location_id': warehouse.lot_stock_id.id,
        })
        self.env['stock.rule'].create({
                'name': 'Custom rental delivery',
                'route_id': custom_rental_route.id,
                'location_dest_id': warehouse.company_id.rental_loc_id.id,
                'location_src_id': custom_location.id,
                'action': 'pull',
                'procure_method': 'make_to_stock',
                'picking_type_id': warehouse.out_type_id.id,
            })
        rental_order = self.sale_order_id.copy()
        rental_order.order_line.product_id.rent_ok = True
        rental_order.order_line.write({'product_uom_qty': 1, 'is_rental': True, 'route_id': custom_rental_route.id})
        rental_order.action_confirm()
        picking_out = rental_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        picking_in = rental_order.picking_ids - picking_out
        self.assertEqual([len(picking_out), len(picking_in)], [1, 1])
        self.assertRecordValues(picking_out.move_ids, [{
            'location_id': custom_location.id,
            'location_dest_id': warehouse.company_id.rental_loc_id.id,
            'route_ids': custom_rental_route.ids,
        }])
        self.assertRecordValues(picking_in.move_ids, [{
            'location_id': warehouse.company_id.rental_loc_id.id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'route_ids': custom_rental_route.ids,
        }])

    def _test_rental_order_with_mixed_lines(self, rental_first=True):
        """
        Helper function to test delivery behavior for rental orders with mixed lines.

        :param rental_first: Whether the rental product should appear first in the order lines.
        """
        rental_order = self.sale_order_id.copy()
        rental_line = rental_order.order_line[0]
        rental_line.write({'product_uom_qty': 2, 'is_rental': True})

        sales_product = self.env['product.product'].create({
            'name': 'Sales Product',
            'rent_ok': False,
        })
        sales_line = self.env['sale.order.line'].create({
            'order_id': rental_order.id,
            'product_id': sales_product.id,
            'product_uom_qty': 5,
            'is_rental': False
        })

        # Reorder lines if sales product is first
        if not rental_first:
            rental_product = rental_line.product_id
            rental_line.unlink()
            rental_line = self.env['sale.order.line'].create({
                'order_id': rental_order.id,
                'product_id': rental_product.id,
                'product_uom_qty': 2,
                'is_rental': True
            })

        rental_order.action_confirm()

        outgoing_picking = rental_order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        )
        self.assertEqual(len(outgoing_picking), 1)
        self.assertEqual(len(outgoing_picking.move_ids), 2)
        outgoing_picking.button_validate()

        self.assertEqual(
            sales_line.qty_delivered, 5,
            "Delivered quantity for sales product is incorrect."
        )
        self.assertEqual(
            rental_line.qty_delivered, 2,
            "Delivered quantity for rental product is incorrect."
        )
        self.assertEqual(
            outgoing_picking.move_ids.filtered(
                lambda m: m.product_id == sales_line.product_id
            ).location_dest_id,
            self.env.ref('stock.stock_location_customers')
        )
        self.assertEqual(
            outgoing_picking.move_ids.filtered(
                lambda m: m.product_id == rental_line.product_id
            ).location_dest_id,
            self.env.company.rental_loc_id
        )

        return_wizard = Form(self.env['stock.return.picking'].with_context(
            active_id=outgoing_picking.id,
            active_ids=outgoing_picking.ids,
            active_model='stock.picking'
        ))

        wizard = return_wizard.save()
        wizard.product_return_moves.quantity = 1
        res = wizard.action_create_returns()
        picking = self.env['stock.picking'].browse(res["res_id"])

        picking.button_validate()
        self.assertEqual(sales_line.qty_delivered, 4)

    def test_rental_order_containing_mixed_lines_1(self):
        """
            Test delivery behavior for rental order where the first line contains a rental product
            and the second line contains a sales product.
        """
        self._test_rental_order_with_mixed_lines(rental_first=True)

    def test_rental_order_containing_mixed_lines_2(self):
        """
            Test delivery behavior for rental order where the first line contains a sales product
            and the second line contains a rental product.
        """
        self._test_rental_order_with_mixed_lines(rental_first=False)

    def test_rental_purchase_mto(self):
        """ Test that renting an MTO product without stock correctly creates
        a PO and that the delivery picking effectively depends on it. """
        if 'purchase.order' not in self.env:
            self.skipTest('`purchase` is not installed')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        incoming_route = self.env.ref('purchase_stock.route_warehouse0_buy')
        seller = self.env['res.partner'].create({'name': 'Marty McScam'})
        mto_product = self.env['product.product'].create({
            'name': 'MTO Product',
            'type': 'consu',
            'is_storable': True,
            'rent_ok': True,
            'route_ids': [Command.set([mto_route.id, incoming_route.id])],
            'seller_ids': [Command.create({'partner_id': seller.id})]
        })

        rental_order = self.sale_order_id.copy()
        rental_order.order_line.write({'product_id': mto_product.id,'product_uom_qty': 3, 'is_rental': True, 'is_mto': True})
        rental_order.rental_start_date = self.rental_start_date
        rental_order.rental_return_date = self.rental_return_date
        rental_order.action_confirm()
        self.assertEqual(len(rental_order.picking_ids), 2)
        purchase = rental_order._get_purchase_orders()
        self.assertRecordValues(purchase, [{'state': 'draft', 'partner_id': seller.id}])
        self.assertRecordValues(purchase.order_line, [{
            'product_id': mto_product.id,
            'move_dest_ids': rental_order.picking_ids.move_ids[0].ids
        }])

    def test_rental_manufacture_mto(self):
        """ Test that renting an MTO product without stock correctly creates
        a MO and that the delivery picking effectively depends on it. """
        if 'mrp.production' not in self.env:
            self.skipTest('`mrp´ is not installed')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        incoming_route = self.env.ref('mrp.route_warehouse0_manufacture')
        mto_product = self.env['product.product'].create({
            'name': 'MTO Product',
            'type': 'consu',
            'is_storable': True,
            'rent_ok': True,
            'route_ids': [Command.set([mto_route.id, incoming_route.id])],
        })
        bom = self.env['mrp.bom'].create({'product_tmpl_id': mto_product.product_tmpl_id.id, 'product_id': mto_product.id})

        rental_order = self.sale_order_id.copy()
        rental_order.order_line.write({'product_id': mto_product.id,'product_uom_qty': 3, 'is_rental': True, 'is_mto': True})
        rental_order.rental_start_date = self.rental_start_date
        rental_order.rental_return_date = self.rental_return_date
        rental_order.action_confirm()
        self.assertEqual(len(rental_order.picking_ids), 2)
        production = rental_order.mrp_production_ids
        self.assertRecordValues(production, [{
            'state': 'draft',
            'bom_id': bom.id,
            'product_id': mto_product.id,
            'product_uom_qty': rental_order.order_line.product_uom_qty,
            'move_dest_ids': rental_order.picking_ids.move_ids[0].ids
        }])
