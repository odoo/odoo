# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.addons.purchase_stock.tests.common import PurchaseTestCommon
from odoo.tests import tagged, freeze_time
from odoo.tests.common import HttpCase


@freeze_time("2021-01-14 09:12:15")
@tagged('post_install', '-at_install')
class TestPurchaseOrderSuggest(PurchaseTestCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a product and a supplier info.
        cls.product_1 = cls.env['product.product'].create({
            'name': 'Product 1',
            'standard_price': 115,
            'is_storable': True,
        })
        cls.env['product.supplierinfo'].create([{
            'partner_id': cls.partner_1.id,
            'price': 100,
            'product_id': cls.product_1.id,
        }])

    def assertEstimatedPrice(self, po_suggest, price, based_on='one_month', days=30, factor=100, warehouse=False):
        """ This helper method does an assert for the `purchase.order.suggest` wizard
        estimated price for the given parameters (use the default values if not set).
        Note that the wizard fields are updated each time this method is called."""
        po_suggest.based_on = based_on
        po_suggest.number_of_days = days
        po_suggest.percent_factor = factor
        po_suggest.warehouse_id = warehouse
        self.assertEqual(po_suggest.estimated_price, price)

    def _create_and_process_delivery_at_date(self, products_and_quantities, date=False, warehouse=False, to_validate=True):
        date = date or datetime.now()
        delivery_type = warehouse.out_type_id if warehouse else self.picking_type_out
        with freeze_time(date):
            delivery = self.env['stock.picking'].create({
                'picking_type_id': self.picking_type_out.id,
                'location_id': delivery_type.default_location_src_id.id,
                'location_dest_id': delivery_type.default_location_dest_id.id,
                'move_ids': [Command.create({
                    'location_id': delivery_type.default_location_src_id.id,
                    'location_dest_id': delivery_type.default_location_dest_id.id,
                    'product_id': product.id,
                    'product_uom': self.uom_unit.id,
                    'product_uom_qty': qty,
                }) for (product, qty) in products_and_quantities],
            })
            delivery.action_confirm()
            if to_validate:
                delivery.action_assign()
                delivery.button_validate()
            return delivery

    def test_purchase_order_suggest_quantities(self):
        """ Checks the suggest wizard adds right products with right quantities.
        Also checks some values, like the products' quantity demand or the
        suggest expected price, are rigthly computed too."""
        today = fields.Datetime.now()
        # Create some products.
        product_2, product_3, product_4, product_5, product_6 = self.env['product.product'].create([{
            'name': f'Product {i + 1}',
            'standard_price': price,
            'is_storable': True,
        } for (i, price) in enumerate([25, 50, 100, 50, 25])])
        self.env['stock.quant']._update_available_quantity(self.product_1, self.stock_location, 42)
        self.env['stock.quant']._update_available_quantity(product_2, self.stock_location, 15)
        self.env['stock.quant']._update_available_quantity(product_3, self.stock_location, 20)

        # Create supplier info.
        self.env['product.supplierinfo'].create([{
            'partner_id': self.partner_1.id,
            'price': 20,
            'product_id': product_2.id,
        }, {
            'partner_id': self.partner_1.id,
            'price': 50,
            'product_id': product_3.id,
        }])

        # Create some delivery in the past.
        self._create_and_process_delivery_at_date(
            [(self.product_1, 12)], today - relativedelta(years=1)
        )
        self._create_and_process_delivery_at_date(
            [(self.product_1, 5), (product_2, 5)], today - relativedelta(months=10, days=3)
        )
        self._create_and_process_delivery_at_date(
            [(self.product_1, 5), (product_3, 10)], today - relativedelta(months=2, days=5)
        )
        self._create_and_process_delivery_at_date(
            [(self.product_1, 10), (product_3, 10)], today - relativedelta(months=1)
        )
        self._create_and_process_delivery_at_date(
            [(self.product_1, 10), (product_2, 5)], today - relativedelta(days=15)
        )
        self._create_and_process_delivery_at_date(
            [(product_2, 5)], today - relativedelta(days=3)
        )

        # Check product demand quantity.
        # With no dates given in the context, the monthly demand should take only last month.
        self.assertEqual(self.product_1.monthly_demand, 20)
        self.assertEqual(product_2.monthly_demand, 10)
        self.assertEqual(product_3.monthly_demand, 10)
        # Check for last week.
        one_week_ago = today - relativedelta(weeks=1)
        context = {
            'monthly_demand_start_date': one_week_ago,
            'monthly_demand_limit_date': today,
        }
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 0)
        self.assertEqual(product_2.with_context(context).monthly_demand, 5)
        self.assertEqual(product_3.with_context(context).monthly_demand, 0)
        # Check for last three months.
        three_months_ago = today - relativedelta(months=3)
        context = {
            'monthly_demand_start_date': three_months_ago,
            'monthly_demand_limit_date': today,
        }
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 25)
        self.assertEqual(product_2.with_context(context).monthly_demand, 10)
        self.assertEqual(product_3.with_context(context).monthly_demand, 20)
        # Check for last year months.
        one_year_ago = today - relativedelta(years=1)
        context = {
            'monthly_demand_start_date': one_year_ago,
            'monthly_demand_limit_date': today,
        }
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 42)
        self.assertEqual(product_2.with_context(context).monthly_demand, 15)
        self.assertEqual(product_3.with_context(context).monthly_demand, 20)
        # Check for January 2020.
        last_january = datetime(year=today.year - 1, month=today.month, day=1)
        context = {
            'monthly_demand_start_date': last_january,
            'monthly_demand_limit_date': last_january + relativedelta(months=1),
        }
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 12)
        self.assertEqual(product_2.with_context(context).monthly_demand, 0)
        self.assertEqual(product_3.with_context(context).monthly_demand, 0)
        # Check for February 2020.
        last_february = datetime(year=today.year - 1, month=today.month, day=1) + relativedelta(months=1)
        context = {
            'monthly_demand_start_date': last_february,
            'monthly_demand_limit_date': last_february + relativedelta(months=1),
        }
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 0)
        self.assertEqual(product_2.with_context(context).monthly_demand, 0)
        self.assertEqual(product_3.with_context(context).monthly_demand, 0)
        # Check for March 2020.
        last_march = datetime(year=today.year - 1, month=today.month, day=1) + relativedelta(months=2)
        context = {
            'monthly_demand_start_date': last_march,
            'monthly_demand_limit_date': last_march + relativedelta(months=1),
        }
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 5)
        self.assertEqual(product_2.with_context(context).monthly_demand, 5)
        self.assertEqual(product_3.with_context(context).monthly_demand, 0)

        # Create a new PO for the vendor then check suggest wizard estimed price.
        po = self.env['purchase.order'].create({'partner_id': self.partner_1.id})
        context = {
            'default_purchase_order_id': po.id,
            'default_warehouse_id': po.picking_type_id.warehouse_id.id,
            'default_product_ids': (self.product_1 | product_2 | product_3).ids,
        }
        po_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })
        # Check estimed price for default values (30 days, based on last month, with 100% factor.)
        self.assertEstimatedPrice(po_suggest, 2700)
        self.assertEstimatedPrice(po_suggest, 1350, days=15)
        self.assertEstimatedPrice(po_suggest, 3410, factor=125)
        # Check estimed price for 3 months.
        self.assertEstimatedPrice(po_suggest, 1330, based_on='three_months')
        self.assertEstimatedPrice(po_suggest, 3700, based_on='three_months', days=90)
        # Check estimed price for current year.
        self.assertEstimatedPrice(po_suggest, 540, based_on='one_year')
        self.assertEstimatedPrice(po_suggest, 5500, based_on='one_year', days=365)

        # Use suggest wizard to generate PO lines and check their values.
        po_suggest.based_on = 'one_month'
        po_suggest.number_of_days = 30
        po_suggest.percent_factor = 100
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 20},
            {'product_id': product_2.id, 'product_qty': 10},
            {'product_id': product_3.id, 'product_qty': 10},
        ])
        # Regenerate PO lines for 3 months (existing lines qty must be updated.)
        po_suggest.based_on = 'three_months'
        po_suggest.number_of_days = 30
        po_suggest.percent_factor = 100
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 9},
            {'product_id': product_2.id, 'product_qty': 4},
            {'product_id': product_3.id, 'product_qty': 7},
        ])
        po_suggest.number_of_days = 90
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 25},
            {'product_id': product_2.id, 'product_qty': 10},
            {'product_id': product_3.id, 'product_qty': 20},
        ])

        # Create supplier info.
        self.env['product.supplierinfo'].create([{
            'partner_id': self.partner_1.id,
            'price': 90,
            'product_id': product_4.id,
        }, {
            'partner_id': self.partner_1.id,
            'price': 45,
            'product_id': product_5.id,
        }, {
            'partner_id': self.partner_1.id,
            'price': 24,
            'product_id': product_6.id,
        }])

        self.env['stock.quant']._update_available_quantity(product_4, self.stock_location, 1)
        self.env['stock.quant']._update_available_quantity(product_5, self.stock_location, 2)
        self.env['stock.quant']._update_available_quantity(product_6, self.stock_location, 10)

        # Create some out delivery on the products and set different scheduled dates.
        delivery_1 = self._create_and_process_delivery_at_date(
            [(product_4, 6)], today, to_validate=False
        )
        delivery_1.scheduled_date = today + relativedelta(days=3)

        delivery_2 = self._create_and_process_delivery_at_date(
            [(product_5, 10)], today, to_validate=False
        )
        delivery_2.scheduled_date = today + relativedelta(days=5)

        self._create_and_process_delivery_at_date(
            [(product_6, 10)], today
        )

        context = {
            'from_date': fields.Datetime.now(),
            'to_date': fields.Datetime.now() + relativedelta(days=2),
        }
        self.assertEqual(product_4.with_context(context).outgoing_qty, 0)
        self.assertEqual(product_5.with_context(context).outgoing_qty, 0)
        self.assertEqual(product_6.with_context(context).outgoing_qty, 0)

        context = {
            'from_date': fields.Datetime.now(),
            'to_date': fields.Datetime.now() + relativedelta(days=4),
        }
        self.assertEqual(product_4.with_context(context).outgoing_qty, 6)
        self.assertEqual(product_5.with_context(context).outgoing_qty, 0)
        self.assertEqual(product_6.with_context(context).outgoing_qty, 0)

        context = {
            'from_date': fields.Datetime.now(),
            'to_date': fields.Datetime.now() + relativedelta(days=8),
        }
        self.assertEqual(product_4.with_context(context).outgoing_qty, 6)
        self.assertEqual(product_5.with_context(context).outgoing_qty, 10)
        self.assertEqual(product_6.with_context(context).outgoing_qty, 0)

        po = self.env['purchase.order'].create({'partner_id': self.partner_1.id})
        context = {
            'default_purchase_order_id': po.id,
            'default_warehouse_id': po.picking_type_id.warehouse_id.id,
            'default_product_ids': (product_4 | product_5 | product_6).ids,
        }
        po_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })
        # Check estimed price when based on actual demand.
        self.assertEstimatedPrice(po_suggest, 810, based_on='actual_demand')
        self.assertEstimatedPrice(po_suggest, 1800, based_on='actual_demand', factor=200)
        self.assertEstimatedPrice(po_suggest, 450, based_on='actual_demand', days=4)
        self.assertEstimatedPrice(po_suggest, 180, based_on='actual_demand', days=4, factor=50)
        self.assertEstimatedPrice(po_suggest, 0, based_on='actual_demand', days=2)

        # Use suggest wizard to generate PO lines and check their values.
        po_suggest.based_on = 'actual_demand'
        po_suggest.number_of_days = 30
        po_suggest.percent_factor = 100
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': product_4.id, 'product_qty': 5},
            {'product_id': product_5.id, 'product_qty': 8},
        ])

        po_suggest.number_of_days = 30
        po_suggest.percent_factor = 200
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': product_4.id, 'product_qty': 11},
            {'product_id': product_5.id, 'product_qty': 18},
        ])

        po_suggest.number_of_days = 4
        po_suggest.percent_factor = 100
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': product_4.id, 'product_qty': 5},
        ])

        po_suggest.number_of_days = 4
        po_suggest.percent_factor = 50
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': product_4.id, 'product_qty': 2},
        ])

    def test_purchase_order_suggest_quantities_for_consu(self):
        """ Checks the suggest wizard works also with consumable products."""
        today = fields.Datetime.now()
        # Create a consumable product.
        consu = self.env['product.product'].create({
            'name': 'Product Consu',
            'standard_price': 23,
        })

        # Create supplier info.
        self.env['product.supplierinfo'].create({
            'partner_id': self.partner_1.id,
            'price': 20,
            'product_id': consu.id,
        })

        # Create some delivery in the past.
        self._create_and_process_delivery_at_date([(consu, 55)], today - relativedelta(years=1, months=3))
        self._create_and_process_delivery_at_date([(consu, 12)], today - relativedelta(years=1))
        self._create_and_process_delivery_at_date([(consu, 5)], today - relativedelta(months=10, days=3))
        self._create_and_process_delivery_at_date([(consu, 5)], today - relativedelta(months=2, days=5))
        self._create_and_process_delivery_at_date([(consu, 10)], today - relativedelta(months=1))
        self._create_and_process_delivery_at_date([(consu, 10)], today - relativedelta(days=15))

        # Check product demand quantity.
        # With no dates given in the context, the monthly demand should take only last month.
        self.assertEqual(consu.monthly_demand, 20)
        # Check for last week.
        one_week_ago = today - relativedelta(weeks=1)
        context = {
            'monthly_demand_start_date': one_week_ago,
            'monthly_demand_limit_date': today,
        }
        self.assertEqual(consu.with_context(context).monthly_demand, 0)
        # Check for last three months.
        three_months_ago = today - relativedelta(months=3)
        context = {
            'monthly_demand_start_date': three_months_ago,
            'monthly_demand_limit_date': today,
        }
        self.assertEqual(consu.with_context(context).monthly_demand, 25)
        # Check for last year months.
        one_year_ago = today - relativedelta(years=1)
        context = {
            'monthly_demand_start_date': one_year_ago,
            'monthly_demand_limit_date': today,
        }
        self.assertEqual(consu.with_context(context).monthly_demand, 42)
        # Check for January 2020.
        last_january = datetime(year=today.year - 1, month=today.month, day=1)
        context = {
            'monthly_demand_start_date': last_january,
            'monthly_demand_limit_date': last_january + relativedelta(months=1),
        }
        self.assertEqual(consu.with_context(context).monthly_demand, 12)
        # Check for February 2020.
        last_february = datetime(year=today.year - 1, month=today.month, day=1) + relativedelta(months=1)
        context = {
            'monthly_demand_start_date': last_february,
            'monthly_demand_limit_date': last_february + relativedelta(months=1),
        }
        self.assertEqual(consu.with_context(context).monthly_demand, 0)
        # Check for March 2020.
        last_march = datetime(year=today.year - 1, month=today.month, day=1) + relativedelta(months=2)
        context = {
            'monthly_demand_start_date': last_march,
            'monthly_demand_limit_date': last_march + relativedelta(months=1),
        }
        self.assertEqual(consu.with_context(context).monthly_demand, 5)

        # Create a new PO for the vendor then check suggest wizard estimed price.
        po = self.env['purchase.order'].create({'partner_id': self.partner_1.id})
        context = {
            'default_purchase_order_id': po.id,
            'default_warehouse_id': po.picking_type_id.warehouse_id.id,
            'default_product_ids': consu.ids,
        }
        po_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })
        # Check estimed price for default values (30 days, based on last month, with 100% factor.)
        self.assertEstimatedPrice(po_suggest, 400)
        self.assertEstimatedPrice(po_suggest, 200, days=15)
        self.assertEstimatedPrice(po_suggest, 500, factor=125)
        # Check estimed price for 3 months.
        self.assertEstimatedPrice(po_suggest, 180, based_on='three_months')
        self.assertEstimatedPrice(po_suggest, 500, based_on='three_months', days=90)
        # Check estimed price for current year.
        self.assertEstimatedPrice(po_suggest, 80, based_on='one_year')
        self.assertEstimatedPrice(po_suggest, 840, based_on='one_year', days=365)

        # Use suggest wizard to generate PO lines and check their values.
        po_suggest.based_on = 'one_month'
        po_suggest.number_of_days = 30
        po_suggest.percent_factor = 100
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': consu.id, 'product_qty': 20},
        ])
        # Regenerate PO lines for 3 months (existing lines qty must be updated.)
        po_suggest.based_on = 'three_months'
        po_suggest.number_of_days = 30
        po_suggest.percent_factor = 100
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': consu.id, 'product_qty': 9},
        ])
        po_suggest.number_of_days = 90
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': consu.id, 'product_qty': 25},
        ])

    def test_purchase_order_suggest_quantities_deduce_forecast_quantity(self):
        """ Ensures that when the forecast quantity is deduced from the suggested quantity"""
        today = fields.Datetime.now()
        self.env['stock.quant']._update_available_quantity(self.product_1, self.stock_location, 12)
        # Do a delivery in the past.
        self._create_and_process_delivery_at_date([(self.product_1, 12)], date=today - timedelta(days=10))

        # Create a new PO for the vendor then check suggest wizard estimed price.
        po = self.env['purchase.order'].create({'partner_id': self.partner_1.id})
        context = {
            'default_purchase_order_id': po.id,
            'default_warehouse_id': po.picking_type_id.warehouse_id.id,
            'default_product_ids': self.product_1.ids,
        }
        po_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })
        # Check estimed price no forecast quantity.
        self.assertEstimatedPrice(po_suggest, 1200)
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 12},
        ])

        # Prepare a receipt for this product and confirm it.
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': self.product_1.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 6,
            })],
        })
        receipt.action_confirm()
        receipt.action_assign()
        # Check estimed price deduce the forecast quantity.
        self.assertEstimatedPrice(po_suggest, 600)
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 6},
        ])

        # Check the same with based_on actual demand.
        product_ad = self.env['product.product'].create([{
            'name': 'Product AD',
            'standard_price': 60,
            'is_storable': True,
        }])

        self.env['product.supplierinfo'].create([{
            'partner_id': self.partner_1.id,
            'price': 55,
            'product_id': product_ad.id,
        }])
        self.env['stock.quant']._update_available_quantity(product_ad, self.stock_location, 7)

        delivery = self._create_and_process_delivery_at_date(
            [(product_ad, 12)], today, to_validate=False
        )
        delivery.scheduled_date = today + relativedelta(days=3)

        # Create a new PO for the vendor then check suggest wizard estimed price.
        po = self.env['purchase.order'].create({'partner_id': self.partner_1.id})
        context = {
            'default_purchase_order_id': po.id,
            'default_warehouse_id': po.picking_type_id.warehouse_id.id,
            'default_product_ids': product_ad.ids,
        }
        po_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })

        self.assertEstimatedPrice(po_suggest, 275, based_on='actual_demand', days=4)
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': product_ad.id, 'product_qty': 5},
        ])

        # Prepare a receipt for this product and confirm it.
        receipt = self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_in.id,
            'location_id': self.supplier_location.id,
            'location_dest_id': self.stock_location.id,
            'move_ids': [Command.create({
                'location_id': self.supplier_location.id,
                'location_dest_id': self.stock_location.id,
                'product_id': product_ad.id,
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 4,
            })],
        })
        receipt.action_confirm()
        receipt.action_assign()

        self.assertEstimatedPrice(po_suggest, 55, based_on='actual_demand', days=4)
        po_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po.order_line, [
            {'product_id': product_ad.id, 'product_qty': 1},
        ])

    def test_purchase_order_suggest_quantities_multiwarehouse(self):
        """ Ensure the product's qty demand is correctly computed for the right warehouse."""
        main_warehouse = self.env.ref('stock.warehouse0')

        date = fields.Datetime.now() - relativedelta(days=15)
        self.env['stock.quant']._update_available_quantity(self.product_1, main_warehouse.lot_stock_id, 5)
        self.env['stock.quant']._update_available_quantity(self.product_1, self.warehouse_1.lot_stock_id, 10)
        # Make a delivery in each warehouse.
        self._create_and_process_delivery_at_date([(self.product_1, 5)], date, warehouse=main_warehouse)
        self._create_and_process_delivery_at_date([(self.product_1, 10)], date, warehouse=self.warehouse_1)
        self.assertEqual(self.product_1.monthly_demand, 15)
        self.assertEqual(self.product_1.with_context(warehouse_id=main_warehouse.id).monthly_demand, 5)
        self.assertEqual(self.product_1.with_context(warehouse_id=self.warehouse_1.id).monthly_demand, 10)

        # Create a PO for each warehouse and check the right quantity is added to the PO line.
        po_1 = self.env['purchase.order'].create({
            'partner_id': self.partner_1.id,
            'picking_type_id': main_warehouse.in_type_id.id,
        })
        context = {
            'default_purchase_order_id': po_1.id,
            'default_warehouse_id': po_1.picking_type_id.warehouse_id.id,
            'default_product_ids': self.product_1.ids,
        }
        po_1_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })
        self.assertEqual(po_1_suggest.warehouse_id, po_1.picking_type_id.warehouse_id, "Should use PO warehouse by default")
        self.assertEstimatedPrice(po_1_suggest, 1500, warehouse=False)
        self.assertEstimatedPrice(po_1_suggest, 500, warehouse=main_warehouse)
        self.assertEstimatedPrice(po_1_suggest, 1000, warehouse=self.warehouse_1)
        # Generate PO line for qty demand based on one specific warehouse.
        po_1_suggest.warehouse_id = main_warehouse
        po_1_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po_1.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 5},
        ])
        # Generate PO line for qty demand not based on any warehouse.
        po_1_suggest.warehouse_id = False
        po_1_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po_1.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 15},
        ])

        po_2 = self.env['purchase.order'].create({
            'partner_id': self.partner_1.id,
            'picking_type_id': self.warehouse_1.in_type_id.id,
        })
        context = {
            'default_purchase_order_id': po_2.id,
            'default_warehouse_id': po_2.picking_type_id.warehouse_id.id,
            'default_product_ids': self.product_1.ids,
        }
        po_2_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })
        self.assertEqual(po_2_suggest.warehouse_id, po_2.picking_type_id.warehouse_id, "Should use PO warehouse by default")
        self.assertEstimatedPrice(po_2_suggest, 1500, warehouse=False)
        self.assertEstimatedPrice(po_2_suggest, 500, warehouse=main_warehouse)
        self.assertEstimatedPrice(po_2_suggest, 1000, warehouse=self.warehouse_1)
        # Generate PO line for qty demand based on one specific warehouse.
        po_2_suggest.warehouse_id = self.warehouse_1
        po_2_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po_2.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 10},
        ])

        # Check the same with based_on actual demand.
        product_ad = self.env['product.product'].create([{
            'name': 'Product AD',
            'standard_price': 60,
            'is_storable': True,
        }])

        self.env['product.supplierinfo'].create([{
            'partner_id': self.partner_1.id,
            'price': 55,
            'product_id': product_ad.id,
        }])
        self.env['stock.quant']._update_available_quantity(product_ad, main_warehouse.lot_stock_id, 7)
        self.env['stock.quant']._update_available_quantity(product_ad, self.warehouse_1.lot_stock_id, 5)

        today = fields.Datetime.now()
        delivery_1 = self._create_and_process_delivery_at_date(
            [(product_ad, 10)], today, to_validate=False, warehouse=main_warehouse
        )
        delivery_1.scheduled_date = today + relativedelta(days=3)

        delivery_2 = self._create_and_process_delivery_at_date(
            [(product_ad, 9)], today, to_validate=False, warehouse=self.warehouse_1
        )
        delivery_2.scheduled_date = today + relativedelta(days=5)

        context = {
            'from_date': fields.Datetime.now(),
            'to_date': fields.Datetime.now() + relativedelta(days=6),
        }
        self.assertEqual(product_ad.with_context(context).outgoing_qty, 19)
        context = {
            'from_date': fields.Datetime.now(),
            'to_date': fields.Datetime.now() + relativedelta(days=6),
            'warehouse_id': main_warehouse.id,
        }
        self.assertEqual(product_ad.with_context(context).outgoing_qty, 10)
        context = {
            'from_date': fields.Datetime.now(),
            'to_date': fields.Datetime.now() + relativedelta(days=6),
            'warehouse_id': self.warehouse_1.id,
        }
        self.assertEqual(product_ad.with_context(context).outgoing_qty, 9)

        # Create a PO for each warehouse and check the right quantity is added to the PO line.
        po_1 = self.env['purchase.order'].create({
            'partner_id': self.partner_1.id,
            'picking_type_id': main_warehouse.in_type_id.id,
        })
        context = {
            'default_purchase_order_id': po_1.id,
            'default_warehouse_id': po_1.picking_type_id.warehouse_id.id,
            'default_product_ids': product_ad.ids,
        }
        po_1_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })
        self.assertEqual(po_1_suggest.warehouse_id, po_1.picking_type_id.warehouse_id, "Should use PO warehouse by default")
        self.assertEstimatedPrice(po_1_suggest, 385, based_on='actual_demand', warehouse=False)
        self.assertEstimatedPrice(po_1_suggest, 165, based_on='actual_demand', warehouse=main_warehouse)
        self.assertEstimatedPrice(po_1_suggest, 220, based_on='actual_demand', warehouse=self.warehouse_1)

        # Generate PO line for qty demand not based on any warehouse.
        po_1_suggest.warehouse_id = False
        po_1_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po_1.order_line, [
            {'product_id': product_ad.id, 'product_qty': 7},
        ])

        # Generate PO line for qty demand based on one specific warehouse.
        po_1_suggest.warehouse_id = main_warehouse
        po_1_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po_1.order_line, [
            {'product_id': product_ad.id, 'product_qty': 3},
        ])

        po_2 = self.env['purchase.order'].create({
            'partner_id': self.partner_1.id,
            'picking_type_id': self.warehouse_1.in_type_id.id,
        })
        context = {
            'default_purchase_order_id': po_2.id,
            'default_warehouse_id': po_2.picking_type_id.warehouse_id.id,
            'default_product_ids': product_ad.ids,
        }
        po_2_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })

        self.assertEqual(po_2_suggest.warehouse_id, po_2.picking_type_id.warehouse_id, "Should use PO warehouse by default")
        self.assertEstimatedPrice(po_2_suggest, 385, based_on='actual_demand', warehouse=False)
        self.assertEstimatedPrice(po_2_suggest, 165, based_on='actual_demand', warehouse=main_warehouse)
        self.assertEstimatedPrice(po_2_suggest, 220, based_on='actual_demand', warehouse=self.warehouse_1)

        # Generate PO line for qty demand based on one specific warehouse.
        po_2_suggest.warehouse_id = self.warehouse_1
        po_2_suggest.action_purchase_order_suggest()
        self.assertRecordValues(po_2.order_line, [
            {'product_id': product_ad.id, 'product_qty': 4},
        ])

    def test_purchase_order_suggest_pricelist_selection(self):
        """ Pricelist selection for suggestion total price estimation
            should follow:
                1 - Best price discounted
                2 - Least qty pricelist if no price match
                3 - Product standard price
        """
        today = fields.Datetime.now()
        po = self.env['purchase.order'].create({'partner_id': self.partner_1.id})
        product = self.env['product.product'].create({
            'name': 'Product 7',
            'standard_price': 20,
            'is_storable': True,
        })
        self.env['product.supplierinfo'].create([{
            'partner_id': self.partner_1.id,
            'price': 17,
            'product_id': product.id,
            'min_qty': 2
        }, {
            'partner_id': self.partner_1.id,
            'price': 13,
            'product_id': product.id,
            'min_qty': 3
        }])
        self.env['stock.quant']._update_available_quantity(product, self.stock_location, 1)
        self._create_and_process_delivery_at_date(
            [(product, 1)], today - relativedelta(days=1)
        )
        context = {
            'default_purchase_order_id': po.id,
            'default_warehouse_id': po.picking_type_id.warehouse_id.id,
            'default_product_ids': [product.id],
        }
        po_suggest = self.env['purchase.order.suggest'].with_context(context).create({
            'number_of_days': 30,
        })
        self.assertEstimatedPrice(po_suggest, 17, based_on='one_week', days=7)  # suggested qty 1 --> should use lowest qty pricelist
        self.assertEstimatedPrice(po_suggest, 34, based_on='one_week', days=14)  # suggested qty 2 --> should matching pricelist
        self.assertEstimatedPrice(po_suggest, 52, based_on='one_week', days=28)  # suggested qty 4 --> should matching pricelist

        partner_2 = self.env['res.partner'].create({'name': "No pricelist"})
        po_2 = self.env['purchase.order'].create({'partner_id': partner_2.id})
        context_2 = {
            'default_purchase_order_id': po_2.id,
            'default_warehouse_id': po.picking_type_id.warehouse_id.id,
            'default_product_ids': [product.id],
        }
        po_suggest_2 = self.env['purchase.order.suggest'].with_context(context_2).create({
            'number_of_days': 30,
        })
        self.assertEstimatedPrice(po_suggest_2, 20, based_on='one_week', days=7)  # No pricelist --> should use standard price

    def test_purchase_order_suggest_search_panel_ux(self):
        # Create product, and supplier info
        today = fields.Datetime.now()
        test_product = self.env['product.product'].create([{
            'name': "test_product",
            'is_storable': True,
        }])
        self.env['stock.quant']._update_available_quantity(test_product, self.stock_location, 12)
        self.env['product.supplierinfo'].create([{
            'partner_id': self.partner_1.id,
            'min_qty': 1,
            'price': 20,
            'product_id': test_product.id,
        }])
        # Create a move yesterday
        self._create_and_process_delivery_at_date([(test_product, 12)], date=today - relativedelta(days=1))
        self.assertEqual(test_product.monthly_demand, 12)

        # Create a and mark as todo a move in 20 days (for checking suggest/forecasted)
        self._create_and_process_delivery_at_date(
            [(test_product, 100)], date=today + relativedelta(days=20), to_validate=False
        )
        # Create a move yesterday on another warehouse
        other_warehouse = self.env.ref('stock.warehouse0')
        self.env['stock.quant']._update_available_quantity(test_product, other_warehouse.lot_stock_id, 1)
        self._create_and_process_delivery_at_date(
            [(test_product, 1)], date=today - relativedelta(days=1), warehouse=other_warehouse
        )
        self.start_tour('/odoo/purchase', "test_purchase_order_suggest_search_panel_ux", login='admin')
