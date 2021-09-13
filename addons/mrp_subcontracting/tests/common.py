# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests.common import Form, TransactionCase

class TestMrpSubcontractingCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestMrpSubcontractingCommon, cls).setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.warehouse = cls.env.ref('stock.warehouse0')

        # Create a subcontracting partner
        cls.subcontractor_partner1 = cls.env['res.partner'].create({
            'name': 'subcontractor_partner',
            'company_id': cls.env.ref('base.main_company').id,
        })

        categ_all = cls.env.ref('product.product_category_all')
        # Create products for BoM
        cls.finished, cls.comp1, cls.comp2, cls.comp2comp = cls.env['product.product'].create([
            {'name': 'Finished  ', 'type': 'product', 'categ_id': categ_all.id},
            {'name': 'Component1', 'type': 'product', 'categ_id': categ_all.id},
            {'name': 'Component2', 'type': 'product', 'categ_id': categ_all.id},
            {'name': 'Component for Component2', 'type': 'product', 'categ_id': categ_all.id},
        ])
        # 3. Create a subcontracted BoM and a Normal BoM for one component
        cls.bom, cls.comp2_bom = cls.env['mrp.bom'].create([
            {
                'type': 'subcontract',
                'consumption': 'strict',
                'product_tmpl_id': cls.finished.product_tmpl_id.id,
                'subcontractor_ids': [Command.link(cls.subcontractor_partner1.id)],
                'bom_line_ids': [
                    Command.create({'product_id': cls.comp1.id, 'product_qty': 1}),
                    Command.create({'product_id': cls.comp2.id, 'product_qty': 1}),
                ]
            }, {
                'product_tmpl_id': cls.comp2.product_tmpl_id.id,
                'bom_line_ids': [
                    Command.create({'product_id': cls.comp2comp.id, 'product_qty': 1}),
                ]
            }
        ])
