# -*- coding: utf-8 -*-

from openerp.tests import common


class TestCrmCommon(common.TransactionCase):

    def setUp(self):
        super(TestCrmCommon, self).setUp()

        # Usefull models
        self.Users = self.env['res.users']
        self.Stage = self.env['crm.stage']
        self.SalesTeam = self.env['crm.team']
        self.Lead = self.env['crm.lead']

        # User groups
        self.group_employee_id = self.env['ir.model.data'].xmlid_to_res_id('base.group_user')
        self.group_sale_manager_id = self.env['ir.model.data'].xmlid_to_res_id('base.group_sale_manager')

        # Test users to use through the various tests
        self.user_employee = self.Users.with_context({'no_reset_password': True}).create({
            'name': 'Armande Employee',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.empoyee@example.com',
            'groups_id': [(6, 0, [self.group_employee_id])]
        })
        self.user_salemanager = self.Users.with_context({'no_reset_password': True}).create({
            'name': 'Bastien SaleManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.salemanager@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_sale_manager_id])]
        })

        """ Stage behavior with salesteam """
        # delete existing stages
        self.Stage.search([]).unlink()

        # create test stages
        self.stage_copy_1 = self.Stage.create({
            'name': 'TestDuplicated',
            'default': 'copy',
        })
        self.stage_link_1 = self.Stage.create({
            'name': 'TestShared',
            'default': 'link',
        })
        self.stage_none_1 = self.Stage.create({
            'name': 'TestFreelance',
            'default': 'none',
        })
        self.stage_specific_1 = self.Stage.create({
            'name': 'TestAlone',
            'default': 'specific',
        })
