# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo.tests.common import TransactionCase
from dateutil import relativedelta
import datetime

class TestEquipment(TransactionCase):
    """ Test used to check that when doing equipment/maintenance_request/equipment_category creation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.equipment = cls.env['maintenance.equipment']
        cls.maintenance_request = cls.env['maintenance.request']
        cls.res_users = cls.env['res.users']
        cls.maintenance_team = cls.env['maintenance.team']
        cls.main_company = cls.env.ref('base.main_company')
        res_user = cls.env.ref('base.group_user')
        res_manager = cls.env.ref('maintenance.group_equipment_manager')

        cls.user = cls.res_users.create(dict(
            name="Normal User/Employee",
            company_id=cls.main_company.id,
            login="emp",
            email="empuser@yourcompany.example.com",
            groups_id=[(6, 0, [res_user.id])]
        ))

        cls.manager = cls.res_users.create(dict(
            name="Equipment Manager",
            company_id=cls.main_company.id,
            login="hm",
            email="eqmanager@yourcompany.example.com",
            groups_id=[(6, 0, [res_manager.id])]
        ))

        cls.equipment_monitor = cls.env['maintenance.equipment.category'].create({
            'name': 'Monitors - Test',
        })

    def test_10_equipment_request_category(self):

        # Create a new equipment
        equipment_01 = self.equipment.with_user(self.manager).create({
            'name': 'Samsung Monitor "15',
            'category_id': self.equipment_monitor.id,
            'technician_user_id': self.ref('base.user_root'),
            'owner_user_id': self.user.id,
            'assign_date': time.strftime('%Y-%m-%d'),
            'serial_no': 'MT/127/18291015',
            'model': 'NP355E5X',
            'color': 3,
        })

        # Check that equipment is created or not
        assert equipment_01, "Equipment not created"

        # Create new maintenance request
        maintenance_request_01 = self.maintenance_request.with_user(self.user).create({
            'name': 'Resolution is bad',
            'user_id': self.user.id,
            'owner_user_id': self.user.id,
            'equipment_id': equipment_01.id,
            'color': 7,
            'stage_id': self.ref('maintenance.stage_0'),
            'maintenance_team_id': self.ref('maintenance.equipment_team_maintenance')
        })

        # I check that maintenance_request is created or not
        assert maintenance_request_01, "Maintenance Request not created"

        # I check that Initially maintenance request is in the "New Request" stage
        self.assertEqual(maintenance_request_01.stage_id.id, self.ref('maintenance.stage_0'))

        # I check that change the maintenance_request stage on click statusbar
        maintenance_request_01.with_user(self.user).write({'stage_id': self.ref('maintenance.stage_1')})

        # I check that maintenance request is in the "In Progress" stage
        self.assertEqual(maintenance_request_01.stage_id.id, self.ref('maintenance.stage_1'))

    def test_20_cron(self):
        """ Check the cron creates the necessary preventive maintenance requests"""
        equipment_cron = self.equipment.create({
            'name': 'High Maintenance Monitor because of Color Calibration',
            'category_id': self.equipment_monitor.id,
            'technician_user_id': self.ref('base.user_root'),
            'owner_user_id': self.user.id,
            'assign_date': time.strftime('%Y-%m-%d'),
            'period': 7,
            'color': 3,
        })

        maintenance_request_cron = self.maintenance_request.create({
            'name': 'Need a special calibration',
            'user_id': self.user.id,
            'request_date': (datetime.datetime.now() + relativedelta.relativedelta(days=7)).strftime('%Y-%m-%d'),
            'maintenance_type': 'preventive',
            'owner_user_id': self.user.id,
            'equipment_id': equipment_cron.id,
            'color': 7,
            'stage_id': self.ref('maintenance.stage_0'),
            'maintenance_team_id': self.ref('maintenance.equipment_team_maintenance')
        })

        self.env['maintenance.equipment']._cron_generate_requests()
        # As it is generating the requests for one month in advance, we should have 4 requests in total
        tot_requests = self.maintenance_request.search([('equipment_id', '=', equipment_cron.id)])
        self.assertEqual(len(tot_requests), 1, 'The cron should have generated just 1 request for the High Maintenance Monitor.')

    def test_21_cron(self):
        """ Check the creation of maintenance requests by the cron"""

        team_test = self.maintenance_team.create({
            'name': 'team_test',
        })
        equipment = self.equipment.create({
            'name': 'High Maintenance Monitor because of Color Calibration',
            'category_id': self.equipment_monitor.id,
            'technician_user_id': self.ref('base.user_root'),
            'owner_user_id': self.user.id,
            'assign_date': time.strftime('%Y-%m-%d'),
            'period': 7,
            'color': 3,
            'maintenance_team_id': team_test.id,
            'maintenance_duration': 3.0,
        })

        self.env['maintenance.equipment']._cron_generate_requests()
        tot_requests = self.maintenance_request.search([('equipment_id', '=', equipment.id)])
        self.assertEqual(len(tot_requests), 1, 'The cron should have generated just 1 request for the High Maintenance Monitor.')
        self.assertEqual(tot_requests.maintenance_team_id.id, team_test.id, 'The maintenance team should be the same as equipment one')
        self.assertEqual(tot_requests.duration, 3.0, 'Equipement maintenance duration is not the same as the request one')
