# -*- coding: utf-8 -*-

from openerp.tests import common

class TestCrmAccessGroupUsers(common.TransactionCase):

    def setUp(self):
        super(TestCrmAccessGroupUsers, self).setUp()
        """ Tests for Access Group Users """
        ResUsers = self.env['res.users']
        SaleManager = self.env.ref('base.group_sale_manager')
        SaleManAllLeads = self.env.ref('base.group_sale_salesman_all_leads')
        PartnerManager = self.env.ref('base.group_partner_manager')

        # Create a user as 'Crm Salesmanager'
        self.crm_res_users_salesmanager = ResUsers.create(
            dict(
                company_id=self.env.ref("base.main_company").id,
                name="Crm Sales manager",
                login="csm",
                password="csm",
                email="crmmanager@yourcompany.com",
                groups_id=[(6, 0, SaleManager.ids)],
            ))

        # Create a user as 'Crm Salesman'
        self.crm_res_users_salesman = ResUsers.create(
            dict(
                company_id=self.env.ref("base.main_company").id,
                name="Crm Salesman",
                login="csu",
                password="csu",
                email="crmuser@yourcompany.com",
                groups_id=[(6, 0, [SaleManAllLeads.id, PartnerManager.id])],
            ))
