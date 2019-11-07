# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase


class TestCrmCommon(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestCrmCommon, cls).setUpClass()

        # Create a user as 'Crm Salesmanager' and added the `sales manager` group
        cls.crm_salemanager = cls.env['res.users'].create({
            'company_id': cls.env.ref("base.main_company").id,
            'name': "Crm Sales manager",
            'login': "csm",
            'email': "crmmanager@yourcompany.com",
            'groups_id': [(6, 0, [cls.env.ref('sales_team.group_sale_manager').id])]
        })

        # Create a user as 'Crm Salesman' and added few groups
        cls.crm_salesman = cls.env['res.users'].create({
            'company_id': cls.env.ref("base.main_company").id,
            'name': "Crm Salesman",
            'login': "csu",
            'email': "crmuser@yourcompany.com",
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [cls.env.ref('sales_team.group_sale_salesman_all_leads').id, cls.env.ref('base.group_partner_manager').id])]
        })

        cls.team_sales_department = cls.env['crm.team'].create({
            'name': 'Sales',
            'company_id': False,
        })

        cls.stage_lead1 = cls.env['crm.stage'].create({
            'name': 'New',
            'sequence': 1,
        })
        cls.stage_lead2 = cls.env['crm.stage'].create({
            'name': 'Qualified',
            'sequence': 2,
        })
        cls.stage_lead3 = cls.env['crm.stage'].create({
            'name': 'Proposition',
            'sequence': 3,
        })
        cls.stage_lead4 = cls.env['crm.stage'].create({
            'name': 'Won',
            'fold': False,
            'is_won': True,
            'sequence': 70,
        })

        cls.crm_case_1 = cls.env['crm.lead'].create({
            'name': 'Club Office Furnitures',
            'type': 'lead',
            'team_id': cls.team_sales_department.id,
        })

        cls.res_partner_1 = cls.env['res.partner'].create({
            'name': 'Wood Corner'
        })
        cls.res_partner_2 = cls.env['res.partner'].create({
            'name': 'Deco Addict'
        })
        cls.res_partner_3 = cls.env['res.partner'].create({
            'name': 'Gemini Furniture'
        })