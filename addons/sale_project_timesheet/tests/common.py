# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestCommonSaleNoChart


class TestCommonSaleTimesheetNoChart(TestCommonSaleNoChart):

    @classmethod
    def setUpEmployees(cls):
        # Create employees
        cls.employee_user = cls.env['hr.employee'].create({
            'name': 'Employee User',
            'timesheet_cost': 15,
        })
        cls.employee_manager = cls.env['hr.employee'].create({
            'name': 'Employee Manager',
            'timesheet_cost': 45,
        })

    @classmethod
    def setUpServiceProducts(cls):
        """ Create Service product for all kind, with each tracking policy. """
        # Account and project
        cls.account_sale = cls.env['account.account'].create({
            'code': 'SERV-2020',
            'name': 'Product Sales - (test)',
            'reconcile': True,
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
        })
        cls.analytic_account_sale = cls.env['account.analytic.account'].create({
            'name': 'Project for selling timesheet - AA',
            'code': 'AA-2030'
        })

        # Create projects
        cls.project_global = cls.env['project.project'].create({
            'name': 'Project for selling timesheets',
            'allow_timesheets': True,
            'analytic_account_id': cls.analytic_account_sale.id,
        })
        cls.project_template = cls.env['project.project'].create({
            'name': 'Project TEMPLATE for services',
            'allow_timesheets': True,
        })
        cls.project_template_state = cls.env['project.task.type'].create({
            'name': 'Only stage in project template',
            'sequence': 1,
            'project_ids': [(4, cls.project_template.id)]
        })

        # Create service products
        uom_hour = cls.env.ref('uom.product_uom_hour')

        # -- ordered quantities (ordered, timesheet)
        cls.product_order_timesheet1 = cls.env['product.product'].create({
            'name': "Service Ordered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
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
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
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
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
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
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
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
            'uom_id': cls.env.ref('uom.product_uom_hour').id,
            'uom_po_id': cls.env.ref('uom.product_uom_hour').id,
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
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
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
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
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
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
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
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
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
            'uom_id': cls.env.ref('uom.product_uom_hour').id,
            'uom_po_id': cls.env.ref('uom.product_uom_hour').id,
            'default_code': 'SERV-DELI4',
            'service_type': 'timesheet',
            'service_tracking': 'project_only',
            'project_template_id': cls.project_template.id,
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })

        # -- milestones (delivered, manual)
        cls.product_delivery_manual1 = cls.env['product.product'].create({
            'name': "Service delivered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-DELI1',
            'service_type': 'manual',
            'service_tracking': 'no',
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_delivery_manual2 = cls.env['product.product'].create({
            'name': "Service delivered, create task in global project",
            'standard_price': 30,
            'list_price': 90,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-DELI2',
            'service_type': 'manual',
            'service_tracking': 'task_global_project',
            'project_id': cls.project_global.id,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_delivery_manual3 = cls.env['product.product'].create({
            'name': "Service delivered, create task in new project",
            'standard_price': 10,
            'list_price': 20,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-DELI3',
            'service_type': 'manual',
            'service_tracking': 'task_in_project',
            'project_id': False,  # will create a project
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_delivery_manual4 = cls.env['product.product'].create({
            'name': "Service delivered, create project only",
            'standard_price': 15,
            'list_price': 30,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': uom_hour.id,
            'uom_po_id': uom_hour.id,
            'default_code': 'SERV-DELI4',
            'service_type': 'manual',
            'service_tracking': 'project_only',
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        cls.product_delivery_manual5 = cls.env['product.product'].create({
            'name': "Service delivered, create project only with template",
            'standard_price': 17,
            'list_price': 34,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.env.ref('uom.product_uom_hour').id,
            'uom_po_id': cls.env.ref('uom.product_uom_hour').id,
            'default_code': 'SERV-DELI4',
            'service_type': 'manual',
            'service_tracking': 'project_only',
            'project_id': False,
            'project_template_id': cls.project_template.id,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
