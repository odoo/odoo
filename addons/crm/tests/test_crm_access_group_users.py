# -*- coding: utf-8 -*-

from odoo.tests import common


class TestCrmAccessGroupUsers(common.TransactionCase):

    def setUp(self):
        super(TestCrmAccessGroupUsers, self).setUp()
        """ Tests for Access Group Users """

        self.ResUsers = self.env['res.users']
        self.CrmLead = self.env['crm.lead']

        sale_manager_group_id = self.ref('base.group_sale_manager')
        all_leads_group_id = self.ref('base.group_sale_salesman_all_leads')
        partner_manager_group_id = self.ref('base.group_partner_manager')

        # Create a user as 'Crm Salesmanager'
        self.crm_salemanager_id = self.ResUsers.create({
            'company_id': self.ref("base.main_company"),
            'name': "Crm Sales manager",
            'login': "csm",
            'email': "crmmanager@yourcompany.com",
            'groups_id': [(6, 0, [sale_manager_group_id])]
        }).id

        # Create a user as 'Crm Salesman'
        self.crm_salesman_id = self.ResUsers.create({
            'company_id': self.ref("base.main_company"),
            'name': "Crm Salesman",
            'login': "csu",
            'email': "crmuser@yourcompany.com",
            'groups_id': [(6, 0, [all_leads_group_id, partner_manager_group_id])]
        }).id
