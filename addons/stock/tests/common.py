# -*- coding: utf-8 -*-

import re

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product.tests.common import TestProductCommon


class TestStockCommon(TestProductCommon):
    """
    This class provides some common resources for stock tests. Most notably, it
    provides a dedicated warehouse: `warehouse_1`, along with its own:
    * picking types:
      * `picking_type_in`
      * `picking_type_out`
      * `picking_type_int`
    * locations:
      * `stock_location`
      * `pack_location`
      * `output_location`
      * `shelf_1` and `shelf_2` sublocations
    * routes:
      * `route_mto`

    It also provides references to some resources that are currently globally
    available, but might be replaced by custom stock data in the future:
    * `customer_location`
    * `supplier_location`
    * `inter_company_location`
    * various product UoMs

    There are also dedicated products, users, custom UoMs etc. provided by this
    class. See the code below for more details.

    Whenever possible, classes inheriting from this one should use the provided
    references instead of obtaining global objects on their own. That's because,
    in the future, stock tests will be using a dedicated set of test data.
    """
    def _create_move(self, product, src_location, dst_location, **values):
        # TDE FIXME: user as parameter
        Move = self.env['stock.move'].with_user(self.user_stock_manager)
        # simulate create + onchange
        move = Move.new({'product_id': product.id, 'location_id': src_location.id, 'location_dest_id': dst_location.id})
        move._onchange_product_id()
        move_values = move._convert_to_write(move._cache)
        move_values.update(**values)
        return Move.create(move_values)

    @classmethod
    def setUpClass(cls):
        super(TestStockCommon, cls).setUpClass()

        cls.ProductObj = cls.env['product.product']
        cls.UomObj = cls.env['uom.uom']
        cls.PartnerObj = cls.env['res.partner']
        cls.ModelDataObj = cls.env['ir.model.data']
        cls.StockPackObj = cls.env['stock.move.line']
        cls.StockQuantObj = cls.env['stock.quant']
        cls.PickingObj = cls.env['stock.picking']
        cls.MoveObj = cls.env['stock.move']
        cls.LotObj = cls.env['stock.lot']
        cls.StockLocationObj = cls.env['stock.location']

        # Warehouses
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'BWH',
            'sequence': 5,
        })
        cls.route_mto = cls.warehouse_1.mto_pull_id.route_id
        cls.route_mto.rule_ids.procure_method = "make_to_order"

        # Model Data
        cls.picking_type_in = cls.warehouse_1.in_type_id
        cls.picking_type_int = cls.warehouse_1.int_type_id
        cls.picking_type_out = cls.warehouse_1.out_type_id
        cls.picking_type_out.reservation_method = 'manual'

        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.warehouse_1.lot_stock_id
        cls.shelf_1, cls.shelf_2 = cls.StockLocationObj.create([{
            'name': 'Shelf 1',
            'location_id': cls.stock_location.id,
        }, {
            'name': 'Shelf 2',
            'location_id': cls.stock_location.id,
        }])

        pack_location = cls.warehouse_1.wh_pack_stock_loc_id
        pack_location.active = True
        cls.pack_location = pack_location
        output_location = cls.warehouse_1.wh_output_stock_loc_id
        output_location.active = True
        cls.output_location = output_location
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.inter_company_location = cls.env.ref('stock.stock_location_inter_company')

        # Product Created A, B, C, D
        cls.productA = cls.ProductObj.create({'name': 'Product A', 'is_storable': True})
        cls.productB = cls.ProductObj.create({'name': 'Product B', 'is_storable': True})
        cls.productC = cls.ProductObj.create({'name': 'Product C', 'is_storable': True})
        cls.productD = cls.ProductObj.create({'name': 'Product D', 'is_storable': True})
        cls.productE = cls.ProductObj.create({'name': 'Product E', 'is_storable': True})

        # Configure unit of measure.
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.uom_gm = cls.env.ref('uom.product_uom_gram')
        cls.uom_ton = cls.env.ref('uom.product_uom_ton')
        # Check Unit
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')

        cls.kgB = cls.ProductObj.create({'name': 'kg-B', 'is_storable': True, 'uom_id': cls.uom_kg.id})
        cls.gB = cls.ProductObj.create({'name': 'g-B', 'is_storable': True, 'uom_id': cls.uom_gm.id})

        cls.env.ref('base.group_user').write({'implied_ids': [
            (4, cls.env.ref('base.group_multi_company').id),
            (4, cls.env.ref('stock.group_production_lot').id),
        ]})
        # User Data: stock user and stock manager
        cls.user_stock_user = mail_new_test_user(
            cls.env,
            name='Pauline Poivraisselle',
            login='pauline',
            email='p.p@example.com',
            notification_type='inbox',
            groups='stock.group_stock_user',
        )
        cls.user_stock_manager = mail_new_test_user(
            cls.env,
            name='Julie Tablier',
            login='julie',
            email='j.j@example.com',
            notification_type='inbox',
            groups='stock.group_stock_manager',
        )

        # Partner
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Julia Agrolait',
            'email': 'julia@agrolait.example.com',
        })

        # Product
        cls.product_3 = cls.env['product.product'].create({
            'name': 'Stone',  # product_3
            'uom_id': cls.uom_dozen.id,
        })

        # Existing data
        cls.existing_inventories = cls.StockQuantObj.search([('inventory_quantity', '!=', 0.0)])
        cls.existing_quants = cls.StockQuantObj.search([])

    def url_extract_rec_id_and_model(self, url):
        # Extract model and record ID
        action_match = re.findall(r'action-([^/]+)', url)
        model_name = self.env.ref(action_match[0]).res_model
        rec_id = re.findall(r'/(\d+)$', url)[0]
        return rec_id, model_name
