# -*- coding: utf-8 -*-

import re

from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.product.tests.common import TestProductCommon


class TestStockCommon(TestProductCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Partner
        cls.partner_1 = cls.env['res.partner'].create({
            'name': 'Julia Agrolait',
            'email': 'julia@agrolait.example.com',
        })
        cls.stock_company = cls.env['res.company'].create({
            'name': 'Test Logistics Company A',
        })

        #######################################################################
        # TODO: refactor these changes from common2.py
        #######################################################################

        # User Data: stock user and stock manager
        cls.user_stock_user = mail_new_test_user(
            cls.env,
            name='Test Stock User',
            login='stock',
            email='stock@test.com',
            notification_type='inbox',
            groups='stock.group_stock_user,base.group_multi_company,stock.group_production_lot',
            company_id=cls.stock_company.id,
        )
        cls.user_stock_manager = mail_new_test_user(
            cls.env,
            name='Julie Tablier',
            login='julie',
            email='j.j@example.com',
            notification_type='inbox',
            groups='stock.group_stock_manager,base.group_multi_company,stock.group_production_lot',
            company_id=cls.stock_company.id,
        )
        cls.ProductObj = cls.env['product.product']
        cls.UomObj = cls.env['uom.uom']
        cls.PartnerObj = cls.env['res.partner']
        cls.ModelDataObj = cls.env['ir.model.data']
        cls.StockPackObj = cls.env['stock.move.line']
        cls.StockQuantObj = cls.env['stock.quant']
        cls.PickingObj = cls.env['stock.picking']
        cls.PickingTypeObj = cls.env['stock.picking.type']
        cls.MoveObj = cls.env['stock.move']
        cls.LotObj = cls.env['stock.lot']
        cls.StockLocationObj = cls.env['stock.location']

        # cls.ProductObj = cls.env['product.product'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.UomObj = cls.env['uom.uom'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.PartnerObj = cls.env['res.partner'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.ModelDataObj = cls.env['ir.model.data'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.StockPackObj = cls.env['stock.move.line'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.StockQuantObj = cls.env['stock.quant'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.PickingObj = cls.env['stock.picking'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.PickingTypeObj = cls.env['stock.picking.type'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.MoveObj = cls.env['stock.move'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.LotObj = cls.env['stock.lot'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.StockLocationObj = cls.env['stock.location'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.WarehouseObj = cls.env['stock.warehouse'].with_context({'allowed_company_ids': cls.stock_company.ids})
        # cls.ReturnPickingObj = cls.env['stock.return.picking'].with_context({'allowed_company_ids': cls.stock_company.ids})

        cls.categ_unit = cls.ModelDataObj._xmlid_to_res_id('uom.product_uom_categ_unit')
        cls.categ_kgm = cls.ModelDataObj._xmlid_to_res_id('uom.product_uom_categ_kgm')
        # Configure unit of measure.
        cls.uom_kg = cls.env['uom.uom'].search([('category_id', '=', cls.categ_kgm), ('uom_type', '=', 'reference')], limit=1)
        cls.uom_kg.write({
            'name': 'Test-KG',
            'rounding': 0.000001
        })
        cls.uom_tone = cls.UomObj.create({
            'name': 'Test-Tone',
            'category_id': cls.categ_kgm,
            'uom_type': 'bigger',
            'factor_inv': 1000.0,
            'rounding': 0.001
        })
        cls.uom_gm = cls.UomObj.create({
            'name': 'Test-G',
            'category_id': cls.categ_kgm,
            'uom_type': 'smaller',
            'factor': 1000.0,
            'rounding': 0.001
        })
        cls.uom_mg = cls.UomObj.create({
            'name': 'Test-MG',
            'category_id': cls.categ_kgm,
            'uom_type': 'smaller',
            'factor': 100000.0,
            'rounding': 0.001
        })
        # Check Unit
        cls.uom_unit = cls.env['uom.uom'].search([('category_id', '=', cls.categ_unit), ('uom_type', '=', 'reference')], limit=1)
        cls.uom_unit.write({
            'name': 'Test-Unit',
            'rounding': 0.001
        })
        cls.uom_dozen = cls.UomObj.create({
            'name': 'Test-DozenA',
            'category_id': cls.categ_unit,
            'factor_inv': 12,
            'uom_type': 'bigger',
            'rounding': 0.001
        })
        cls.uom_sdozen = cls.UomObj.create({
            'name': 'Test-SDozenA',
            'category_id': cls.categ_unit,
            'factor_inv': 144,
            'uom_type': 'bigger',
            'rounding': 0.001
        })
        cls.uom_sdozen_round = cls.UomObj.create({
            'name': 'Test-SDozenA Round',
            'category_id': cls.categ_unit,
            'factor_inv': 144,
            'uom_type': 'bigger',
            'rounding': 1.0
        })

        # Product Created A, B, C, D
        cls.productA = cls.ProductObj.create({'name': 'Product A', 'is_storable': True})
        cls.productB = cls.ProductObj.create({'name': 'Product B', 'is_storable': True})
        cls.productC = cls.ProductObj.create({'name': 'Product C', 'is_storable': True})
        cls.productD = cls.ProductObj.create({'name': 'Product D', 'is_storable': True})
        cls.productE = cls.ProductObj.create({'name': 'Product E', 'is_storable': True})
        cls.setup_product_common()
        # Product
        cls.product_3 = cls.ProductObj.create({
            'name': 'Stone',  # product_3
            'uom_id': cls.uom_dozen.id,
            'uom_po_id': cls.uom_dozen.id,
        })
        # Product for different unit of measure.
        cls.DozA = cls.ProductObj.create({'name': 'Dozon-A', 'is_storable': True, 'uom_id': cls.uom_dozen.id, 'uom_po_id': cls.uom_dozen.id})
        cls.SDozA = cls.ProductObj.create({'name': 'SuperDozon-A', 'is_storable': True, 'uom_id': cls.uom_sdozen.id, 'uom_po_id': cls.uom_sdozen.id})
        cls.SDozARound = cls.ProductObj.create({'name': 'SuperDozenRound-A', 'is_storable': True, 'uom_id': cls.uom_sdozen_round.id, 'uom_po_id': cls.uom_sdozen_round.id})
        cls.UnitA = cls.ProductObj.create({'name': 'Unit-A', 'is_storable': True})
        cls.kgB = cls.ProductObj.create({'name': 'kg-B', 'is_storable': True, 'uom_id': cls.uom_kg.id, 'uom_po_id': cls.uom_kg.id})
        cls.gB = cls.ProductObj.create({'name': 'g-B', 'is_storable': True, 'uom_id': cls.uom_gm.id, 'uom_po_id': cls.uom_gm.id})

        # Warehouses
        cls.warehouse_1 = cls.env['stock.warehouse'].search([('company_id', '=', cls.stock_company.id)])
        cls.warehouse_2 = cls.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'BWH',
            'company_id': cls.stock_company.id,
        })

        # Locations
        cls.location_1 = cls.StockLocationObj.create({
            'name': 'TestLocation1',
            'posx': 3,
            'location_id': cls.warehouse_1.lot_stock_id.id,
            'company_id': cls.stock_company.id,
        })

        cls.picking_type_in = cls.warehouse_1.in_type_id
        cls.picking_type_int = cls.warehouse_1.int_type_id
        cls.picking_type_out = cls.warehouse_1.out_type_id
        cls.warehouse_1.out_type_id.reservation_method = 'manual'

        cls.supplier_location = cls.StockLocationObj.browse(
            [cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_suppliers')]
        )[0]
        cls.stock_location = cls.warehouse_1.lot_stock_id
        location = cls.warehouse_1.lot_stock_id
        if not location.child_ids:
            cls.StockLocationObj.create([{
                'name': 'Shelf 1',
                'location_id': location.id,
            }, {
                'name': 'Shelf 2',
                'location_id': location.id,
            }])

        # Model Data
        pack_location = cls.warehouse_1.wh_pack_stock_loc_id
        pack_location.active = True
        cls.pack_location = pack_location
        output_location = cls.warehouse_1.wh_output_stock_loc_id
        output_location.active = True
        cls.output_location = output_location
        cls.customer_location = cls.StockLocationObj.browse(
            [cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_customers')]
        )[0]
        cls.production_location = cls.StockLocationObj.search(
            [('usage', '=', 'production'), ('company_id', '=', cls.stock_company.id)]
        )
        cls.production_location_id = cls.production_location.id

        # Existing data
        cls.existing_inventories = cls.StockQuantObj.search([('inventory_quantity', '!=', 0.0)])
        cls.existing_quants = cls.StockQuantObj.search([])
        cls.env.ref('stock.route_warehouse0_mto').rule_ids.procure_method = "make_to_order"

    def setUp(self):
        super().setUp()
        self.env = self.env(context={'allowed_company_ids': self.stock_company.ids})
        self.uid = self.user_stock_user
        self.ProductObj = self.env['product.product']
        self.UomObj = self.env['uom.uom']
        self.PartnerObj = self.env['res.partner']
        self.ModelDataObj = self.env['ir.model.data']
        self.StockPackObj = self.env['stock.move.line']
        self.StockQuantObj = self.env['stock.quant']
        self.PickingObj = self.env['stock.picking']
        self.PickingTypeObj = self.env['stock.picking.type']
        self.MoveObj = self.env['stock.move']
        self.LotObj = self.env['stock.lot']
        self.StockLocationObj = self.env['stock.location']

    def _create_move(self, product, src_location, dst_location, **values):
        # TDE FIXME: user as parameter
        Move = self.MoveObj
        # simulate create + onchange
        move = Move.new({'product_id': product.id, 'location_id': src_location.id, 'location_dest_id': dst_location.id})
        move._onchange_product_id()
        move_values = move._convert_to_write(move._cache)
        move_values.update(**values)
        return Move.create(move_values)

    @classmethod
    def _enable_adv_location(cls, user=None):
        """ Required for `manufacture_steps` to be visible in the view """
        user = user or cls.user
        user.groups_id += cls.env.ref('stock.group_adv_location')

    def url_extract_rec_id_and_model(self, url):
        # Extract model and record ID
        action_match = re.findall(r'action-([^/]+)', url)
        model_name = self.env.ref(action_match[0]).sudo().res_model
        rec_id = re.findall(r'/(\d+)$', url)[0]
        return rec_id, model_name

    @classmethod
    def setup_product_common(cls):
        # moved from TestProductCommon
        # Product environment related data
        cls.uom_dunit = cls.env['uom.uom'].create({
            'name': 'DeciUnit',
            'category_id': cls.uom_unit.category_id.id,
            'factor_inv': 0.1,
            'factor': 10.0,
            'uom_type': 'smaller',
            'rounding': 0.001,
        })

        cls.product_1, cls.product_2 = cls.ProductObj.create([{
            'name': 'Courage',  # product_1
            'type': 'consu',
            'default_code': 'PROD-1',
            'uom_id': cls.uom_dunit.id,
            'uom_po_id': cls.uom_dunit.id,
        }, {
            'name': 'Wood',  # product_2
        }])

        # Kept for reduced diff in other modules (mainly stock & mrp)
        cls.prod_att_1 = cls.color_attribute
        cls.prod_attr1_v1 = cls.color_attribute_red
        cls.prod_attr1_v2 = cls.color_attribute_blue
        cls.prod_attr1_v3 = cls.color_attribute_green

        cls.product_7_template = cls.product_template_sofa

        cls.product_7_attr1_v1 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[0]
        cls.product_7_attr1_v2 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[1]
        cls.product_7_attr1_v3 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[2]

        cls.product_7_1 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v1)
        cls.product_7_2 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v2)
        cls.product_7_3 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v3)
