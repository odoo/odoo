# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://www.openerp.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
