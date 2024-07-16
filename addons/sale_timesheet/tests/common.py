# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_project.tests.common import TestSaleProjectCommon


class TestCommonSaleTimesheet(TestSaleProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

        cls.user_employee_company_B = mail_new_test_user(
            cls.env,
            name='Gregor Clegane Employee',
            login='gregor',
            email='gregor@example.com',
            notification_type='email',
            groups='base.group_user',
            company_id=cls.company_data_2['company'].id,
            company_ids=[cls.company_data_2['company'].id],
        )
        cls.user_manager_company_B = mail_new_test_user(
            cls.env,
            name='Cersei Lannister Manager',
            login='cersei',
            email='cersei@example.com',
            notification_type='email',
            groups='base.group_user',
            company_id=cls.company_data_2['company'].id,
            company_ids=[cls.company_data_2['company'].id, cls.env.company.id],
        )

        cls.employee_user = cls.env['hr.employee'].create({
            'name': 'Employee User',
            'hourly_cost': 15,
        })
        cls.employee_manager = cls.env['hr.employee'].create({
            'name': 'Employee Manager',
            'hourly_cost': 45,
        })

        cls.employee_company_B = cls.env['hr.employee'].create({
            'name': 'Gregor Clegane',
            'user_id': cls.user_employee_company_B.id,
            'hourly_cost': 15,
        })

        cls.manager_company_B = cls.env['hr.employee'].create({
            'name': 'Cersei Lannister',
            'user_id': cls.user_manager_company_B.id,
            'hourly_cost': 45,
        })

        # Account and project
        cls.analytic_account_sale.name = 'Project for selling timesheet - AA'
        cls.analytic_plan, _other_plans = cls.env['account.analytic.plan']._get_all_plans()
        cls.analytic_account_sale_company_B = cls.env['account.analytic.account'].create({
            'name': 'Project for selling timesheet Company B - AA',
            'code': 'AA-2030',
            'plan_id': cls.analytic_plan.id,
            'company_id': cls.company_data_2['company'].id,
        })

        # Create projects
        Project = cls.env['project.project']
        cls.project_global.write({
            'name': 'Project for selling timesheets',
            'allow_timesheets': True,
        })
        cls.project_template.write({
            'name': 'Project TEMPLATE for services',
        })
        # Projects: at least one per billable type
        cls.project_task_rate = Project.create({
            'name': 'Project with pricing_type="task_rate"',
            'allow_timesheets': True,
            'allow_billable': True,
            'partner_id': cls.partner_b.id,
            'account_id': cls.analytic_account_sale.id,
        })

        cls.project_subtask = Project.create({
            'name': "Sub Task Project (non billable)",
            'allow_timesheets': True,
            'allow_billable': False,
            'partner_id': False,
        })
        cls.project_non_billable = Project.create({
            'name': "Non Billable Project",
            'allow_timesheets': True,
            'allow_billable': False,
            'partner_id': False,
        })

        # Create service products

        # -- ordered quantities (ordered, timesheet)
        cls.product_order_timesheet1 = cls.env['product.product'].create({
            'name': "Service Ordered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED1',
            'service_type': 'timesheet',
            'service_tracking': 'no',
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_order_timesheet2 = cls.env['product.product'].create({
            'name': "Service Ordered, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED2',
            'service_type': 'timesheet',
            'service_tracking': 'task_global_project',
            'project_id': cls.project_global.id,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_order_timesheet3 = cls.env['product.product'].create({
            'name': "Service Ordered, create task in new project",
            'standard_price': 10,
            'list_price': 20,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED3',
            'service_type': 'timesheet',
            'service_tracking': 'task_in_project',
            'project_id': False,  # will create a project
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_order_timesheet4 = cls.env['product.product'].create({
            'name': "Service Ordered, create project only",
            'standard_price': 15,
            'list_price': 30,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED4',
            'service_type': 'timesheet',
            'service_tracking': 'project_only',
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_order_timesheet5 = cls.env['product.product'].create({
            'name': "Service Ordered, create project only based on template",
            'standard_price': 17,
            'list_price': 34,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-ORDERED4',
            'service_type': 'timesheet',
            'service_tracking': 'project_only',
            'project_id': False,
            'project_template_id': cls.project_template.id,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })

        # -- timesheet on tasks (delivered, timesheet)
        cls.product_delivery_timesheet1 = cls.env['product.product'].create({
            'name': "Service delivered, create no task",
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
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_delivery_timesheet2 = cls.env['product.product'].create({
            'name': "Service delivered, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-DELI2',
            'service_type': 'timesheet',
            'service_tracking': 'task_global_project',
            'project_id': cls.project_global.id,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_delivery_timesheet3 = cls.env['product.product'].create({
            'name': "Service delivered, create task in new project",
            'standard_price': 10,
            'list_price': 20,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-DELI3',
            'service_type': 'timesheet',
            'service_tracking': 'task_in_project',
            'project_id': False,  # will create a project
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_delivery_timesheet4 = cls.env['product.product'].create({
            'name': "Service delivered, create project only",
            'standard_price': 15,
            'list_price': 30,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-DELI4',
            'service_type': 'timesheet',
            'service_tracking': 'project_only',
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_delivery_timesheet5 = cls.env['product.product'].create({
            'name': "Service delivered, create project only based on template",
            'standard_price': 17,
            'list_price': 34,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-DELI5',
            'service_type': 'timesheet',
            'service_tracking': 'project_only',
            'project_template_id': cls.project_template.id,
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_service_delivered_timesheet = cls.env['product.product'].create({
            'name': "Service timesheet",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'service_tracking': 'no',
            'project_id': False,
            'invoice_policy': 'delivery',
            'service_type': 'timesheet',
        })

    def setUp(self):
        super().setUp()
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner_b.id,
            'partner_invoice_id': self.partner_b.id,
            'partner_shipping_id': self.partner_b.id,
        })
        self.env['sale.order.line'].create([{
            'order_id': self.so.id,
            'product_id': self.product_delivery_timesheet1.id,
            'product_uom_qty': 10,
        }, {
            'order_id': self.so.id,
            'product_id': self.product_delivery_timesheet2.id,
            'product_uom_qty': 5,
        }, {
            'order_id': self.so.id,
            'product_id': self.product_delivery_timesheet3.id,
            'product_uom_qty': 5,
        }, {
            'order_id': self.so.id,
            'product_id': self.product_order_timesheet1.id,
            'product_uom_qty': 2,
        }])
        self.so.action_confirm()
