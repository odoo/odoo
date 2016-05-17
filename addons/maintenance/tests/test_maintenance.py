# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
import time


class TestHrEquipment(TransactionCase):
    """ Test used to check that when doing equipment/maintenance_request/equipment_category creation."""

    def setUp(self):
        super(TestHrEquipment, self).setUp()
        self.equipment = self.env['hr.equipment']
        self.maintenance_request = self.env['hr.equipment.request']
        self.user = self.env['res.users']
        self.main_company = self.env.ref('base.main_company')
        res_hr_user = self.env.ref('base.group_user')
        res_hr_manager = self.env.ref('base.group_hr_manager')

        self.hr_user = self.user.create(dict(
            name="Normal User/Employee",
            company_id=self.main_company.id,
            login="emp",
            password="emp",
            email="empuser@yourcompany.example.com",
            groups_id=[(6, 0, [res_hr_user.id])]
        ))
        self.env.ref('hr.employee_qdp').write({'user_id': self.hr_user.id})

        self.hr_manager = self.user.create(dict(
            name="HR Manager",
            company_id=self.main_company.id,
            login="hm",
            password="hm",
            email="hrmanager@yourcompany.example.com",
            groups_id=[(6, 0, [res_hr_manager.id])]
        ))

    def test_hr_equipment_request_category(self):

        # Create a new equipment
        equipment_01 = self.equipment.sudo(self.hr_manager).create({
            'name': 'Samsung Monitor "15',
            'category_id': self.ref('hr_equipment.hr_equipment_monitor'),
            'employee_id': self.ref('hr.employee_qdp'),
            'user_id': self.ref('base.user_root'),
            'assign_date': time.strftime('%Y-%m-%d'),
            'serial_no': 'MT/127/18291015',
            'model': 'NP355E5X',
            'color': 3,
        })

        # Check that equipment is created or not
        assert equipment_01, "Equipment not created"

        # Create new maintenance request
        maintenance_request_01 = self.maintenance_request.sudo(self.hr_user).create({
            'name': 'Resolution is bad',
            'user_id': self.hr_user.id,
            'employee_id': self.ref('hr.employee_qdp'),
            'equipment_id': equipment_01.id,
            'category_id': self.ref('hr_equipment.hr_equipment_monitor'),
            'color': 7,
            'stage_id': self.ref('hr_equipment.stage_0')
        })

        # I check that maintenance_request is created or not
        assert maintenance_request_01, "Maintenance Request not created"

        # I check that Initially maintenance request is in the "New Request" stage
        self.assertEquals(maintenance_request_01.stage_id.id, self.ref('hr_equipment.stage_0'))

        # I check that change the maintenance_request stage on click statusbar
        maintenance_request_01.sudo(self.hr_user).write({'stage_id': self.ref('hr_equipment.stage_1')})

        # I check that maintenance request is in the "In Progress" stage
        self.assertEquals(maintenance_request_01.stage_id.id, self.ref('hr_equipment.stage_1'))
