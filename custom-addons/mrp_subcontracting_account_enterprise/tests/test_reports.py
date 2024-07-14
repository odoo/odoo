# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon
from odoo.fields import Command
from odoo.tests import Form


class TestReportsMrpAccountSubcontracting(TestMrpSubcontractingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        in_picking_type = cls.env.ref('stock.picking_type_in')
        supplier_location = cls.env.ref('stock.stock_location_suppliers')
        stock_location = cls.env.ref('stock.stock_location_stock')
        cls.picking = cls.env['stock.picking'].create({
            'location_id': supplier_location.id,
            'location_dest_id': stock_location.id,
            'picking_type_id': in_picking_type.id,
            'partner_id': cls.subcontractor_partner1.id,
            'move_ids_without_package': [Command.create({
                'name': 'test_mrp_cost_structure_subcontracting',
                'product_id': cls.finished.id,
                'product_uom_qty': 2,
                'location_id': supplier_location.id,
                'location_dest_id': stock_location.id,
                'product_uom': cls.finished.uom_id.id,
                'price_unit': 25,
            })]
        })

    def test_mrp_cost_structure_and_mrp_report_subcontracting(self):
        """ Check that values of mrp_cost_structure are correctly calculated for subcontracting """

        self.picking.action_confirm()
        self.assertEqual(self.picking.move_ids_without_package.is_subcontract, True)

        self.picking.move_ids_without_package.quantity = 2
        self.picking.button_validate()

        self.env.flush_all()  # Need to flush for mrp report

        mo_subcontracted = self.env['mrp.production'].search([('product_id', '=', self.finished.id)], limit=1)
        self.assertTrue(mo_subcontracted)
        self.assertEqual(mo_subcontracted.state, 'done')

        # Test MRP Cost structure
        report = self.env['report.mrp_account_enterprise.mrp_cost_structure']
        report_values = report._get_report_values(docids=mo_subcontracted.id)['lines'][0]
        self.assertEqual(report_values['subcontracting_total_cost'], 50)
        self.assertEqual(report_values['subcontracting_total_qty'], 2)
        self.assertEqual(report_values['subcontracting'][0]['unit_cost'], 25)
        self.assertEqual(report_values['subcontracting'][0]['partner_name'], self.subcontractor_partner1.display_name)

        # Test Production Analyses Report
        record_report = self.env['mrp.report'].search([('product_id', '=', self.finished.id)])
        self.assertEqual(len(record_report), 1)
        self.assertEqual(record_report.subcontracting_cost, 25 * 2)
        self.assertEqual(record_report.unit_subcontracting_cost, 25)

    def test_mrp_cost_structure_backorder(self):
        """ Check that values of mrp_cost_structure are correctly calculated for subcontracting """

        self.picking.action_confirm()
        self.picking.move_ids_without_package.quantity = 1
        res = self.picking.button_validate()
        wizard = Form(self.env[res.get('res_model')].with_context(res['context'])).save()
        wizard.process()
        backorder_id = self.picking.search([('backorder_id', '=', self.picking.id)])
        backorder_id.move_ids_without_package.quantity = 1
        backorder_id.button_validate()

        self.env.flush_all()  # Need to flush for mrp report

        mo_subcontracted = self.env['mrp.production'].search([('product_id', '=', self.finished.id)])
        self.assertEqual(len(mo_subcontracted), 2)
        self.assertEqual(mo_subcontracted.mapped('state'), ['done', 'done'])

        # Test MRP Cost structure
        for mo in mo_subcontracted:
            report = self.env['report.mrp_account_enterprise.mrp_cost_structure']
            report_values = report._get_report_values(docids=mo.id)['lines'][0]
            self.assertEqual(report_values['subcontracting_total_cost'], 25)
            self.assertEqual(report_values['subcontracting_total_qty'], 1)
            self.assertEqual(report_values['subcontracting'][0]['unit_cost'], 25)
            self.assertEqual(report_values['subcontracting'][0]['partner_name'], self.subcontractor_partner1.display_name)
