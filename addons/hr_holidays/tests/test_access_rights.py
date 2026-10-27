# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from datetime import date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import api, tests
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import date_utils
from odoo.tests import tagged

from odoo.tools import mute_logger


@tests.tagged('access_rights', 'post_install', '-at_install')
class TestHrHolidaysAccessRightsCommon(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestHrHolidaysAccessRightsCommon, cls).setUpClass()
        cls.time_type = cls.env['hr.time.type'].create({
            'name': 'Unlimited',
            'code': 'Unlimited',
            'leave_validation_type': 'hr',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        cls.rd_dept.manager_id = False
        cls.hr_dept.manager_id = False
        cls.employee_emp.parent_id = False

        leave_day = date_utils.start_of(date.today() + relativedelta(days=30), 'week')

        cls.employee_leave = cls.env['hr.leave'].with_user(cls.user_employee_id).create({
            'name': 'Test',
            'time_type_id': cls.time_type.id,
            'department_id': cls.employee_emp.department_id.id,
            'employee_id': cls.employee_emp.id,
            'request_date_from': leave_day,
            'request_date_to': leave_day,
        })

        cls.lt_no_validation = cls.env['hr.time.type'].create({
            'name': 'Validation = no_validation',
            'code': 'Validation = no_validation',
            'leave_validation_type': 'hr',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.lt_validation_hr = cls.env['hr.time.type'].create({
            'name': 'Validation = HR',
            'code': 'Validation = HR',
            'leave_validation_type': 'hr',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.lt_validation_manager = cls.env['hr.time.type'].create({
            'name': 'Validation = manager',
            'code': 'Validation = manager',
            'leave_validation_type': 'hr',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.lt_validation_both = cls.env['hr.time.type'].create({
            'name': 'Validation = both',
            'code': 'Validation = both',
            'leave_validation_type': 'hr',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })

        cls.confirm_status = [
            cls.lt_no_validation,
            cls.lt_validation_hr,
            cls.lt_validation_manager,
            cls.lt_validation_both
        ]

        # Here we only test access rights, prevent any conflict with
        # existing mandatory days - they are tested someplace else.
        cls.env['hr.leave.mandatory.day'].search([]).unlink()

    def request_leave(self, user_id, request_date_from, number_of_days, values=None):
        values = dict(values or {}, **{
            'request_date_from': request_date_from,
            'request_date_to': request_date_from + relativedelta(days=number_of_days - 1),
        })
        return self.env['hr.leave'].with_user(user_id).with_context(leave_fast_create=True).create(values)

@tests.tagged('access_rights', 'access_rights_create')
class TestAccessRightsCreate(TestHrHolidaysAccessRightsCommon):
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_base_user_create_self(self):
        """ A simple user can create a leave for himself """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_emp_id,
            'time_type_id': self.time_type.id,
        }
        self.request_leave(self.user_employee_id, date.today() + relativedelta(days=5), 1, values)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_base_user_create_other(self):
        """ A simple user cannot create a leave for someone else """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_hruser_id,
            'time_type_id': self.time_type.id,
        }
        with self.assertRaises(AccessError):
            self.request_leave(self.user_employee_id, date.today() + relativedelta(days=5), 1, values)


    # hr_holidays.group_hr_holidays_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_user_create_self(self):
        """ A holidays user can create a leave for himself """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_hruser_id,
            'time_type_id': self.time_type.id,
        }
        self.request_leave(self.user_hruser_id, date.today() + relativedelta(days=5), 1, values)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_user_create_other(self):
        """ A holidays user can create a leave for someone else """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_emp_id,
            'time_type_id': self.time_type.id,
        }
        self.request_leave(self.user_hruser_id, date.today() + relativedelta(days=5), 1, values)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_create_first_approved_double_validation(self):
        """ Creating a first approved leave of a double validation type checks the rights """
        lt_both = self.env['hr.time.type'].create({
            'name': 'Double Validation',
            'code': 'Double Validation',
            'leave_validation_type': 'both',
            'requires_allocation': False,
            'request_unit': 'day',
            'unit_of_measure': 'day',
        })
        leave_day = date.today() + relativedelta(days=5)
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_emp_id,
            'time_type_id': lt_both.id,
            'request_date_from': leave_day,
            'request_date_to': leave_day,
            'state': 'validate1',
        }
        Leave = self.env['hr.leave'].with_context(leave_skip_state_check=True)
        with self.assertRaises(AccessError):
            Leave.with_user(self.user_employee_id).create(values)
        leave = Leave.with_user(self.user_hruser_id).create(values)
        self.assertTrue(leave)

    # hr_holidays.group_hr_holidays_manager

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_manager_create_self(self):
        """ A holidays manager can create a leave for himself """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_hrmanager_id,
            'time_type_id': self.time_type.id,
        }
        self.request_leave(self.user_hrmanager_id, date.today() + relativedelta(days=5), 1, values)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_manager_create_other(self):
        """ A holidays manager can create a leave for someone else """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_emp_id,
            'time_type_id': self.time_type.id,
        }
        self.request_leave(self.user_hrmanager_id, date.today() + relativedelta(days=5), 1, values)


@tests.tagged('access_rights', 'access_rights_read')
class TestAccessRightsRead(TestHrHolidaysAccessRightsCommon):
    # base.group_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_other(self):
        """ Users should not be able to read other people requests """
        other_leave = self.env['hr.leave'].with_user(self.user_hruser).create({
            'name': 'Test',
            'time_type_id': self.time_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': date.today(),
            'request_date_to': date.today() + relativedelta(days=1),
        })
        with self.assertRaises(AccessError):
            res = other_leave.with_user(self.user_employee_id).read(['number_of_days', 'state', 'name'])

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_other_browse(self):
        """ Users should not be able to browse other people requests """
        other_leave = self.env['hr.leave'].with_user(self.user_hruser).create({
            'name': 'Test',
            'time_type_id': self.time_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': date.today(),
            'request_date_to': date.today() + relativedelta(days=1),
        })
        with self.assertRaises(AccessError):
            other_leave.invalidate_model(['name'])
            name = other_leave.with_user(self.user_employee_id).name

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_own(self):
        """ Users should be able to read name field of own requests """
        res = self.employee_leave.read(['name', 'number_of_days', 'state'])
        self.assertEqual(res[0]['name'], 'Test')


@tests.tagged('access_rights', 'access_rights_write')
class TestAccessRightsWrite(TestHrHolidaysAccessRightsCommon):
    # base.group_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_update_by_user(self):
        """ User may update its leave """
        self.employee_leave.with_user(self.user_employee_id).write({'name': 'Crocodile Dundee is my man'})

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_update_by_user_other(self):
        """ User cannot update other people leaves """
        other_leave = self.env['hr.leave'].with_user(self.user_hruser).create({
            'name': 'Test',
            'time_type_id': self.time_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'request_date_from': date.today(),
            'request_date_to': date.today() + relativedelta(days=1),
        })
        with self.assertRaises(AccessError):
            other_leave.with_user(self.user_employee_id).write({'name': 'Crocodile Dundee is my man'})

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_creation_for_other_user(self):
        """ Employee cannot creates a leave request for another employee """
        HolidaysEmployeeGroup = self.env['hr.leave'].with_user(self.user_employee_id)
        with self.assertRaises(AccessError):
            HolidaysEmployeeGroup.create({
                'name': 'Hol10',
                'employee_id': self.employee_hruser_id,
                'time_type_id': self.time_type.id,
                'request_date_from': (date.today() - relativedelta(days=1)),
                'request_date_to': date.today(),
            })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_messaging_by_user(self):
        """ User may communicate on its own leaves, even if validated """
        self.employee_leave.with_user(self.user_employee_id).message_post(
            body='I haz messaging',
            subtype_xmlid='mail.mt_comment',
            message_type='comment'
        )

        self.employee_leave.with_user(self.user_hrmanager_id).action_approve()

        self.employee_leave.with_user(self.user_employee_id).message_post(
            body='I still haz messaging',
            subtype_xmlid='mail.mt_comment',
            message_type='comment'
        )

    def test_leave_approval_flags_depend_on_user(self):
        """ The approval flags of a leave are computed for the current user """
        def check_flags(leave, field_names):
            for field_name in field_names:
                values = []
                for user_id in (self.user_hrmanager_id, self.user_employee_id):
                    leave.invalidate_recordset([field_name])
                    values.append(leave.with_user(user_id)[field_name])
                self.assertEqual(values, [True, False], field_name)
                leave.invalidate_recordset([field_name])
                self.assertEqual(
                    [leave.with_user(user_id)[field_name] for user_id in (self.user_hrmanager_id, self.user_employee_id)],
                    values, field_name)

        check_flags(self.employee_leave, ['can_validate', 'can_refuse'])
        self.employee_leave.with_user(self.user_hrmanager_id).action_approve()
        check_flags(self.employee_leave, ['can_back_to_approve'])

    # ----------------------------------------
    # Validation: one validation, HR
    # ----------------------------------------

    # base.group_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_hr_to_validate_by_user(self):
        """ User may not validate any leaves in HR mode """
        with self.assertRaises(UserError):
            self.employee_leave.with_user(self.user_employee_id).action_approve()

        with self.assertRaises(UserError):
            self.employee_leave.with_user(self.user_employee_id).write({'state': 'validate'})

    # hr_holidays.group_hr_holidays_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_hr_to_validate_by_holiday_user(self):
        """ Manager can validate leaves in HR mode """
        self.assertEqual(self.employee_leave.state, 'confirm')
        self.employee_leave.with_user(self.user_hrmanager_id).action_approve()
        self.assertEqual(self.employee_leave.state, 'validate')

    # hr_holidays.group_hr_holidays_manager

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_hr_to_validate_by_manager(self):
        """ Manager validate its own leaves """
        leave_start = date_utils.start_of(date.today() + relativedelta(days=15), 'week')
        manager_leave = self.env['hr.leave'].with_user(self.user_hrmanager_id).with_context(leave_fast_create=True).create({
            'name': 'Hol manager',
            'time_type_id': self.time_type.id,
            'employee_id': self.employee_hrmanager_id,
            'request_date_from': leave_start,
            'request_date_to': leave_start + relativedelta(days=1),
        })
        self.assertEqual(manager_leave.state, 'confirm')
        manager_leave.action_approve()
        self.assertEqual(manager_leave.state, 'validate')

    # ----------------------------------------
    # Validation: one validation, manager
    # ----------------------------------------

    # base.group_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_manager_to_validate_by_user(self):
        """ A simple user can validate in manager mode if he is leave_manager_id """
        self.time_type.write({'leave_validation_type': 'manager'})
        values = {
            'name': 'Hol HrUser',
            'employee_id': self.employee_hruser_id,
            'time_type_id': self.time_type.id,
            'state': 'confirm',
        }
        hr_leave = self.request_leave(self.user_hruser_id, date_utils.start_of(date.today() + relativedelta(days=7), 'week'), 1, values)
        with self.assertRaises(UserError):
            hr_leave.with_user(self.user_employee_id).action_approve()
        self.employee_hruser.write({'leave_manager_id': self.user_employee_id})
        hr_leave.with_user(self.user_employee_id).action_approve()

    # hr_holidays.group_hr_holidays_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_manager_to_validate_by_holiday_user(self):
        """ A holiday user can validate in manager mode """
        self.time_type.write({'leave_validation_type': 'manager'})
        values = {
            'name': 'Hol HrUser',
            'employee_id': self.employee_emp_id,
            'time_type_id': self.time_type.id,
            'state': 'confirm',
        }
        hr_leave = self.request_leave(self.user_hruser_id, date_utils.start_of(date.today() + relativedelta(days=7), 'week'), 1, values)
        hr_leave.with_user(self.user_hruser_id).action_approve()

    # ----------------------------------------
    # Validation: double
    # ----------------------------------------

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_double_validate(self):
        self.time_type.write({'leave_validation_type': 'both'})
        values = {
            'name': 'double HrManager',
            'employee_id': self.employee_hrmanager_id,
            'time_type_id': self.time_type.id,
            'state': 'confirm',
        }
        self.employee_hrmanager.leave_manager_id = api.SUPERUSER_ID
        leave_date = date_utils.start_of(date.today() + relativedelta(days=7), 'week')
        hr_leave = self.request_leave(self.user_hruser_id, leave_date, 1, values)

        with self.assertRaises(UserError):
            hr_leave.with_user(self.user_employee_id).action_approve()
        self.employee_hrmanager.leave_manager_id = self.user_responsible
        hr_leave.with_user(self.user_responsible_id).action_approve()

        with self.assertRaises(UserError):
            hr_leave.with_user(self.user_employee_id).action_approve()
        hr_leave.with_user(self.user_hruser_id).action_approve()

    # hr_holidays.group_hr_holidays_manager

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_double_validate_holiday_manager(self):
        self.time_type.write({'leave_validation_type': 'both'})
        values = {
            'name': 'double HrManager',
            'employee_id': self.employee_emp_id,
            'time_type_id': self.time_type.id,
            'state': 'confirm',
        }
        leave_start = date_utils.start_of(date.today() + relativedelta(days=15), 'week')
        hr_leave = self.request_leave(self.user_hrmanager_id, leave_start, 1, values).with_user(self.user_hrmanager_id)
        hr_leave.action_approve()

    # ----------------------------------------
    # State = Refuse
    # ----------------------------------------

    # base.group_user

    # hr_holidays.group_hr_holidays_user

    # TODO Can refuse

    # hr_holidays.group_hr_holidays_manager

    # TODO Can refuse

    # hr_holidays.group_hr_holidays_responsible

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    @freeze_time('2026-01-23 10:00:00')
    def test_holiday_responsible_refuse_leave(self):
        """
            The holiday responsible should be able to accept and refuse correct type leaves of users they are responsible for
        """
        respo_user = self.user_responsible
        self.employee_emp.leave_manager_id = respo_user

        for validatation_type in ['manager', 'both']:
            self.time_type.write({'leave_validation_type': validatation_type})
            values = {
                'name': 'Random Time Off',
                'employee_id': self.employee_emp.id,
                'time_type_id': self.time_type.id,
                'state': 'confirm',
            }
            leave = self.request_leave(self.user_employee, date.today(), 1, values)
            leave.with_user(respo_user).action_refuse()
            # Check that refusing after first approval also works
            leave = self.request_leave(self.user_employee, date.today(), 1, values)
            leave.with_user(respo_user).action_approve()
            leave.with_user(respo_user).action_refuse()

    # ----------------------------------------
    # State = Cancel
    # ----------------------------------------

    # base.group_user

    # TODO Can Cancel if start_date in the future

    # hr_holidays.group_hr_holidays_user

    # TODO Can Cancel if not in validate

    # hr_holidays.group_hr_holidays_manager

    # TODO Can always cancel with great powers comes great responbilities

class TestAccessRightsUnlink(TestHrHolidaysAccessRightsCommon):

    # base.group_user


    def test_leave_unlink_confirm_by_user(self):
        """ A simple user may delete its leave in confirm state in the future"""
        values = {
            'name': 'Random Time Off',
            'employee_id': self.employee_emp.id,
            'time_type_id': self.time_type.id,
            'state': 'confirm',
        }
        leave = self.request_leave(self.user_employee_id, date.today() + relativedelta(days=6), 1, values)
        leave.with_user(self.user_employee.id).unlink()

    def test_leave_unlink_confirm_in_past_by_user(self):
        """ A simple user cannot delete its leave in the past"""
        values = {
            'name': 'Random Time Off',
            'employee_id': self.employee_emp.id,
            'time_type_id': self.time_type.id,
            'state': 'confirm',
        }
        leave = self.request_leave(self.user_employee_id, date.today() + relativedelta(days=-4), 1, values)
        with self.assertRaises(UserError):
            leave.with_user(self.user_employee.id).unlink()

    def test_leave_unlink_error_names_offending_state(self):
        """ The error raised when a simple user deletes leaves names the state of the faulty one

        The record rules only let simple users delete leaves to approve: the check is reached as
        superuser, e.g. by a flow deleting leaves on behalf of the user.
        """
        values = {
            'name': 'Random Time Off',
            'employee_id': self.employee_emp.id,
            'time_type_id': self.time_type.id,
            'state': 'confirm',
        }
        confirmed_leave = self.request_leave(self.user_employee_id, date.today() + relativedelta(days=6), 1, values)
        validated_leave = self.request_leave(self.user_employee_id, date.today() + relativedelta(days=8), 1, values)
        validated_leave.with_user(self.user_hrmanager_id).write({'state': 'validate'})
        with self.assertRaisesRegex(UserError, 'Approved'):
            (confirmed_leave | validated_leave).with_user(self.user_employee.id).sudo().unlink()

    def test_leave_unlink_validate_by_user(self):
        """ A simple user cannot delete its leave in validate state"""
        values = {
            'name': 'Random Time Off',
            'employee_id': self.employee_emp.id,
            'time_type_id': self.time_type.id,
        }
        leave = self.request_leave(self.user_employee_id, date.today() + relativedelta(days=6), 1, values)
        leave.with_user(self.user_hrmanager_id).write({'state': 'validate'})
        with self.assertRaises(UserError):
            leave.with_user(self.user_employee.id).unlink()
