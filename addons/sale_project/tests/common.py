# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.common import TestSaleCommon


class TestSaleProjectCommon(TestSaleCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env['res.config.settings'] \
            .create({'group_project_milestone': True}) \
            .execute()

        cls.uom_hour = cls.env.ref('uom.product_uom_hour')
        cls.account_sale = cls.company_data['default_account_revenue']

        cls.analytic_plan, _other_plans = cls.env['account.analytic.plan']._get_all_plans()
        cls.analytic_account_sale = cls.env['account.analytic.account'].create({
            'name': 'Project for selling timesheet - AA',
            'code': 'AA-2030',
            'plan_id': cls.analytic_plan.id,
            'company_id': cls.company_data['company'].id,
        })
        Project = cls.env['project.project'].with_context(tracking_disable=True)
        cls.project_global = Project.create({
            'name': 'Project Global',
            'analytic_account_id': cls.analytic_account_sale.id,
            'allow_billable': True,
        })
        cls.project_template = Project.create({
            'name': 'Project TEMPLATE for services',
        })
        cls.project_template_state = cls.env['project.task.type'].create({
            'name': 'Only stage in project template',
            'sequence': 1,
            'project_ids': [(4, cls.project_template.id)]
        })

        # -- manual (delivered, manual)
        cls.product_delivery_manual1 = cls.env['product.product'].create({
            'name': "Service delivered, create no task",
            'standard_price': 11,
            'list_price': 13,
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
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
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
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
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
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
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
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
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-DELI4',
            'service_type': 'manual',
            'service_tracking': 'project_only',
            'project_id': False,
            'project_template_id': cls.project_template.id,
            'taxes_id': False,
            'property_account_income_id': cls.account_sale.id,
        })
        price_vals = {
            'standard_price': 11,
            'list_price': 13,
        }
        service_vals = {
            'type': 'service',
            'service_tracking': 'no',
            'project_id': False,
        }
        (
            cls.product_service_ordered_prepaid,
            cls.product_service_delivered_milestone,
            cls.product_service_delivered_manual,
            cls.product_consumable,
        ) = cls.env['product.product'].create([{
            'name': "Service prepaid",
            **price_vals,
            **service_vals,
            'invoice_policy': 'order',
            'service_type': 'manual',
        }, {
            'name': "Service milestone",
            **price_vals,
            **service_vals,
            'invoice_policy': 'delivery',
            'service_type': 'milestones',
        }, {
            'name': "Service manual",
            **price_vals,
            **service_vals,
            'invoice_policy': 'delivery',
            'service_type': 'manual',
        }, {
            'name': "Consumable",
            **price_vals,
            'type': 'consu',
            'invoice_policy': 'order',
        }])
        # -- devliered_milestones (delivered, milestones)
        product_milestone_vals = {
            'type': 'service',
            'invoice_policy': 'delivery',
            'uom_id': cls.uom_hour.id,
            'uom_po_id': cls.uom_hour.id,
            'default_code': 'SERV-MILES',
            'service_type': 'milestones',
            'service_tracking': 'no',
            'property_account_income_id': cls.account_sale.id,
        }
        cls.product_milestone, cls.product_milestone2 = cls.env['product.product'].create([
            {**product_milestone_vals, 'name': 'Milestone Product', 'list_price': 20},
            {**product_milestone_vals, 'name': 'Milestone Product 2', 'list_price': 15},
        ])

    def set_project_milestone_feature(self, value):
        self.env['res.config.settings'] \
            .create({'group_project_milestone': value}) \
            .execute()
