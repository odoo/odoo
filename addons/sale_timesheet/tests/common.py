# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class CommonTest(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(CommonTest, cls).setUpClass()

        # Create accounts
        cls.account_debit = cls.env['account.account'].create({
            'code': 'X1012',
            'name': 'Debtors - (test)',
            'reconcile': True,
            'user_type_id': cls.env.ref('account.data_account_type_receivable').id,
        })
        cls.account_credit = cls.env['account.account'].create({
            'code': 'X1111',
            'name': 'Creditors - (test)',
            'reconcile': True,
            'user_type_id': cls.env.ref('account.data_account_type_payable').id,
        })
        cls.account_sale = cls.env['account.account'].create({
            'code': 'X2020',
            'name': 'Product Sales - (test)',
            'reconcile': True,
            'user_type_id': cls.env.ref('account.data_account_type_revenue').id,
        })

        # Create project
        cls.project_global = cls.env['project.project'].create({
            'name': 'Project for selling timesheets',
            'allow_timesheets': True,
        })

        # Create service products

        # -- ordered quantities (ordered, timesheet)
        cls.product_order_timesheet1 = cls.env['product.product'].create({
            'name': "Service Ordered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'order',
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-ORDERED3',
            'service_type': 'timesheet',
            'service_tracking': 'task_new_project',
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-ORDERED4',
            'service_type': 'timesheet',
            'service_tracking': 'project_only',
            'project_id': False,
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI3',
            'service_type': 'timesheet',
            'service_tracking': 'task_new_project',
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI4',
            'service_type': 'timesheet',
            'service_tracking': 'project_only',
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })

        # -- milestons (delivered, manual)
        cls.product_delivery_manual1 = cls.env['product.product'].create({
            'name': "Service delivered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI3',
            'service_type': 'manual',
            'service_tracking': 'task_new_project',
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
            'uom_id': cls.env.ref('product.product_uom_hour').id,
            'uom_po_id': cls.env.ref('product.product_uom_hour').id,
            'default_code': 'SERV-DELI4',
            'service_type': 'manual',
            'service_tracking': 'project_only',
            'project_id': False,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })

        # Create pricelists
        cls.pricelist_usd = cls.env['product.pricelist'].create({
            'name': 'USD pricelist',
            'active': True,
            'currency_id': cls.env.ref('base.USD').id,
            'company_id': cls.env.user.company_id.id,
        })

        cls.bank_journal_euro = cls.env['account.journal'].create({
            'name': 'Sale Journal - Test',
            'type': 'sale',
            'code': 'SJT',
            'currency_id': cls.env.ref('base.EUR').id,
        })

        cls.bank_journal_usd = cls.env['account.journal'].create({
            'name': 'Sale Journal - Test US',
            'type': 'sale',
            'code': 'SJTU',
            'currency_id': cls.env.ref('base.USD').id,
        })

        cls.pricelist_eur = cls.env['product.pricelist'].create({
            'name': 'EUR pricelist',
            'active': True,
            'currency_id': cls.env.ref('base.EUR').id,
            'company_id': cls.env.user.company_id.id,
        })

        # Create partners
        cls.partner_usd = cls.env['res.partner'].create({
            'name': 'Cool Partner in USD',
            'email': 'partner.usd@test.com',
            'property_product_pricelist': cls.pricelist_usd.id,
            'property_account_payable_id': cls.account_credit.id,
            'property_account_receivable_id': cls.account_debit.id,
        })
        cls.partner_eur = cls.env['res.partner'].create({
            'name': 'Cool partner in EUR',
            'email': 'partner.eur@test.com',
            'property_product_pricelist': cls.pricelist_eur.id,
            'property_account_payable_id': cls.account_credit.id,
            'property_account_receivable_id': cls.account_debit.id,
        })

        # Create employees
        cls.employee_user = cls.env['hr.employee'].create({
            'name': 'Employee User',
            'timesheet_cost': 15,
        })
        cls.employee_manager = cls.env['hr.employee'].create({
            'name': 'Employee Manager',
            'timesheet_cost': 45,
        })
