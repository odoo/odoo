# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
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
            'name': 'Other Product',
            'standard_price': 115,
            'is_storable': True,
        })
        cls.env['product.supplierinfo'].create([{
            'partner_id': cls.vendor.id,
            'price': 100,
            'product_id': cls.product_1.id,
        }])
        cls.other_warehouse = cls.env['stock.warehouse'].create({
            'name': 'Other Warehouse',
            'code': 'TWH2',
            'company_id': cls.env.company.id,
        })

    def assertEstimatedPrice(self, po, price, based_on='30_days', days=30, factor=100, warehouse=False, domain=[]):
        """ This helper method does an assert for the `purchase.order.suggest` wizard
        estimated price for the given parameters (use the default values if not set).
        Note that the wizard fields are updated each time this method is called."""
        base_warehouse = self.picking_type_out.default_location_src_id.warehouse_id
        warehouse_id = (warehouse or base_warehouse).id
        suggest_context = {
            "order_id": po.id,
            "partner_id": po.partner_id.id,
            "warehouse_id": warehouse_id,
            "suggest_based_on": based_on,
            "suggest_days": days,
            "suggest_percent": factor,
        }
        products = self.env["product.product"].with_context(suggest_context).search(domain)
        # Invalidate so changes such as partner_id or new deliveries without changing the @api_depends of the computes
        products.invalidate_recordset(["suggest_estimated_price", "suggested_qty"])
        self.assertEqual(sum(products.mapped("suggest_estimated_price")), price)

    def actionAddAll(self, po, based_on='30_days', days=30, factor=100, warehouse=False):
        base_warehouse = self.picking_type_out.default_location_src_id.warehouse_id
        warehouse_id = (warehouse or base_warehouse).id
        suggest_context = {
            "warehouse_id": warehouse_id,
            "suggest_based_on": based_on,
            "suggest_percent": factor,
            "suggest_days": days,
        }
        po.with_context(suggest_context).action_purchase_order_suggest()

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
                    'product_uom': self.uom.id,
                    'product_uom_qty': qty,
                }) for (product, qty) in products_and_quantities],
            })
            delivery.action_confirm()
            if to_validate:
                delivery.action_assign()
                delivery.button_validate()
            return delivery

    def test_purchase_order_suggest_access_error_non_admin(self):
        """ Test that non-admin users can use the suggest feature without access errors """
        self.env = self.env(user=self.purchase_user)
        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
        })
        po.with_context(
            suggest_days=12,
            suggest_based_on='last_year_m_plus_1',
            suggest_percent=42,
        ).action_purchase_order_suggest()
        self.assertRecordValues(self.vendor, [
            {'suggest_days': 12, 'suggest_based_on': 'last_year_m_plus_1', 'suggest_percent': 42}
        ])

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
            'partner_id': self.vendor.id,
            'price': 20,
            'product_id': product_2.id,
        }, {
            'partner_id': self.vendor.id,
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
            [(self.product_1, 10), (product_3, 10)], today - relativedelta(days=30)
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
        context = {'suggest_based_on': "one_week"}
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 0)
        self.assertAlmostEqual(product_2.with_context(context).monthly_demand, 5 * (365.25 / 12) / 7, places=6)
        self.assertEqual(product_3.with_context(context).monthly_demand, 0)
        # Check for last three months.
        context = {'suggest_based_on': "three_months"}
        self.assertAlmostEqual(self.product_1.with_context(context).monthly_demand, 25 / 3, places=6)
        self.assertAlmostEqual(product_2.with_context(context).monthly_demand, 10 / 3, places=6)
        self.assertAlmostEqual(product_3.with_context(context).monthly_demand, 20 / 3, places=6)
        # Check for last year months.
        context = {'suggest_based_on': "one_year"}
        self.assertAlmostEqual(self.product_1.with_context(context).monthly_demand, 42 / 12, places=6)
        self.assertAlmostEqual(product_2.with_context(context).monthly_demand, 15 / 12, places=6)
        self.assertAlmostEqual(product_3.with_context(context).monthly_demand, 20 / 12, places=6)
        # Check for January 2020.
        context = {'suggest_based_on': "last_year"}
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 12)
        self.assertEqual(product_2.with_context(context).monthly_demand, 0)
        self.assertEqual(product_3.with_context(context).monthly_demand, 0)
        # Check for February 2020.
        context = {'suggest_based_on': "last_year_m_plus_1"}
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 0)
        self.assertEqual(product_2.with_context(context).monthly_demand, 0)
        self.assertEqual(product_3.with_context(context).monthly_demand, 0)
        # Check for March 2020.
        context = {'suggest_based_on': "last_year_m_plus_2"}
        self.assertEqual(self.product_1.with_context(context).monthly_demand, 5)
        self.assertEqual(product_2.with_context(context).monthly_demand, 5)
        self.assertEqual(product_3.with_context(context).monthly_demand, 0)

        # Create a new PO for the vendor then check suggest wizard estimed price.
        po = self.env['purchase.order'].create({'partner_id': self.vendor.id})
        # Check estimed price for default values (30 days, based on last month, with 100% factor.)
        self.assertEstimatedPrice(po, 2700)
        self.assertEstimatedPrice(po, 1350, days=15)
        self.assertEstimatedPrice(po, 3410, factor=125)
        # Check estimed price for 3 months.
        self.assertEstimatedPrice(po, 1330, based_on='three_months')
        self.assertEstimatedPrice(po, 3700, based_on='three_months', days=90)
        # Check estimed price for current year.
        self.assertEstimatedPrice(po, 540, based_on='one_year')
        self.assertEstimatedPrice(po, 5500, based_on='one_year', days=365)

        # Use suggest to generate PO lines and check their values.
        self.actionAddAll(po, based_on='30_days', days=30, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 20},
            {'product_id': product_2.id, 'product_qty': 10},
            {'product_id': product_3.id, 'product_qty': 10},
        ])
        # Regenerate PO lines for 3 months (existing lines qty must be updated.)
        self.actionAddAll(po, based_on='three_months', days=30, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 9},
            {'product_id': product_2.id, 'product_qty': 4},
            {'product_id': product_3.id, 'product_qty': 7},
        ])
        self.actionAddAll(po, based_on='three_months', days=90, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 25},
            {'product_id': product_2.id, 'product_qty': 10},
            {'product_id': product_3.id, 'product_qty': 20},
        ])

        # Create supplier info.
        self.env['product.supplierinfo'].create([{
            'partner_id': self.vendor.id,
            'price': 90,
            'product_id': product_4.id,
        }, {
            'partner_id': self.vendor.id,
            'price': 45,
            'product_id': product_5.id,
        }, {
            'partner_id': self.vendor.id,
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
            'to_date': fields.Datetime.now() + relativedelta(days=2),
        }
        self.assertEqual(product_4.with_context(context).virtual_available, 1)
        self.assertEqual(product_5.with_context(context).virtual_available, 2)
        self.assertEqual(product_6.with_context(context).virtual_available, 0)

        context = {
            'to_date': fields.Datetime.now() + relativedelta(days=4),
        }
        self.assertEqual(product_4.with_context(context).virtual_available, -5)
        self.assertEqual(product_5.with_context(context).virtual_available, 2)
        self.assertEqual(product_6.with_context(context).virtual_available, 0)

        context = {
            'to_date': fields.Datetime.now() + relativedelta(days=8),
        }
        self.assertEqual(product_4.with_context(context).virtual_available, -5)
        self.assertEqual(product_5.with_context(context).virtual_available, -8)
        self.assertEqual(product_6.with_context(context).virtual_available, 0)

        po = self.env['purchase.order'].create({'partner_id': self.vendor.id})

        # Check estimed price when based on actual demand.
        self.assertEstimatedPrice(po, 810, based_on='actual_demand')
        self.assertEstimatedPrice(po, 1620, based_on='actual_demand', factor=200)
        self.assertEstimatedPrice(po, 450, based_on='actual_demand', days=4)
        self.assertEstimatedPrice(po, 270, based_on='actual_demand', days=4, factor=50)
        self.assertEstimatedPrice(po, 0, based_on='actual_demand', days=2)

        # Use suggest wizard to generate PO lines and check their values.
        self.actionAddAll(po, based_on='actual_demand', days=30, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': product_4.id, 'product_qty': 5},
            {'product_id': product_5.id, 'product_qty': 8},
        ])

        self.actionAddAll(po, based_on='actual_demand', days=30, factor=200)
        self.assertRecordValues(po.order_line, [
            {'product_id': product_4.id, 'product_qty': 10},
            {'product_id': product_5.id, 'product_qty': 16},
        ])

        self.actionAddAll(po, based_on='actual_demand', days=4, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': product_4.id, 'product_qty': 5},
        ])

        self.actionAddAll(po, based_on='actual_demand', days=4, factor=50)
        self.assertRecordValues(po.order_line, [
            {'product_id': product_4.id, 'product_qty': 3},
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
            'partner_id': self.vendor.id,
            'price': 20,
            'product_id': consu.id,
        })

        # Create some delivery in the past.
        self._create_and_process_delivery_at_date([(consu, 55)], today - relativedelta(years=1, months=3))
        self._create_and_process_delivery_at_date([(consu, 12)], today - relativedelta(years=1))
        self._create_and_process_delivery_at_date([(consu, 5)], today - relativedelta(months=10, days=3))
        self._create_and_process_delivery_at_date([(consu, 5)], today - relativedelta(months=2, days=5))
        self._create_and_process_delivery_at_date([(consu, 10)], today - relativedelta(days=30))
        self._create_and_process_delivery_at_date([(consu, 10)], today - relativedelta(days=15))

        # Check product demand quantity.
        # With no dates given in the context, the monthly demand should take only last month.
        self.assertEqual(consu.monthly_demand, 20)
        # Check for last week.
        context = {'suggest_based_on': "one_week"}
        self.assertEqual(consu.with_context(context).monthly_demand, 0)
        # Check for last three months.
        context = {'suggest_based_on': "three_months"}
        self.assertAlmostEqual(consu.with_context(context).monthly_demand, 25 / 3, places=6)
        # Check for last year months.
        context = {'suggest_based_on': "one_year"}
        self.assertAlmostEqual(consu.with_context(context).monthly_demand, 42 / 12, places=6)
        # Check for January 2020.
        context = {'suggest_based_on': "last_year"}
        self.assertEqual(consu.with_context(context).monthly_demand, 12)
        # Check for February 2020.
        context = {'suggest_based_on': "last_year_m_plus_1"}
        self.assertEqual(consu.with_context(context).monthly_demand, 0)
        # Check for March 2020.
        context = {'suggest_based_on': "last_year_m_plus_2"}
        self.assertEqual(consu.with_context(context).monthly_demand, 5)

        # Create a new PO for the vendor then check suggest wizard estimed price.
        po = self.env['purchase.order'].create({'partner_id': self.vendor.id})
        # Check estimed price for default values (30 days, based on last month, with 100% factor.)
        self.assertEstimatedPrice(po, 400)
        self.assertEstimatedPrice(po, 200, days=15)
        self.assertEstimatedPrice(po, 500, factor=125)
        # Check estimed price for 3 months.
        self.assertEstimatedPrice(po, 180, based_on='three_months')
        self.assertEstimatedPrice(po, 500, based_on='three_months', days=90)
        # Check estimed price for current year.
        self.assertEstimatedPrice(po, 80, based_on='one_year')
        self.assertEstimatedPrice(po, 840, based_on='one_year', days=365)

        # Use suggest wizard to generate PO lines and check their values.
        self.actionAddAll(po, based_on='30_days', days=30, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': consu.id, 'product_qty': 20},
        ])
        # Regenerate PO lines for 3 months (existing lines qty must be updated.)
        self.actionAddAll(po, based_on='three_months', days=30, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': consu.id, 'product_qty': 9},
        ])
        self.actionAddAll(po, based_on='three_months', days=90, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': consu.id, 'product_qty': 25},
        ])

    def test_purchase_order_suggest_quantities_deduce_forecast_quantity(self):
        """ Ensures that when the forecast quantity is deduced from the suggested quantity"""
        today = fields.Datetime.now()
        self.env['stock.quant']._update_available_quantity(self.product_1, self.stock_location, 12)
        # Do a delivery in the past.
        self._create_and_process_delivery_at_date([(self.product_1, 12)], date=today - relativedelta(days=10))

        # Create a new PO for the vendor then check suggest wizard estimed price.
        po = self.env['purchase.order'].create({'partner_id': self.vendor.id})

        # Check estimed price no forecast quantity.
        self.assertEstimatedPrice(po, 1200)
        self.actionAddAll(po, based_on='30_days', days=30, factor=100)
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
                'product_uom': self.uom.id,
                'product_uom_qty': 6,
            })],
        })
        receipt.action_confirm()
        receipt.action_assign()
        # Check estimed price deduce the forecast quantity.
        self.assertEstimatedPrice(po, 600, days=30)
        self.actionAddAll(po, based_on='30_days', days=30, factor=100)
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
            'partner_id': self.vendor.id,
            'price': 55,
            'product_id': product_ad.id,
        }])
        self.env['stock.quant']._update_available_quantity(product_ad, self.stock_location, 7)

        delivery = self._create_and_process_delivery_at_date(
            [(product_ad, 12)], today, to_validate=False
        )
        delivery.scheduled_date = today + relativedelta(days=3)

        # Create a new PO for the vendor then check suggest wizard estimed price.
        po = self.env['purchase.order'].create({'partner_id': self.vendor.id})
        self.assertEstimatedPrice(po, 275, based_on='actual_demand', days=4)
        self.actionAddAll(po, based_on='actual_demand', days=30, factor=100)
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
                'product_uom': self.uom.id,
                'product_uom_qty': 4,
            })],
        })
        receipt.action_confirm()
        receipt.action_assign()

        self.assertEstimatedPrice(po, 55, based_on='actual_demand', days=4)
        self.actionAddAll(po, based_on='actual_demand', days=30, factor=100)
        self.assertRecordValues(po.order_line, [
            {'product_id': product_ad.id, 'product_qty': 1},
        ])

    def test_purchase_order_suggest_quantities_multiwarehouse(self):
        """ Ensure the product's qty demand is correctly computed for the right warehouse."""
        date = fields.Datetime.now() - relativedelta(days=15)
        self.env['stock.quant']._update_available_quantity(self.product_1, self.warehouse.lot_stock_id, 5)
        self.env['stock.quant']._update_available_quantity(self.product_1, self.other_warehouse.lot_stock_id, 10)
        # Make a delivery in each warehouse.
        self._create_and_process_delivery_at_date([(self.product_1, 5)], date, warehouse=self.warehouse)
        self._create_and_process_delivery_at_date([(self.product_1, 10)], date, warehouse=self.other_warehouse)
        self.assertEqual(self.product_1.monthly_demand, 15)
        self.assertEqual(self.product_1.with_context(warehouse_id=self.warehouse.id).monthly_demand, 5)
        self.assertEqual(self.product_1.with_context(warehouse_id=self.other_warehouse.id).monthly_demand, 10)

        # Create a PO for each warehouse and check the right quantity is added to the PO line.
        po_1 = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'picking_type_id': self.warehouse.in_type_id.id,
        })
        self.assertEstimatedPrice(po_1, 500, warehouse=self.warehouse)
        self.assertEstimatedPrice(po_1, 1000, warehouse=self.other_warehouse)
        # Generate PO line for qty demand based on one specific warehouse.
        self.actionAddAll(po_1, based_on='30_days', days=30, factor=100, warehouse=self.warehouse)
        self.assertRecordValues(po_1.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 5},
        ])
        # Generate PO line for qty demand based on other warehouse
        self.actionAddAll(po_1, based_on='30_days', days=30, factor=100, warehouse=self.other_warehouse)
        self.assertRecordValues(po_1.order_line, [
            {'product_id': self.product_1.id, 'product_qty': 10},
        ])

        po_2 = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'picking_type_id': self.other_warehouse.in_type_id.id,
        })
        self.assertEstimatedPrice(po_2, 500, warehouse=self.warehouse)
        self.assertEstimatedPrice(po_2, 1000, warehouse=self.other_warehouse)
        # Generate PO line for qty demand based on one specific warehouse.
        self.actionAddAll(po_2, based_on='30_days', days=30, factor=100, warehouse=self.other_warehouse)
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
            'partner_id': self.vendor.id,
            'price': 55,
            'product_id': product_ad.id,
        }])
        self.env['stock.quant']._update_available_quantity(product_ad, self.warehouse.lot_stock_id, 7)
        self.env['stock.quant']._update_available_quantity(product_ad, self.other_warehouse.lot_stock_id, 5)

        today = fields.Datetime.now()
        delivery_1 = self._create_and_process_delivery_at_date(
            [(product_ad, 10)], today, to_validate=False, warehouse=self.warehouse
        )
        delivery_1.scheduled_date = today + relativedelta(days=3)

        delivery_2 = self._create_and_process_delivery_at_date(
            [(product_ad, 9)], today, to_validate=False, warehouse=self.other_warehouse
        )
        delivery_2.scheduled_date = today + relativedelta(days=5)

        context = {
            'to_date': fields.Datetime.now() + relativedelta(days=6),
        }
        self.assertEqual(product_ad.with_context(context).virtual_available, -7)
        context = {
            'to_date': fields.Datetime.now() + relativedelta(days=6),
            'warehouse_id': self.warehouse.id,
        }
        self.assertEqual(product_ad.with_context(context).virtual_available, -3)
        context = {
            'to_date': fields.Datetime.now() + relativedelta(days=6),
            'warehouse_id': self.other_warehouse.id,
        }
        self.assertEqual(product_ad.with_context(context).virtual_available, -4)

        # Create a PO for each warehouse and check the right quantity is added to the PO line.
        po_1 = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'picking_type_id': self.warehouse.in_type_id.id,
        })
        self.assertEstimatedPrice(po_1, 165, based_on='actual_demand', warehouse=self.warehouse)
        self.assertEstimatedPrice(po_1, 220, based_on='actual_demand', warehouse=self.other_warehouse)

        # Generate PO line for qty demand based on 1st warehouse.
        self.actionAddAll(po_1, based_on='actual_demand', days=30, factor=100, warehouse=self.other_warehouse)
        self.assertRecordValues(po_1.order_line, [
            {'product_id': product_ad.id, 'product_qty': 4},
        ])
        # Generate PO line for qty demand based on 2nd specific warehouse.
        self.actionAddAll(po_1, based_on='actual_demand', days=30, factor=100, warehouse=self.warehouse)
        self.assertRecordValues(po_1.order_line, [
            {'product_id': product_ad.id, 'product_qty': 3},
        ])

        po_2 = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'picking_type_id': self.other_warehouse.in_type_id.id,
        })
        self.assertEstimatedPrice(po_2, 165, based_on='actual_demand', warehouse=self.warehouse)
        self.assertEstimatedPrice(po_2, 220, based_on='actual_demand', warehouse=self.other_warehouse)

    def test_purchase_order_suggest_pricelist_selection(self):
        """ Pricelist selection for suggestion total price estimation
            should follow:
                1 - Best price discounted
                2 - Least qty pricelist if no price match
                3 - Product standard price
        """
        today = fields.Datetime.now()
        po = self.env['purchase.order'].create({'partner_id': self.vendor.id})
        product = self.env['product.product'].create({
            'name': 'Product 7',
            'standard_price': 20,
            'is_storable': True,
        })
        self.env['product.supplierinfo'].create([{
            'partner_id': self.vendor.id,
            'price': 17,
            'product_id': product.id,
            'min_qty': 2
        }, {
            'partner_id': self.vendor.id,
            'price': 13,
            'product_id': product.id,
            'min_qty': 3
        }])
        self.env['stock.quant']._update_available_quantity(product, self.stock_location, 1)
        self._create_and_process_delivery_at_date(
            [(product, 1)], today - relativedelta(days=1)
        )
        self.assertEstimatedPrice(po, 17, based_on='one_week', days=7)  # suggested qty 1 --> should use lowest qty pricelist
        self.assertEstimatedPrice(po, 34, based_on='one_week', days=14)  # suggested qty 2 --> should matching pricelist
        self.assertEstimatedPrice(po, 52, based_on='one_week', days=28)  # suggested qty 4 --> should matching pricelist

        partner_2 = self.env['res.partner'].create({'name': "No pricelist"})
        po_2 = self.env['purchase.order'].create({'partner_id': partner_2.id})
        self.assertEstimatedPrice(po_2, 20, based_on='one_week', days=7)  # No pricelist --> should use standard price

    def test_purchase_order_suggest_search_panel_ux(self):
        """ Tests the purchase catalog suggest component, in particular:
        - Suggest component: Hidding, Estimated price, Add all, Changing warehouse, Saving defaults
        - Suggest record interactions: Monthly demand & forecast, Add button
        - Suggest kanban interactions: Add All Filter, and kanban ordering
        """
        today = fields.Datetime.now()
        test_category = self.env['product.category'].create({
            'name': "Test Category",
        })
        test_category_goods = self.env['product.category'].create({
            'name': "Goods",
        })
        self.product_1.categ_id = test_category_goods.id
        test_product = self.env['product.product'].create([{
            'name': "test_product",
            'categ_id': test_category.id,
            'is_storable': True,
        }])
        self.env['product.supplierinfo'].create([{
            'partner_id': self.vendor.id,
            'min_qty': 1,
            'price': 20,
            'product_id': test_product.id,
        }])

        # Create and confirm a move yesterday (used to check monthly_demand/suggest)
        self.env['stock.quant']._update_available_quantity(test_product, self.stock_location, 24)
        self._create_and_process_delivery_at_date(
            [(test_product, 12)], date=fields.Datetime.now() - relativedelta(days=1)
        )
        # Create and confirm 10 days ago (used to check monthly_demand/suggest with 7 days)
        self._create_and_process_delivery_at_date(
            [(test_product, 12)], date=fields.Datetime.now() - relativedelta(days=10)
        )
        self.assertEqual(test_product.monthly_demand, 24)

        # Create and mark as todo a move in  18 & 20 days (for checking forecast on records and suggestion with Forecasted mode)
        self._create_and_process_delivery_at_date(
            [(test_product, 50)], date=today + relativedelta(days=18), to_validate=False
        )
        self._create_and_process_delivery_at_date(
            [(test_product, 50)], date=today + relativedelta(days=20), to_validate=False
        )
        # Create a move yesterday on another warehouse
        other_warehouse = self.other_warehouse
        self.env['stock.quant']._update_available_quantity(test_product, other_warehouse.lot_stock_id, 1)
        self._create_and_process_delivery_at_date(
            [(test_product, 1)], date=today - relativedelta(days=1), warehouse=other_warehouse
        )
        self.start_tour('/odoo/purchase', "test_purchase_order_suggest_search_panel_ux", login='admin')
