# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, TransactionCase

class TestMrpSubcontractingCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestMrpSubcontractingCommon, cls).setUpClass()
        cls.env.ref('base.group_user').write({'implied_ids': [(4, cls.env.ref('stock.group_production_lot').id)]})
        # 1: Create a subcontracting partner
        main_partner = cls.env['res.partner'].create({'name': 'main_partner'})
        cls.subcontractor_partner1 = cls.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'parent_id': main_partner.id,
            'company_id': cls.env.ref('base.main_company').id,
        })
        # 2. Create a BOM of subcontracting type
        cls.product_category = cls.env.ref('product.product_category_goods')
        cls.comp1 = cls.env['product.product'].create({
            'name': 'Component1',
            'is_storable': True,
            'categ_id': cls.product_category.id,
        })
        cls.comp2 = cls.env['product.product'].create({
            'name': 'Component2',
            'is_storable': True,
            'categ_id': cls.product_category.id,
        })
        cls.finished = cls.env['product.product'].create({
            'name': 'finished',
            'is_storable': True,
            'categ_id': cls.product_category.id,
        })
        bom_form = Form(cls.env['mrp.bom'])
        bom_form.type = 'subcontract'
        bom_form.product_tmpl_id = cls.finished.product_tmpl_id
        bom_form.subcontractor_ids.add(cls.subcontractor_partner1)
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.comp1
            bom_line.product_qty = 1
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.comp2
            bom_line.product_qty = 1
        cls.bom = bom_form.save()

        # Create a BoM for cls.comp2
        cls.comp2comp = cls.env['product.product'].create({
            'name': 'component for Component2',
            'is_storable': True,
            'categ_id': cls.product_category.id,
        })
        bom_form = Form(cls.env['mrp.bom'])
        bom_form.product_tmpl_id = cls.comp2.product_tmpl_id
        with bom_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = cls.comp2comp
            bom_line.product_qty = 1
        cls.comp2_bom = bom_form.save()

        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)

    def _setup_category_stock_journals(self):
        """
        Sets up the all category with some stock accounts.
        """
        a_val = self.env['account.account'].create([{
            'name': 'VALU Account',
            'code': '000003',
            'account_type': 'asset_current',
        }])
        stock_journal = self.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        product_category_all = self.env.ref('product.product_category_goods')
        product_category_all.property_stock_valuation_account_id = a_val
        product_category_all.property_stock_journal = stock_journal
