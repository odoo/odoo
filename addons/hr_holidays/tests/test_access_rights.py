# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import tests
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysBase
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tools import mute_logger


@tests.tagged('access_rights')
class TestLeavesRights(TestHrHolidaysBase):

    def setUp(self):
        super(TestLeavesRights, self).setUp()
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Unlimited',
            'validation_type': 'hr',
            'allocation_type': 'no',
            'validity_start': False,
        })
        self.rd_dept.manager_id = False
        self.hr_dept.manager_id = False
        self.employee_emp.parent_id = False
        self.employee_leave = self.env['hr.leave'].sudo(self.user_employee_id).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_emp.department_id.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_messaging_by_user(self):
        """ User may communicate on its own leaves, even if validated """
        self.employee_leave.sudo(self.user_employee_id).message_post(
            body='I haz messaging',
            subtype='mail.mt_comment',
            message_type='comment'
        )

        self.employee_leave.sudo(self.user_hrmanager_id).action_approve()

        self.employee_leave.sudo(self.user_employee_id).message_post(
            body='I still haz messaging',
            subtype='mail.mt_comment',
            message_type='comment'
        )

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_other(self):
        """ Users should be able to read other people requests except name field """
        other_leave = self.env['hr.leave'].sudo(self.user_hruser).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })
        res = other_leave.sudo(self.user_employee_id).read(['number_of_days', 'state', 'name'])
        self.assertEqual(
            res[0]['name'], '*****',
            'Private information should have been stripped, received %s instead' % res[0]['name']
        )

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_other_browse(self):
        """ Users should be able to browse other people requests except name field """
        other_leave = self.env['hr.leave'].sudo(self.user_hruser).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })
        self.assertEqual(
            other_leave.sudo(self.user_employee_id).name, '*****',
            'Private information should have been stripped, received %s instead' % other_leave.sudo(self.user_employee_id).name
        )

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_own(self):
        """ Users should be able to read name field of own requests """
        res = self.employee_leave.read(['name', 'number_of_days', 'state'])
        self.assertEqual(res[0]['name'], 'Test')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_own_browse(self):
        """ Users should be able to browse name field of own requests """
        self.assertEqual(self.employee_leave.state, 'confirm')
        self.assertEqual(self.employee_leave.name, 'Test')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_update_hr_by_user(self):
        """ User may update its leave """
        self.employee_leave.sudo(self.user_employee_id).write({'name': 'Crocodile Dundee is my man'})

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_update_hr_by_user_other(self):
        """ User cannot update other people leaves """
        other_leave = self.env['hr.leave'].sudo(self.user_hruser).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })
        with self.assertRaises(AccessError):
            other_leave.sudo(self.user_employee_id).write({'name': 'Crocodile Dundee is my man'})

    # ----------------------------------------
    # Creation
    # ----------------------------------------

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_creation_for_other_user(self):
        """ Employee cannot creates a leave request for another employee """
        HolidaysEmployeeGroup = self.env['hr.leave'].sudo(self.user_employee_id)
        with self.assertRaises(AccessError):
            HolidaysEmployeeGroup.create({
                'name': 'Hol10',
                'employee_id': self.employee_hruser_id,
                'holiday_status_id': self.leave_type.id,
                'date_from': (datetime.today() - relativedelta(days=1)),
                'date_to': datetime.today(),
                'number_of_days': 1,
            })

    # ----------------------------------------
    # Reset
    # ----------------------------------------

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_reset_by_manager(self):
        """ Manager resets its own leaves """
        manager_leave = self.env['hr.leave'].sudo(self.user_hrmanager).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hrmanager.department_id.id,
            'employee_id': self.employee_hrmanager.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })
        manager_leave.sudo(self.user_hrmanager).action_draft()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_reset_by_manager_other(self):
        """ Manager may reset other leaves """
        self.employee_leave.sudo(self.user_hrmanager).action_draft()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_reset_by_officer(self):
        """ Officer resets its own leaves """
        officer_leave = self.env['hr.leave'].sudo(self.user_hruser).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })
        officer_leave.sudo(self.user_hruser).action_draft()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_reset_by_officer_other(self):
        """ Officer may not reset other leaves """
        with self.assertRaises(UserError):
            self.employee_leave.sudo(self.user_hruser).action_draft()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_reset_by_user(self):
        """ User resets its own leaves """
        self.employee_leave.sudo(self.user_employee_id).action_draft()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_reset_by_user_other(self):
        """ User may not reset other leaves """
        other_leave = self.env['hr.leave'].sudo(self.user_hruser).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })
        with self.assertRaises(UserError):
            other_leave.sudo(self.user_employee_id).action_draft()

    # ----------------------------------------
    # Validation: one validation, HR
    # ----------------------------------------

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_hr_by_manager(self):
        """ Manager validates hr-only leaves """
        self.assertEqual(self.employee_leave.state, 'confirm')
        self.employee_leave.sudo(self.user_hrmanager_id).action_approve()
        self.assertEqual(self.employee_leave.state, 'validate')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_hr_by_officer_department(self):
        """ Officer validates hr-only leaves for co-workers """
        self.assertEqual(self.employee_leave.state, 'confirm')
        self.employee_leave.sudo(self.user_hruser).action_approve()
        self.assertEqual(self.employee_leave.state, 'validate')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_hr_by_officer_no_department(self):
        """ Officer validates hr-only leaves for workers from no department and with no manager """
        self.employee_hruser.write({'department_id': False})
        with self.assertRaises(AccessError):
            self.employee_leave.sudo(self.user_hruser).action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_hr_by_officer_other_department_with_manager(self):
        """ Officer may not validate hr-only leaves for workers from another department that has a manager """
        self.employee_hruser.write({'department_id': self.hr_dept.id})
        with self.assertRaises(AccessError):
            self.employee_leave.sudo(self.user_hruser).action_approve()
        self.assertEqual(self.employee_leave.state, 'confirm')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_hr_by_officer_other_department_wo_manager(self):
        """ Officer may not validate hr-only leaves for workers from another department that has no manager """
        self.employee_hruser.write({'department_id': self.hr_dept.id})
        with self.assertRaises(AccessError):
            self.employee_leave.sudo(self.user_hruser).action_approve()
        self.assertEqual(self.employee_leave.state, 'confirm')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_hr_by_officer_other_department_manager(self):
        """ Officer validates hr-only leaves for workers from another department that he manages """
        self.employee_hruser.write({'department_id': self.hr_dept.id})
        self.employee_leave.sudo().department_id.write({'manager_id': self.employee_hruser.id})

        self.assertEqual(self.employee_leave.state, 'confirm')
        self.employee_leave.sudo(self.user_hruser).action_approve()
        self.assertEqual(self.employee_leave.state, 'validate')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_hr_by_user(self):
        """ User may not validate any leaves """
        with self.assertRaises(UserError):
            self.employee_leave.sudo(self.user_employee_id).action_approve()

        with self.assertRaises(UserError):
            self.employee_leave.sudo(self.user_employee_id).write({'state': 'validate'})

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validate_by_manager(self):
        """ Manager (who has no manager) validate its own leaves """
        manager_leave = self.env['hr.leave'].sudo(self.user_hrmanager_id).create({
            'name': 'Hol manager',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hrmanager_id,
            'date_from': (datetime.today() + relativedelta(days=15)),
            'date_to': (datetime.today() + relativedelta(days=16)),
            'number_of_days': 1,
        })
        self.assertEqual(manager_leave.state, 'confirm')
        manager_leave.action_approve()
        self.assertEqual(manager_leave.state, 'validate')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validate_by_manager_2(self):
        """ Manager (who has also a manager) validate its own leaves """
        manager_leave2 = self.env['hr.leave'].sudo(self.user_hrmanager_2_id).create({
            'name': 'Hol manager2',
            'holiday_status_id': self.leave_type.id,
            'employee_id': self.employee_hrmanager_2_id,
            'date_from': (datetime.today() + relativedelta(days=15)),
            'date_to': (datetime.today() + relativedelta(days=16)),
            'number_of_days': 1,
        })
        self.assertEqual(manager_leave2.state, 'confirm')
        manager_leave2.action_approve()
        self.assertEqual(manager_leave2.state, 'validate')

    # ----------------------------------------
    # Validation: one validation, manager
    # ----------------------------------------

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_manager_by_manager(self):
        """ Manager validates manager-only leaves """
        self.leave_type.write({'validation_type': 'manager'})
        self.employee_leave.sudo(self.user_hrmanager_id).action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_manager_by_officer_department_manager(self):
        """ Officer validates manager-only leaves for co-workers from department he manages"""
        self.leave_type.write({'validation_type': 'manager'})
        self.employee_hruser.write({'department_id': self.hr_dept.id})
        self.employee_leave.sudo().department_id.write({'manager_id': self.employee_hruser.id})
        self.employee_leave.sudo(self.user_hruser).action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_manager_by_officer_department_manager_other(self):
        """ Officer may not validates manager-only leaves for co-workers from department he does not"""
        self.leave_type.write({'validation_type': 'manager'})
        self.employee_hruser.write({'department_id': self.hr_dept.id})
        self.employee_leave.sudo().department_id.write({'manager_id': self.employee_hrmanager.id})
        with self.assertRaises(AccessError):
            self.employee_leave.sudo(self.user_hruser).action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_manager_by_officer_manager(self):
        """ Officer validates manager-only leaves for co-workers that he manages"""
        self.leave_type.write({'validation_type': 'manager'})
        self.employee_emp.write({'parent_id': self.employee_hruser.id})
        self.employee_leave.sudo(self.user_hruser).action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_manager_by_officer_manager_other(self):
        """ Officer may not validate manager-only leaves for co-workers he does not manage"""
        self.leave_type.write({'validation_type': 'manager'})
        self.employee_emp.write({'parent_id': self.employee_hrmanager.id})
        with self.assertRaises(UserError):
            self.employee_leave.sudo(self.user_hruser).action_approve()

        with self.assertRaises(UserError):
            self.employee_leave.sudo(self.user_hruser).write({'state': 'validate'})

    # ----------------------------------------
    # Validation: double
    # ----------------------------------------

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_both_by_manager(self):
        """ Manager validates double validation leaves """
        self.leave_type.write({'validation_type': 'both'})
        self.employee_leave.sudo(self.user_hrmanager_id).action_approve()
        self.employee_leave.sudo(self.user_hrmanager_id).action_validate()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_both_by_officer(self):
        """ Officer may not validate double validation leaves """
        self.leave_type.write({'validation_type': 'both'})
        self.employee_leave.sudo(self.user_hruser).action_approve()
        with self.assertRaises(UserError):
            self.employee_leave.sudo(self.user_hruser).action_validate()

        with self.assertRaises(UserError):
            self.employee_leave.sudo(self.user_hruser).write({'state': 'validate'})

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_validation_both_by_officer_and_manager(self):
        """ Officer + Manager complete double validation leaves """
        self.leave_type.write({'validation_type': 'both'})
        self.employee_leave.sudo(self.user_hruser).action_approve()
        self.employee_leave.sudo(self.user_hrmanager_id).action_validate()


class TestMultiCompany(TestHrHolidaysBase):

    def setUp(self):
        super(TestMultiCompany, self).setUp()
        self.new_company = self.env['res.company'].create({
            'name': 'Crocodile Dundee Company',
        })
        self.leave_type = self.env['hr.leave.type'].create({
            'name': 'Unlimited - Company New',
            'company_id': self.new_company.id,
            'validation_type': 'hr',
            'allocation_type': 'no',
        })
        self.rd_dept.manager_id = False
        self.hr_dept.manager_id = False

        self.employee_leave = self.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_emp.department_id.id,
            'employee_id': self.employee_emp.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_other_company_user(self):
        employee_leave = self.employee_leave.sudo(self.user_employee)

        with self.assertRaises(AccessError):
            name = employee_leave.name

        with self.assertRaises(AccessError):
            employee_leave.action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_other_company_officer(self):
        employee_leave_hruser = self.employee_leave.sudo(self.user_hruser)

        with self.assertRaises(AccessError):
            name = employee_leave_hruser.name

        with self.assertRaises(AccessError):
            employee_leave_hruser.action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_other_company_manager(self):
        employee_leave_hrmanager = self.employee_leave.sudo(self.user_hrmanager)

        with self.assertRaises(AccessError):
            name = employee_leave_hrmanager.name

        with self.assertRaises(AccessError):
            employee_leave_hrmanager.action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_no_company_user(self):
        self.leave_type.write({'company_id': False})
        employee_leave = self.employee_leave.sudo(self.user_employee)

        name = employee_leave.name
        with self.assertRaises(UserError):
            employee_leave.action_approve()
        self.assertEqual(employee_leave.state, 'confirm')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_no_company_officer(self):
        self.leave_type.write({'company_id': False})
        employee_leave_hruser = self.employee_leave.sudo(self.user_hruser)

        name = employee_leave_hruser.name
        employee_leave_hruser.action_approve()
        self.assertEqual(employee_leave_hruser.state, 'validate')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_no_company_manager(self):
        self.leave_type.write({'company_id': False})
        employee_leave_hrmanager = self.employee_leave.sudo(self.user_hrmanager)

        name = employee_leave_hrmanager.name
        employee_leave_hrmanager.action_approve()
        self.assertEqual(employee_leave_hrmanager.state, 'validate')
