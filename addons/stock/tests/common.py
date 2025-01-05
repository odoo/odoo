# -*- coding: utf-8 -*-

import re

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product.tests.common import TestProductCommon


class TestStockCommon(TestProductCommon):
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

        # Model Data
        cls.picking_type_in = cls.ModelDataObj._xmlid_to_res_id('stock.picking_type_in')
        cls.picking_type_out = cls.ModelDataObj._xmlid_to_res_id('stock.picking_type_out')
        cls.env['stock.picking.type'].browse(cls.picking_type_out).reservation_method = 'manual'
        cls.supplier_location = cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_suppliers')
        cls.stock_location = cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_stock')
        location = cls.StockLocationObj.browse(cls.stock_location)
        if not location.child_ids:
            cls.StockLocationObj.create([{
                'name': 'Shelf 1',
                'location_id': location.id,
            }, {
                'name': 'Shelf 2',
                'location_id': location.id,
            }])
        pack_location = cls.env.ref('stock.location_pack_zone')
        pack_location.active = True
        cls.pack_location = pack_location.id
        output_location = cls.env.ref('stock.stock_location_output')
        output_location.active = True
        cls.output_location = output_location.id
        cls.customer_location = cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_customers')

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
        #######################################################################
        # TODO: refactor these changes from common2.py
        #######################################################################
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

        # Warehouses
        cls.warehouse_1 = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'BWH'})

        # Locations
        cls.location_1 = cls.env['stock.location'].create({
            'name': 'TestLocation1',
            'posx': 3,
            'location_id': cls.warehouse_1.lot_stock_id.id,
        })

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
        cls.existing_inventories = cls.env['stock.quant'].search([('inventory_quantity', '!=', 0.0)])
        cls.existing_quants = cls.env['stock.quant'].search([])
        cls.env.ref('stock.route_warehouse0_mto').rule_ids.procure_method = "make_to_order"

    def url_extract_rec_id_and_model(self, url):
        # Extract model and record ID
        action_match = re.findall(r'action-([^/]+)', url)
        model_name = self.env.ref(action_match[0]).res_model
        rec_id = re.findall(r'/(\d+)$', url)[0]
        return rec_id, model_name
