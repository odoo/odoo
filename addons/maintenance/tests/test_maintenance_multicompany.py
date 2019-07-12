# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestEquipmentMulticompany(TransactionCase):

    def test_00_equipment_multicompany_user(self):
        """Test Check maintenance with equipment manager and user in multi company environment"""

        # Use full models
        Equipment = self.env['maintenance.equipment']
        MaintenanceRequest = self.env['maintenance.request']
        Category = self.env['maintenance.equipment.category']
        ResUsers = self.env['res.users']
        ResCompany = self.env['res.company']
        MaintenanceTeam = self.env['maintenance.team']

        # Use full reference.
        group_user = self.env.ref('base.group_user')
        group_manager = self.env.ref('maintenance.group_equipment_manager')

        # Company A
        company_a = ResCompany.create({
            'name': 'Company A',
            'currency_id': self.env.ref('base.USD').id,
        })

        # Create one child company having parent company is 'Your company'
        company_b = ResCompany.create({
            'name': 'Company B',
            'currency_id': self.env.ref('base.USD').id,
        })

        # Create equipment manager.
        cids = [company_a.id, company_b.id] 
        equipment_manager = ResUsers.create({
            'name': 'Equipment Manager',
            'company_id': company_a.id,
            'login': 'e_equipment_manager',
            'email': 'eqmanager@yourcompany.example.com',
            'groups_id': [(6, 0, [group_manager.id])],
            'company_ids': [(6, 0, [company_a.id, company_b.id])]
        })

        # Create equipment user
        user = ResUsers.create({
            'name': 'Normal User/Employee',
            'company_id': company_b.id,
            'login': 'emp',
            'email': 'empuser@yourcompany.example.com',
            'groups_id': [(6, 0, [group_user.id])],
            'company_ids': [(6, 0, [company_b.id])]
        })

        # create a maintenance team for company A user
        team = MaintenanceTeam.with_user(equipment_manager).create({
            'name': 'Metrology',
            'company_id': company_a.id,
        })
        # create a maintenance team for company B user
        teamb = MaintenanceTeam.with_user(equipment_manager).with_context(allowed_company_ids=cids).create({
            'name': 'Subcontractor',
            'company_id': company_b.id,
        })

        # User should not able to create equipment category.
        with self.assertRaises(AccessError):
            Category.with_user(user).create({
                'name': 'Software',
                'company_id': company_b.id,
                'technician_user_id': user.id,
            })

        # create equipment category for equipment manager
        category_1 = Category.with_user(equipment_manager).with_context(allowed_company_ids=cids).create({
            'name': 'Monitors',
            'company_id': company_b.id,
            'technician_user_id': equipment_manager.id,
        })

        # create equipment category for equipment manager
        Category.with_user(equipment_manager).with_context(allowed_company_ids=cids).create({
            'name': 'Computers',
            'company_id': company_b.id,
            'technician_user_id': equipment_manager.id,
        })

        # create equipment category for equipment user
        Category.with_user(equipment_manager).create({
            'name': 'Phones',
            'company_id': company_a.id,
            'technician_user_id': equipment_manager.id,
        })

        # Check category for user equipment_manager and user
        self.assertEquals(Category.with_user(equipment_manager).with_context(allowed_company_ids=cids).search_count([]), 3)
        self.assertEquals(Category.with_user(user).search_count([]), 2)

        # User should not able to create equipment.
        with self.assertRaises(AccessError):
            Equipment.with_user(user).create({
                'name': 'Samsung Monitor 15',
                'category_id': category_1.id,
                'assign_date': time.strftime('%Y-%m-%d'),
                'company_id': company_b.id,
                'owner_user_id': user.id,
            })

        Equipment.with_user(equipment_manager).with_context(allowed_company_ids=cids).create({
            'name': 'Acer Laptop',
            'category_id': category_1.id,
            'assign_date': time.strftime('%Y-%m-%d'),
            'company_id': company_b.id,
            'owner_user_id': user.id,
        })

        # create an equipment for user
        Equipment.with_user(equipment_manager).with_context(allowed_company_ids=cids).create({
            'name': 'HP Laptop',
            'category_id': category_1.id,
            'assign_date': time.strftime('%Y-%m-%d'),
            'company_id': company_b.id,
            'owner_user_id': equipment_manager.id,
        })
        # Now there are total 2 equipments created and can view by equipment_manager user
        self.assertEquals(Equipment.with_user(equipment_manager).with_context(allowed_company_ids=cids).search_count([]), 2)

        # And there is total 1 equipment can be view by Normal User ( Which user is followers)
        self.assertEquals(Equipment.with_user(user).search_count([]), 1)

        # create an equipment team BY user
        with self.assertRaises(AccessError):
            MaintenanceTeam.with_user(user).create({
                'name': 'Subcontractor',
                'company_id': company_b.id,
            })

        # create an equipment category BY user
        with self.assertRaises(AccessError):
            Category.with_user(user).create({
                'name': 'Computers',
                'company_id': company_b.id,
                'technician_user_id': user.id,
            })

        # create an maintenance stage BY user
        with self.assertRaises(AccessError):
            self.env['maintenance.stage'].with_user(user).create({
                'name': 'identify corrective maintenance requirements',
            })

        # Create an maintenance request for ( User Follower ).
        MaintenanceRequest.with_user(user).create({
            'name': 'Some keys are not working',
            'company_id': company_b.id,
            'user_id': user.id,
            'owner_user_id': user.id,
        })

        # Create an maintenance request for equipment_manager (Admin Follower)
        MaintenanceRequest.with_user(equipment_manager).create({
            'name': 'Battery drains fast',
            'company_id': company_a.id,
            'user_id': equipment_manager.id,
            'owner_user_id': equipment_manager.id,
        })

        # Now here is total 1 maintenance request can be view by Normal User
        self.assertEquals(MaintenanceRequest.with_user(equipment_manager).with_context(allowed_company_ids=cids).search_count([]), 2)
        self.assertEquals(MaintenanceRequest.with_user(user).search_count([]), 1)
