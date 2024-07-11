# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_landed_costs.tests.test_stockvaluationlayer import TestStockValuationLCCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestStockLandedCostsBranches(TestStockValuationLCCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company = cls.env.company
        cls.branch = cls.env['res.company'].create({
            'name': 'Branch',
            'parent_id': cls.company.id,
        })
        cls.env['account.chart.template'].try_loading(cls.company.chart_template, company=cls.branch, install_demo=False)
        cls.env.user.company_id = cls.branch

        cls.vendor1 = cls.env['res.partner'].create({'name': 'vendor1'})

        cls.product1.categ_id.property_cost_method = 'fifo'

    def test_create_lc_from_branch(self):
        """
        From a company's branch, create a LC and ensure it impacts the SVL
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.branch.id)], limit=1)
        supplier_location = self.env.ref('stock.stock_location_suppliers')

        receipt = self.env['stock.picking'].create({
            'location_id': supplier_location.id,
            'location_dest_id': warehouse.lot_stock_id.id,
            'picking_type_id': warehouse.in_type_id.id,
            'move_ids': [(0, 0, {
                'name': self.product1.name,
                'location_id': supplier_location.id,
                'location_dest_id': warehouse.lot_stock_id.id,
                'picking_type_id': warehouse.in_type_id.id,
                'product_id': self.product1.id,
                'product_uom_qty': 1,
                'product_uom': self.product1.uom_id.id,
                'price_unit': 10,
            })],
        })
        receipt.action_confirm()
        receipt.action_assign()
        receipt.move_line_ids.quantity = 1
        receipt.button_validate()

        lc_form = Form(self.env['stock.landed.cost'])
        lc_form.picking_ids.add(receipt)
        with lc_form.cost_lines.new() as cost_line:
            cost_line.product_id = self.productlc1
            cost_line.price_unit = 5
        lc = lc_form.save()
        lc.compute_landed_cost()
        lc.button_validate()

        self.assertEqual(self.product1.value_svl, 15)
        self.assertEqual(self.product1.quantity_svl, 1)
        self.assertEqual(self.product1.standard_price, 15)

    def test_lc_generated_from_bill(self):
        """
        Confirm PO, receive products, post bill and generate LC
        """
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor1
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10
            po_line.taxes_id.clear()
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_line_ids.quantity = 1
        receipt.button_validate()

        action = po.action_create_invoice()
        bill = self.env['account.move'].browse(action['res_id'])
        bill_form = Form(bill)
        bill_form.invoice_date = bill_form.date
        with bill_form.invoice_line_ids.new() as inv_line:
            inv_line.product_id = self.productlc1
            inv_line.price_unit = 5
        bill = bill_form.save()
        bill.action_post()

        action = bill.button_create_landed_costs()
        lc_form = Form(self.env[action['res_model']].browse(action['res_id']))
        lc_form.picking_ids.add(receipt)
        lc = lc_form.save()
        lc.button_validate()

        self.assertEqual(self.product1.value_svl, 15)
        self.assertEqual(self.product1.quantity_svl, 1)
        self.assertEqual(self.product1.standard_price, 15)
