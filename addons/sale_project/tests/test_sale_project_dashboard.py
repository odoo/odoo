# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_project.tests.test_project_profitability import TestProjectProfitabilityCommon as Common


class TestProjectDashboardCommon(Common):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard_project = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Project',
            'partner_id': cls.partner.id,
            'account_id': cls.analytic_account.id,
            'allow_billable': True,
        })
        cls.dashboard_sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner.id,
            'partner_invoice_id': cls.partner.id,
            'partner_shipping_id': cls.partner.id,
        })
        cls.dashboard_sale_order.action_confirm()
        cls.dashboardSaleOrderLine = cls.env['sale.order.line'].with_context(tracking_disable=True, default_order_id=cls.dashboard_sale_order.id)
        cls.dashboard_product_delivery_service, cls.product_milestone, cls.product_prepaid = cls.env['product.product'].create([{
            'name': "Service Delivery",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'service_type': 'manual',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': cls.dashboard_project.id,
        }, {
            'name': "Service Milestone",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'service_type': 'milestones',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': cls.dashboard_project.id,
        }, {
            'name': "Product prepaid",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_tracking': 'task_global_project',
            'project_id': cls.dashboard_project.id,
        }])


class TestDashboardProject(TestProjectDashboardCommon):
    """
    This test ensures that the method get_sale_item_data compute correctly the data needed for the project_profitability sale sub section.
    Since the data is different for the same input when the timesheet module is installed, those tests have to be run at_install
    """

    def test_get_sale_item_data_various_sols(self):
        """This test ensures that the sols are computed and put into the correct profitability sections"""
        sol_service_1, sol_service_2, sol_service_3, sol_service_4 = self.dashboardSaleOrderLine.create([{
                'product_id': self.product_milestone.id,
                'product_uom_qty': 1,
            }, {
                'product_id': self.product_prepaid.id,
                'product_uom_qty': 1,
            }, {
                'product_id': self.material_product.id,
                'product_uom_qty': 1,
            }, {
                'product_id': self.dashboard_product_delivery_service.id,
                'product_uom_qty': 1,
        }])
        expected_dict = sol_service_3._read_format(
            ['display_name', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'product_uom_id', 'product_id']
        )
        sale_item_data = self.dashboard_project.get_sale_items_data(limit=5, with_action=False, section_id='materials')
        self.assertEqual(sale_item_data['sol_items'], expected_dict)
        expected_dict = (sol_service_1 + sol_service_2 + sol_service_4)._read_format(
            ['display_name', 'product_uom_qty', 'qty_delivered', 'qty_invoiced', 'product_uom_id', 'product_id']
        )
        sale_item_data = self.dashboard_project.get_sale_items_data(limit=5, with_action=False, section_id='service_revenues')
        self.assertEqual(sale_item_data['sol_items'], expected_dict)
