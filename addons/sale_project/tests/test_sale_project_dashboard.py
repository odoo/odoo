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

    def test_get_sale_item_data_limit_and_load_more(self):
        """This test ensures that when more than 5 sols are present, only 5 are computed on the first call.
        It also ensures that the call from the 'load more' button is correctly computed"""

        sols = self.dashboardSaleOrderLine.create([{
            'product_id': self.dashboard_product_delivery_service.id,
            'product_uom_qty': i,
        } for i in range(1, 8)])
        sale_item_data = self.dashboard_project.get_sale_items_data(limit=5)
        expected_dict = {
            'materials': {'data': [], 'displayLoadMore': False},
            'service_revenues': {
                'data':
                    [
                        {'id': sols[0].id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')},
                        {'id': sols[1].id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 2.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')},
                        {'id': sols[2].id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 3.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')},
                        {'id': sols[3].id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 4.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')},
                        {'id': sols[4].id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 5.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')},
                    ],
                'displayLoadMore': True,
            },
        }
        self.assertEqual(sale_item_data, expected_dict)
        # add a new call with the 'section_id' to ensure that the 2 extra sol are fetched correctly.
        sale_item_data = self.dashboard_project.get_sale_items_data(offset=5, limit=5, section_id='service_revenues')
        expected_list = [
            {'id': sols[5].id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 6.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')},
            {'id': sols[6].id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 7.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')},
        ]
        self.assertEqual(sale_item_data, expected_list)

    def test_get_sale_item_data_various_sols(self):
        """This test ensures that the sols are computed and put into the correct profitability sections"""
        self.dashboard_project.allow_billable = True
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
        expected_dict = {
            'materials': {
                'data': [
                    {'id': sol_service_3.id, 'name': 'Material', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (1, 'Units'), 'product_id': (self.material_product.id, 'Material')}
                ],
                'displayLoadMore': False,
            },
            'service_revenues': {
                'data': [
                     {'id': sol_service_1.id, 'name': '[SERV-ORDERED2] Service Milestone', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.product_milestone.id, '[SERV-ORDERED2] Service Milestone')},
                     {'id': sol_service_2.id, 'name': '[SERV-ORDERED2] Product prepaid', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.product_prepaid.id, '[SERV-ORDERED2] Product prepaid')},
                     {'id': sol_service_4.id, 'name': '[SERV-ORDERED2] Service Delivery', 'product_uom_qty': 1.0, 'qty_delivered': 0.0, 'qty_invoiced': 0.0, 'product_uom': (4, 'Hours'), 'product_id': (self.dashboard_product_delivery_service.id, '[SERV-ORDERED2] Service Delivery')},
                ],
                'displayLoadMore': False,
            },
        }

        sale_item_data = self.dashboard_project.get_sale_items_data(limit=5)
        self.assertEqual(sale_item_data, expected_dict)
