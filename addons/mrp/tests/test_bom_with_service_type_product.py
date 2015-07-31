# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common
from openerp import fields


class TestBomWithServiceTypeProduct(common.TransactionCase):

    def setUp(self):
        super(TestBomWithServiceTypeProduct, self).setUp()

# I create Bill of Materials with one service type product and one consumable product

        self.MrpBom = self.env['mrp.bom']
        self.MrpProduction = self.env['mrp.production']
        self.MrpProductProduce = self.env['mrp.product.produce']
        self.main_company = self.env.ref('base.main_company')
        self.product_3_product_template = self.env.ref('product.product_product_3_product_template')
        self.product_3 = self.env.ref('product.product_product_3')
        self.product_uom_unit = self.env.ref('product.product_uom_unit')
        self.product_2 = self.env.ref('product.product_product_2')
        self.product_44 = self.env.ref('product.product_product_44')
        self.mrp_production_action = self.env.ref('mrp.menu_mrp_production_action')

        self.bill_of_material_product = self.MrpBom.create({
            'company_id': self.main_company.id,
            'name': 'PC Assemble SC234',
            'product_tmpl_id': self.product_3_product_template.id,
            'product_id': self.product_3.id,
            'product_uom': self.product_uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': self.product_2.id,
                'product_uom': self.product_uom_unit.id,
                'product_qty': 1.0,
                'product_id': self.product_44.id,
                'product_uom': self.product_uom_unit.id,
                'product_qty': 1.0})]})

# I make the production order using BoM having one service type product and one consumable product.

        self.mrp_production_service_mo1 = self.MrpProduction.create({
            'product_id': self.product_3.id,
            'product_qty': 1.0,
            'bom_id': self.bill_of_material_product.id,
            'date_planned': fields.Datetime.now()})

    def test_00_bom_with_service_type_product(self):

    # I compute the data of production order.

        context = {"lang": "en_US", "tz": False, "search_default_Current": 1, "active_model": "ir.ui.menu", "active_ids": [self.mrp_production_action.id], "active_id": self.mrp_production_action.id, }
        self.mrp_production_service_mo1.with_context(context).action_compute()

    # I confirm the production order.
        self.mrp_production_service_mo1.signal_workflow('button_confirm')

    # I reserved the product.
        self.assertEqual(self.mrp_production_service_mo1.state, 'confirmed', "Production order should be confirmed.")
        self.mrp_production_service_mo1.force_production()

    #I produce product.
        context.update({'active_id': self.mrp_production_service_mo1.id})

        self.mrp_product_produce_1 = self.MrpProductProduce.with_context(context).create({
            'mode': 'consume_produce'})

        lines = self.mrp_product_produce_1.on_change_qty(1.0, [])
        self.mrp_product_produce_1.write(lines['value'])
        self.mrp_product_produce_1.do_produce()

    # I check production order after produced.
        self.assertEqual(self.mrp_production_service_mo1.state, 'done', "Production order should be closed.")
