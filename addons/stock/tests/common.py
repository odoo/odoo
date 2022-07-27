# -*- coding: utf-8 -*-

import re
from odoo.tests import common


class TestStockCommon(common.TransactionCase):
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

        # Model Data
        cls.picking_type_in = cls.ModelDataObj._xmlid_to_res_id('stock.picking_type_in')
        cls.picking_type_out = cls.ModelDataObj._xmlid_to_res_id('stock.picking_type_out')
        cls.env['stock.picking.type'].browse(cls.picking_type_out).reservation_method = 'manual'
        cls.supplier_location = cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_suppliers')
        cls.stock_location = cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_stock')
        pack_location = cls.env.ref('stock.location_pack_zone')
        pack_location.active = True
        cls.pack_location = pack_location.id
        output_location = cls.env.ref('stock.stock_location_output')
        output_location.active = True
        cls.output_location = output_location.id
        cls.customer_location = cls.ModelDataObj._xmlid_to_res_id('stock.stock_location_customers')
        cls.categ_unit = cls.ModelDataObj._xmlid_to_res_id('uom.product_uom_categ_unit')
        cls.categ_kgm = cls.ModelDataObj._xmlid_to_res_id('uom.product_uom_categ_kgm')

        # Product Created A, B, C, D
        cls.productA = cls.ProductObj.create({'name': 'Product A', 'type': 'product'})
        cls.productB = cls.ProductObj.create({'name': 'Product B', 'type': 'product'})
        cls.productC = cls.ProductObj.create({'name': 'Product C', 'type': 'product'})
        cls.productD = cls.ProductObj.create({'name': 'Product D', 'type': 'product'})
        cls.productE = cls.ProductObj.create({'name': 'Product E', 'type': 'product'})

        # Configure unit of measure.
        cls.uom_kg = cls.env['uom.uom'].search([('category_id', '=', cls.categ_kgm), ('uom_type', '=', 'reference')], limit=1)
        cls.uom_kg.write({
            'name': 'Test-KG',
            'rounding': 0.000001})
        cls.uom_tone = cls.UomObj.create({
            'name': 'Test-Tone',
            'category_id': cls.categ_kgm,
            'uom_type': 'bigger',
            'factor_inv': 1000.0,
            'rounding': 0.001})
        cls.uom_gm = cls.UomObj.create({
            'name': 'Test-G',
            'category_id': cls.categ_kgm,
            'uom_type': 'smaller',
            'factor': 1000.0,
            'rounding': 0.001})
        cls.uom_mg = cls.UomObj.create({
            'name': 'Test-MG',
            'category_id': cls.categ_kgm,
            'uom_type': 'smaller',
            'factor': 100000.0,
            'rounding': 0.001})
        # Check Unit
        cls.uom_unit = cls.env['uom.uom'].search([('category_id', '=', cls.categ_unit), ('uom_type', '=', 'reference')], limit=1)
        cls.uom_unit.write({
            'name': 'Test-Unit',
            'rounding': 1.0})
        cls.uom_dozen = cls.UomObj.create({
            'name': 'Test-DozenA',
            'category_id': cls.categ_unit,
            'factor_inv': 12,
            'uom_type': 'bigger',
            'rounding': 0.001})
        cls.uom_sdozen = cls.UomObj.create({
            'name': 'Test-SDozenA',
            'category_id': cls.categ_unit,
            'factor_inv': 144,
            'uom_type': 'bigger',
            'rounding': 0.001})
        cls.uom_sdozen_round = cls.UomObj.create({
            'name': 'Test-SDozenA Round',
            'category_id': cls.categ_unit,
            'factor_inv': 144,
            'uom_type': 'bigger',
            'rounding': 1.0})

        # Product for different unit of measure.
        cls.DozA = cls.ProductObj.create({'name': 'Dozon-A', 'type': 'product', 'uom_id': cls.uom_dozen.id, 'uom_po_id': cls.uom_dozen.id})
        cls.SDozA = cls.ProductObj.create({'name': 'SuperDozon-A', 'type': 'product', 'uom_id': cls.uom_sdozen.id, 'uom_po_id': cls.uom_sdozen.id})
        cls.SDozARound = cls.ProductObj.create({'name': 'SuperDozenRound-A', 'type': 'product', 'uom_id': cls.uom_sdozen_round.id, 'uom_po_id': cls.uom_sdozen_round.id})
        cls.UnitA = cls.ProductObj.create({'name': 'Unit-A', 'type': 'product'})
        cls.kgB = cls.ProductObj.create({'name': 'kg-B', 'type': 'product', 'uom_id': cls.uom_kg.id, 'uom_po_id': cls.uom_kg.id})
        cls.gB = cls.ProductObj.create({'name': 'g-B', 'type': 'product', 'uom_id': cls.uom_gm.id, 'uom_po_id': cls.uom_gm.id})

    def url_extract_rec_id_and_model(self, url):
        rec_id = re.findall(r'[?&]id=([^&]+).*', url)
        model_name = re.findall(r'[?&]model=([^&]+).*', url)
        return rec_id, model_name
