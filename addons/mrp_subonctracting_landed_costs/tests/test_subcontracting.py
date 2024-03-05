# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon


class TestSubcontractingLandedCosts(TestMrpSubcontractingCommon):
    def test_subcontracted_landed_cost(self):
        self.finished.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.finished.product_tmpl_id.categ_id.property_valuation = 'real_time'

        # Create a receipt picking from the subcontractor
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_in')
        picking_form.partner_id = self.subcontractor_partner1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = 1
        picking_receipt = picking_form.save()
        picking_receipt.action_confirm()
        picking_receipt.move_lines.quantity_done = 1
        picking_receipt.button_validate()

        productlc = self.env['product.product'].create({
            'name': 'product landed cost',
            'type': 'service',
        })

        lc = Form(self.env['stock.landed.cost'])
        lc.account_journal_id = self.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        lc.picking_ids.add(picking_receipt)
        with lc.cost_lines.new() as cost_line:
            cost_line.product_id = productlc
            cost_line.price_unit = 500
        lc = lc.save()
        lc.compute_landed_cost()
        lc.button_validate()

        self.assertEqual(self.finished.value_svl, 500)
