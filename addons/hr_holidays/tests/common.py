# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class TestHrHolidaysBase(common.TransactionCase):

    def setUp(self):
        super(TestHrHolidaysBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.hr_employee = self.registry('hr.employee')
        self.hr_holidays = self.registry('hr.holidays')
        self.hr_holidays_status = self.registry('hr.holidays.status')
        self.res_users = self.registry('res.users')
        self.res_partner = self.registry('res.partner')

        # Find Employee group
        group_employee_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_user')
        self.group_employee_id = group_employee_ref and group_employee_ref[1] or False

        # Find Hr User group
        group_hr_user_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_hr_user')
        self.group_hr_user_ref_id = group_hr_user_ref and group_hr_user_ref[1] or False

        # Find Hr Manager group
        group_hr_manager_ref = self.registry('ir.model.data').get_object_reference(cr, uid, 'base', 'group_hr_manager')
        self.group_hr_manager_ref_id = group_hr_manager_ref and group_hr_manager_ref[1] or False

        # Test partners to use through the various tests
        self.hr_partner_id = self.res_partner.create(cr, uid, {
            'name': 'Gertrude AgrolaitPartner',
            'email': 'gertrude.partner@agrolait.com',
        })
        self.email_partner_id = self.res_partner.create(cr, uid, {
            'name': 'Patrick Ratatouille',
            'email': 'patrick.ratatouille@agrolait.com',
        })

        # Test users to use through the various tests
        self.user_hruser_id = self.res_users.create(cr, uid, {
            'name': 'Armande HrUser',
            'login': 'Armande',
            'alias_name': 'armande',
            'email': 'armande.hruser@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_hr_user_ref_id])]
        }, {'no_reset_password': True})
        self.user_hrmanager_id = self.res_users.create(cr, uid, {
            'name': 'Bastien HrManager',
            'login': 'bastien',
            'alias_name': 'bastien',
            'email': 'bastien.hrmanager@example.com',
            'groups_id': [(6, 0, [self.group_employee_id, self.group_hr_manager_ref_id])]
        }, {'no_reset_password': True})
        self.user_none_id = self.res_users.create(cr, uid, {
            'name': 'Charlie Avotbonkeur',
            'login': 'charlie',
            'alias_name': 'charlie',
            'email': 'charlie.noone@example.com',
            'groups_id': [(6, 0, [])]
        }, {'no_reset_password': True})
        self.user_employee_id = self.res_users.create(cr, uid, {
            'name': 'David Employee',
            'login': 'david',
            'alias_name': 'david',
            'email': 'david.employee@example.com',
            'groups_id': [(6, 0, [self.group_employee_id])]
        }, {'no_reset_password': True})

        # Hr Data
        self.employee_emp_id = self.hr_employee.create(cr, uid, {
            'name': 'David Employee',
            'user_id': self.user_employee_id,
        })
        self.employee_hruser_id = self.hr_employee.create(cr, uid, {
            'name': 'Armande HrUser',
            'user_id': self.user_hruser_id,
        })
