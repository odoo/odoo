# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.sale_project.tests.test_sale_project_dashboard import TestProjectDashboardCommon as Common


@tagged('-at_install', 'post_install')
class TestSaleTimesheetDashboard(Common):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard_product_delivery_timesheet = cls.env['product.product'].create({
            'name': "Service delivered",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-DELI1',
            'service_type': 'timesheet',
            'service_tracking': 'no',
            'project_id': False,
            'taxes_id': False,
        })

    def test_get_sale_item_data_various_sol_with_timesheet_installed(self):
        """This test ensures that when the timesheet module is installed, the sols are computed and put into the new profitability sections."""

        sol_service_1, sol_service_2, sol_service_3, sol_service_4, sol_service_5 = self.dashboardSaleOrderLine.create([{
            'product_id': self.product_milestone.id,
            'product_uom_qty': 1,
        }, {
            'product_id': self.product_prepaid.id,
            'product_uom_qty': 1,
        }, {
            'product_id': self.material_product.id,
            'product_uom_qty': 1,
        }, {
            'product_id': self.dashboard_product_delivery_timesheet.id,
            'product_uom_qty': 1,
        }, {
            'product_id': self.dashboard_product_delivery_service.id,
            'product_uom_qty': 1,
        }])
        sale_item_data = self.dashboard_project.get_sale_items_data(with_action=False, limit=5, section_id='materials')
        self.assertEqual(
            sale_item_data['sol_items'],
            [{'id': sol_service_3.id, 'name': 'Material', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (1, 'Units'), 'product_id': (self.material_product.id, 'Material')}]
        )
        sale_item_data = self.dashboard_project.get_sale_items_data(with_action=False, limit=5, section_id='billable_fixed')
        self.assertEqual(
            sale_item_data['sol_items'],
            [{'id': sol_service_2.id, 'name': '[SERV-ORDERED2] Product prepaid', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.product_prepaid.id, '[SERV-ORDERED2] Product prepaid')}]
        )
        sale_item_data = self.dashboard_project.get_sale_items_data(with_action=False, limit=5, section_id='billable_milestones')
        self.assertEqual(
            sale_item_data['sol_items'],
            [{'id': sol_service_1.id, 'name': '[SERV-ORDERED2] Service Milestone', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.product_milestone.id, '[SERV-ORDERED2] Service Milestone')}]
        )
        sale_item_data = self.dashboard_project.get_sale_items_data(with_action=False, limit=5, section_id='billable_time')
        self.assertEqual(
            sale_item_data['sol_items'],
            [{'id': sol_service_4.id, 'name': '[SERV-DELI1] Service delivered', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_timesheet.id, '[SERV-DELI1] Service delivered')}]
        )
        sale_item_data = self.dashboard_project.get_sale_items_data(with_action=False, limit=5, section_id='billable_manual')
        self.assertEqual(
            sale_item_data['sol_items'],
            [{'id': sol_service_5.id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')}]
        )
