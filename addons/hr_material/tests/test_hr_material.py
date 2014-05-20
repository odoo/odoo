# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
import time


class TestHrMaterial(TransactionCase):
    """ Test used to check that when doing material/maintenance_request/material_category creation."""

    def setUp(self):
        super(TestHrMaterial, self).setUp()
        self.maintenance_request_stage_obj = self.env['hr.material.stage']
        self.material_category_obj = self.env['hr.material.category']
        self.material_obj = self.env['hr.material']
        self.maintenance_request_obj = self.env['hr.material.request']
        self.res_user_model = self.env['res.users']
        self.main_company = self.env.ref('base.main_company')
        res_hr_user = self.env.ref('base.group_user')
        res_hr_manager = self.env.ref('base.group_hr_manager')

        self.hr_user = self.res_user_model.create(dict(
            name="Normal user/Employee",
            company_id=self.main_company.id,
            login="emp",
            password="emp",
            email="empuser@yourcompany.com",
            groups_id=[(6, 0, [res_hr_user.id])]
        ))

        self.hr_manager = self.res_user_model.create(dict(
            name="HR Manager",
            company_id=self.main_company.id,
            login="hm",
            password="hm",
            email="hrmanager@yourcompany.com",
            groups_id=[(6, 0, [res_hr_manager.id])]
        ))

    def test_hr_material_request_category(self):
        # I will create material detail with using manager access rights
        # because account manager can only create material details.

        material_info_value = {
            'name': 'Samsung Monitor "15',
            'category_id': self.ref('hr_material.hr_material_monitor'),
            'employee_id': self.ref('hr.employee_al'),
            'user_id': self.ref('base.user_root'),
            'assign_date': time.strftime('%Y-%m-%d'),
            'serial_no': 'MT/127/18291015',
            'model': 'NP355E5X',
            'color': 3,
        }

        material_01 = self.material_obj.sudo(self.hr_manager).create(material_info_value)

        # I check that material is create or not.
        assert material_01, "Material not created"

        maintenance_request_value = {
            'name': 'Resolution is bad',
            'user_id': self.hr_user.id,
            'employee_id': self.ref('hr.employee_qdp'),
            'material_id': material_01.id,
            'category_id': self.ref('hr_material.hr_material_monitor'),
            'color': 7,
            'stage_id': self.ref('hr_material.stage_0')
        }

        maintenance_request_01 = self.maintenance_request_obj.sudo(self.hr_user).create(maintenance_request_value)

        # I check that maintenance_request is create or not.
        assert maintenance_request_01, "Maintenance Request not created"

        # I check that Initially maintenance request is in the "New Request" stage
        self.assertEquals(maintenance_request_01.stage_id.id, self.ref('hr_material.stage_0'))

        # I check that change the maintenance_request stage on click statusbar
        maintenance_request_01.sudo(self.hr_user).write({'stage_id': self.ref('hr_material.stage_1')})

        # I check that maintenance request is in the "In Progress" stage
        self.assertEquals(maintenance_request_01.stage_id.id, self.ref('hr_material.stage_1'))
