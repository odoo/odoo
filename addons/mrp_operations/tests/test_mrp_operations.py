# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import os
from openerp.tests import TransactionCase
from openerp import fields, tools
from openerp import report as odoo_report


class TestMrpOperation(TransactionCase):

    def setUp(self):
        super(TestMrpOperation, self).setUp()
        ResUsers = self.env["res.users"]
        self.MrpProduction = self.env['mrp.production']
        self.ProcurementOrder = self.env['procurement.order']
        self.mrp_group_mrp_user = self.env.ref('mrp.group_mrp_user')
        self.stock_group_stock_user = self.env.ref('stock.group_stock_user')
        self.product_uom = self.env.ref('product.product_uom_unit')
        self.location_src = self.env.ref('stock.stock_location_stock')
        self.product_3 = self.env.ref('product.product_product_3')
        self.mrp_production_workcenter_line = self.env['mrp.production.workcenter.line']
        self.mrp_workcenter_1 = self.env.ref('mrp.mrp_workcenter_1')

        # Create a user as 'MRP User'
        self.mrpUser = ResUsers.create({
            'name': 'MRP User',
            'login': 'mrpuser',
            'password': 'mrppwd',
            'email': 'mrp_operation_user@yourcompany.com',
            'groups_id': [(6, 0, [self.mrp_group_mrp_user.id, self.stock_group_stock_user.id])], })

    def test_mrp_operation(self):
        production = self.MrpProduction.create({'name': 'PC Assemble SC234',
                                                'product_id': self.product_3.id,
                                                'product_qty': 2.0,
                                                'product_uom': self.product_uom.id,
                                                'bom_id': self.env.ref('mrp.mrp_bom_9').id,
                                                'location_src_id': self.location_src.id,
                                                'routing_id': self.env.ref('mrp.mrp_routing_2').id,
                                                'date_planned': fields.Datetime.now()
                                                })

        #I compute the production order.
        production.sudo(self.mrpUser.id).action_compute()

        workcenter_line = self.mrp_production_workcenter_line.create({
            'name': "assembly",
            'workcenter_id': self.mrp_workcenter_1.id,
            'production_id': production.id,
            'date_planned': fields.Datetime.now(),
            'cycle': 2.00,
            'hour': 4.00
        })

        # I check planned date in workcenter lines of production order.
        for line in workcenter_line:
            #TODO: to check start date of next line should be end of date of previous line.
            self.assertTrue(line.date_planned, "Planned Start date is not computed")
            self.assertTrue(line.date_planned_end, "Planned End date is not computed")
        # I confirm the Production Order.
        production.signal_workflow('button_confirm')

        # I run scheduler.
        self.ProcurementOrder.run_scheduler()

        # I forcefully close internal shipment.
        production.force_production()

        # I start production.
        production.signal_workflow('button_produce')

        # Production start on first work center, so I start work operation on first work center.
        workcenter_line.signal_workflow('button_start_working')

        # Now I pause first work operation due to technical fault of work center.
        workcenter_line.signal_workflow('button_pause')

        # I resume first work operation.
        workcenter_line.signal_workflow('button_resume')

        # I cancel first work operation.
        workcenter_line.signal_workflow('button_cancel')

        # I reset first work operation and start after resolving technical fault of work center.
        workcenter_line.signal_workflow('button_draft')
        workcenter_line.signal_workflow('button_start_working')

        # I close first work operation as this work center completed its process.
        workcenter_line.signal_workflow('button_done')

        # Now I close other operations one by one which are in start state.
        for work_line in workcenter_line:
            work_line.signal_workflow('button_start_working')
            work_line.signal_workflow('button_done')

        # I check that the production order is now done.
        self.assertEqual(workcenter_line.state, 'done', 'Production should be closed after finished all operations.')

        # I print Workcenter's Barcode Report.
        ids = [self.env.ref('mrp.mrp_workcenter_0').id, self.env.ref('mrp.mrp_workcenter_1').id]
        data, format = odoo_report.render_report(self.env.cr, self.mrpUser.id, ids, 'mrp_operations.report_wcbarcode', {})
        assert data
        if tools.config['test_report_directory']:
            file(os.path.join(tools.config['test_report_directory'], 'mrp_operations-workcenter_barcode_report.'+format), 'wb+').write(data)
