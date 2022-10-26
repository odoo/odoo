# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import tests
from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import mute_logger


@tests.tagged('access_rights', 'post_install', '-at_install')
class TestHrHolidaysAccessRightsCommon(TestHrHolidaysCommon):
    @classmethod
    def setUpClass(cls):
        super(TestHrHolidaysAccessRightsCommon, cls).setUpClass()
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Unlimited',
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
        })
        cls.rd_dept.manager_id = False
        cls.hr_dept.manager_id = False
        cls.employee_emp.parent_id = False
        cls.employee_leave = cls.env['hr.leave'].with_user(cls.user_employee_id).create({
            'name': 'Test',
            'holiday_status_id': cls.leave_type.id,
            'department_id': cls.employee_emp.department_id.id,
            'employee_id': cls.employee_emp.id,
            'date_from': datetime.now() + relativedelta(days=30),
            'date_to': datetime.now() + relativedelta(days=31),
            'number_of_days': 1,
        })

        cls.lt_no_validation = cls.env['hr.leave.type'].create({
            'name': 'Validation = no_validation',
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
        })

        cls.lt_validation_hr = cls.env['hr.leave.type'].create({
            'name': 'Validation = HR',
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
        })

        cls.lt_validation_manager = cls.env['hr.leave.type'].create({
            'name': 'Validation = manager',
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
        })

        cls.lt_validation_both = cls.env['hr.leave.type'].create({
            'name': 'Validation = both',
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
        })

        cls.draft_status = [
            cls.lt_validation_hr,
            cls.lt_validation_manager,
            cls.lt_validation_both
        ]

        cls.confirm_status = [
            cls.lt_no_validation,
            cls.lt_validation_hr,
            cls.lt_validation_manager,
            cls.lt_validation_both
        ]

    def request_leave(self, user_id, date_from, number_of_days, values=None):
        values = dict(values or {}, **{
            'date_from': date_from,
            'request_date_from': date_from,
            'date_to': date_from + relativedelta(days=number_of_days),
            'request_date_to': date_from + relativedelta(days=number_of_days),
            'number_of_days': number_of_days,
        })
        return self.env['hr.leave'].with_user(user_id).create(values)


@tests.tagged('access_rights', 'access_rights_states')
class TestAcessRightsStates(TestHrHolidaysAccessRightsCommon):
    # ******************************************************
    # Action draft
    # ******************************************************

    def test_draft_status(self):
        """
            We should only be able to draft a leave that is
            in confirm or refuse state
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Ranoi',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.action_draft()

            values = {
                'name': 'Ranoi',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=20 + i), 1, values)
            # the state has to be set to draft in a write because it is initialized to confirm if it has validation
            leave.write({'state': 'draft'})
            with self.assertRaises(UserError):
                leave.action_draft()

    def test_base_user_draft_his_leave(self):
        """
            Should be able to draft his own leave
            whatever the holiday_status_id
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.with_user(self.user_employee.id).action_draft()

    def test_base_user_draft_other_employee_leave(self):
        """
            Should not be able to draft the leave of someone else
            whatever the holiday_status_id
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            with self.assertRaises(UserError):
                leave.with_user(self.user_employee.id).action_draft()

    def test_base_user_draft_other_employee_leave_and_is_leave_manager_id(self):
        """
            Should not be able to draft the leave of someone else
            even when being the leave manager id for this person
            whatever the holiday_status_id
        """
        self.employee_hruser.write({'leave_manager_id': self.user_employee.id})
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            with self.assertRaises(UserError):
                leave.with_user(self.user_employee.id).action_draft()

    def test_base_user_draft_self_and_is_leave_manager_id(self):
        """
            Should be able to draft his own leave
            even when being leave manager id
            whatever the holiday_status_id
        """
        self.employee_emp.write({'leave_manager_id': self.user_employee.id})
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.with_user(self.user_employee.id).action_draft()

    def test_base_user_draft_refused_leave(self):
        """
            Should not be able to draft a refused leave
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.action_refuse()
            with self.assertRaises(UserError):
                leave.with_user(self.user_employee.id).action_draft()

    def test_base_user_draft_current_leave(self):
        """
            Should not be able to draft a passed leave
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=-20 + i), 1, values)
            with self.assertRaises(UserError):
                leave.with_user(self.user_employee.id).action_draft()

    def test_holiday_user_draft_his_leave(self):
        """
            Should be able to draft his own leave
            whatever the holiday_status_id
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.with_user(self.user_hruser.id).action_draft()

    def test_holiday_user_draft_other_employee_leave(self):
        """
            Should not be able to draft other employee leave
            whatever the holiday_status_id
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            with self.assertRaises(UserError):
                leave.with_user(self.user_hruser.id).action_draft()

    def test_holiday_user_draft_other_employee_leave_and_is_leave_manager_id(self):
        """
            Should not be able to draft other employee leave
            even if he is the leave manager id
            whatever the holiday_status_id
        """
        self.employee_emp.write({'leave_manager_id': self.user_hruser.id})
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_emp.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            with self.assertRaises(UserError):
                leave.with_user(self.user_hruser.id).action_draft()

    def test_holiday_user_draft_self_and_is_manager_id(self):
        """
            Should be able to draft his own leave
            even if he is leave manager id
            whatever the holiday_status_id
        """
        self.employee_hruser.write({'leave_manager_id': self.user_hruser.id})
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.with_user(self.user_hruser.id).action_draft()

    def test_holiday_user_draft_refused_leave(self):
        """
            Should not be able to draft a refused leave
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.action_refuse()
            with self.assertRaises(UserError):
                leave.with_user(self.user_hruser.id).action_draft()

    def test_holiday_user_draft_current_leave(self):
        """
            Should not be able to draft a passed leave
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=-20 + i), 1, values)
            with self.assertRaises(UserError):
                leave.with_user(self.user_hruser.id).action_draft()

    def test_holiday_manager_draft_his_leave(self):
        """
            The holiday manager should be able to do everything
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.with_user(self.user_hrmanager.id).action_draft()

    def test_holiday_manager_draft_other_employee_leave(self):
        """
            The holiday manager should be able to do everything
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.with_user(self.user_hrmanager.id).action_draft()

    def test_holiday_manager_draft_other_employee_leave_and_is_leave_manager_id(self):
        """
            The holiday manager should be able to do everything
        """
        self.employee_hruser.write({'leave_manager_id': self.user_hrmanager.id})
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.with_user(self.user_hrmanager.id).action_draft()

    def test_holiday_manager_draft_self_and_is_manager_id(self):
        """
            The holiday manager should be able to do everything
        """
        self.employee_hrmanager.write({'leave_manager_id': self.user_hrmanager.id})
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hrmanager.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.with_user(self.user_hrmanager.id).action_draft()

    def test_holiday_manager_draft_refused_leave(self):
        """
            The holiday manager should be able to do everything
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=5 + i), 1, values)
            leave.action_refuse()
            leave.with_user(self.user_hrmanager.id).action_draft()

    def test_holiday_manager_draft_current_leave(self):
        """
            The holiday manager should be able to do everything
        """
        for i, status in enumerate(self.draft_status):
            values = {
                'name': 'Random Leave',
                'employee_id': self.employee_hruser.id,
                'holiday_status_id': status.id,
            }
            leave = self.request_leave(1, datetime.today() + relativedelta(days=-20 + i), 1, values)
            leave.with_user(self.user_hrmanager.id).action_draft()

@tests.tagged('access_rights', 'access_rights_create')
class TestAccessRightsCreate(TestHrHolidaysAccessRightsCommon):
    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_base_user_create_self(self):
        """ A simple user can create a leave for himself """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.leave_type.id,
        }
        self.request_leave(self.user_employee_id, datetime.today() + relativedelta(days=5), 1, values)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_base_user_create_other(self):
        """ A simple user cannot create a leave for someone else """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.leave_type.id,
        }
        with self.assertRaises(AccessError):
            self.request_leave(self.user_employee_id, datetime.today() + relativedelta(days=5), 1, values)


    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_base_user_create_batch(self):
        """ A simple user cannot create a leave in bacth mode (by company, by department, by tag)"""
        values = {
            'name': 'Hol10',
            'holiday_status_id': self.leave_type.id,
            'holiday_type': 'company',
            'mode_company_id': 1,
        }
        with self.assertRaises(AccessError):
            self.request_leave(self.user_employee_id, datetime.today() + relativedelta(days=5), 1, values)

    # hr_holidays.group_hr_holidays_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_user_create_self(self):
        """ A holidays user can create a leave for himself """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.leave_type.id,
        }
        self.request_leave(self.user_hruser_id, datetime.today() + relativedelta(days=5), 1, values)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_user_create_other(self):
        """ A holidays user can create a leave for someone else """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.leave_type.id,
        }
        self.request_leave(self.user_hruser_id, datetime.today() + relativedelta(days=5), 1, values)

    # hr_holidays.group_hr_holidays_manager

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_manager_create_self(self):
        """ A holidays manager can create a leave for himself """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_hrmanager_id,
            'holiday_status_id': self.leave_type.id,
        }
        self.request_leave(self.user_hrmanager_id, datetime.today() + relativedelta(days=5), 1, values)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_manager_create_other(self):
        """ A holidays manager can create a leave for someone else """
        values = {
            'name': 'Hol10',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.leave_type.id,
        }
        self.request_leave(self.user_hrmanager_id, datetime.today() + relativedelta(days=5), 1, values)

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_holidays_manager_create_batch(self):
        """ A holidays manager can create a leave in bacth mode (by company, by department, by tag)"""
        values = {
            'name': 'Hol10',
            'holiday_status_id': self.leave_type.id,
            'holiday_type': 'company',
            'mode_company_id': 1,
        }
        self.request_leave(self.user_hrmanager_id, datetime.today() + relativedelta(days=5), 1, values)


@tests.tagged('access_rights', 'access_rights_read')
class TestAccessRightsRead(TestHrHolidaysAccessRightsCommon):
    # base.group_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_other(self):
        """ Users should not be able to read other people requests """
        other_leave = self.env['hr.leave'].with_user(self.user_hruser).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })
        with self.assertRaises(AccessError), self.cr.savepoint():
            res = other_leave.with_user(self.user_employee_id).read(['number_of_days', 'state', 'name'])

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_read_by_user_other_browse(self):
        """ Users should not be able to browse other people requests """
        other_leave = self.env['hr.leave'].with_user(self.user_hruser).create({
            'name': 'Test',
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })
        with self.assertRaises(AccessError), self.cr.savepoint():
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
            'holiday_status_id': self.leave_type.id,
            'department_id': self.employee_hruser.department_id.id,
            'employee_id': self.employee_hruser.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
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
                'holiday_status_id': self.leave_type.id,
                'date_from': (datetime.today() - relativedelta(days=1)),
                'date_to': datetime.today(),
                'number_of_days': 1,
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
        manager_leave = self.env['hr.leave'].with_user(self.user_hrmanager_id).create({
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

    # ----------------------------------------
    # Validation: one validation, manager
    # ----------------------------------------

    # base.group_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_manager_to_validate_by_user(self):
        """ A simple user can validate in manager mode if he is leave_manager_id """
        self.leave_type.write({'leave_validation_type': 'manager'})
        values = {
            'name': 'Hol HrUser',
            'employee_id': self.employee_hruser_id,
            'holiday_status_id': self.leave_type.id,
            'state': 'confirm',
        }
        hr_leave = self.request_leave(self.user_hruser_id, datetime.now() + relativedelta(days=2), 1, values)
        with self.assertRaises(AccessError):
            hr_leave.with_user(self.user_employee_id).action_approve()
        self.employee_hruser.write({'leave_manager_id': self.user_employee_id})
        hr_leave.with_user(self.user_employee_id).action_approve()

    # hr_holidays.group_hr_holidays_user

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_manager_to_validate_by_holiday_user(self):
        """ A holiday user can validate in manager mode """
        self.leave_type.write({'leave_validation_type': 'manager'})
        values = {
            'name': 'Hol HrUser',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.leave_type.id,
            'state': 'confirm',
        }
        hr_leave = self.request_leave(self.user_hruser_id, datetime.now() + relativedelta(days=2), 1, values)
        hr_leave.with_user(self.user_hruser_id).action_approve()

    # ----------------------------------------
    # Validation: double
    # ----------------------------------------

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_double_validate(self):
        self.leave_type.write({'leave_validation_type': 'both'})
        values = {
            'name': 'double HrManager',
            'employee_id': self.employee_hrmanager_id,
            'holiday_status_id': self.leave_type.id,
            'state': 'confirm',
        }
        self.employee_hrmanager.leave_manager_id = self.env['res.users'].browse(1)
        hr_leave = self.request_leave(self.user_hruser_id, datetime.now() + relativedelta(days=6), 1, values)

        with self.assertRaises(AccessError):
            hr_leave.with_user(self.user_employee_id).action_approve()

        self.employee_hrmanager.leave_manager_id = self.user_hruser
        hr_leave.with_user(self.user_hruser_id).action_approve()

        with self.assertRaises(AccessError):
            hr_leave.with_user(self.user_employee_id).action_validate()
        hr_leave.with_user(self.user_hruser_id).action_validate()

    # hr_holidays.group_hr_holidays_manager

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_double_validate_holiday_manager(self):
        self.leave_type.write({'leave_validation_type': 'both'})
        values = {
            'name': 'double HrManager',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.leave_type.id,
            'state': 'confirm',
        }
        hr_leave = self.request_leave(self.user_hrmanager_id, datetime.now() + relativedelta(days=4), 1, values).with_user(self.user_hrmanager_id)
        hr_leave.action_approve()
        hr_leave.action_validate()

    # ----------------------------------------
    # State = Refuse
    # ----------------------------------------

    # base.group_user

    # hr_holidays.group_hr_holidays_user

    # TODO Can refuse

    # hr_holidays.group_hr_holidays_manager

    # TODO Can refuse

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

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_unlink_draft_by_user(self):
        """ A simple user may delete its leave in draft state in the future"""
        values = {
            'name': 'Random Leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'state': 'draft',
        }
        leave = self.request_leave(self.user_employee_id, datetime.now() + relativedelta(days=6), 1, values)
        leave.with_user(self.user_employee.id).unlink()

    def test_leave_unlink_confirm_by_user(self):
        """ A simple user may delete its leave in confirm state in the future"""
        values = {
            'name': 'Random Leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'state': 'confirm',
        }
        leave = self.request_leave(self.user_employee_id, datetime.now() + relativedelta(days=6), 1, values)
        leave.with_user(self.user_employee.id).unlink()

    def test_leave_unlink_confirm_in_past_by_user(self):
        """ A simple user cannot delete its leave in the past"""
        values = {
            'name': 'Random Leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
            'state': 'confirm',
        }
        leave = self.request_leave(self.user_employee_id, datetime.now() + relativedelta(days=-4), 1, values)
        with self.assertRaises(UserError), self.cr.savepoint():
            leave.with_user(self.user_employee.id).unlink()

    def test_leave_unlink_validate_by_user(self):
        """ A simple user cannot delete its leave in validate state"""
        values = {
            'name': 'Random Leave',
            'employee_id': self.employee_emp.id,
            'holiday_status_id': self.leave_type.id,
        }
        leave = self.request_leave(self.user_employee_id, datetime.now() + relativedelta(days=6), 1, values)
        leave.with_user(self.user_hrmanager_id).write({'state': 'validate'})
        with self.assertRaises(UserError), self.cr.savepoint():
            leave.with_user(self.user_employee.id).unlink()

class TestMultiCompany(TestHrHolidaysCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMultiCompany, cls).setUpClass()
        cls.new_company = cls.env['res.company'].create({
            'name': 'Crocodile Dundee Company',
        })
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Unlimited - Company New',
            'company_id': cls.new_company.id,
            'leave_validation_type': 'hr',
            'requires_allocation': 'no',
        })
        cls.rd_dept.manager_id = False
        cls.hr_dept.manager_id = False

        cls.employee_leave = cls.env['hr.leave'].create({
            'name': 'Test',
            'holiday_status_id': cls.leave_type.id,
            'department_id': cls.employee_emp.department_id.id,
            'employee_id': cls.employee_emp.id,
            'date_from': datetime.now(),
            'date_to': datetime.now() + relativedelta(days=1),
            'number_of_days': 1,
        })

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_other_company_user(self):
        employee_leave = self.employee_leave.with_user(self.user_employee)
        employee_leave.invalidate_model(['name'])
        with self.assertRaises(AccessError):
            employee_leave.name

        with self.assertRaises(AccessError):
            employee_leave.action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_other_company_officer(self):
        employee_leave_hruser = self.employee_leave.with_user(self.user_hruser)
        employee_leave_hruser.invalidate_model(['name'])
        with self.assertRaises(AccessError):
            employee_leave_hruser.name

        with self.assertRaises(AccessError):
            employee_leave_hruser.action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_other_company_manager(self):
        employee_leave_hrmanager = self.employee_leave.with_user(self.user_hrmanager)
        employee_leave_hrmanager.invalidate_model(['name'])
        with self.assertRaises(AccessError):
            employee_leave_hrmanager.name

        with self.assertRaises(AccessError):
            employee_leave_hrmanager.action_approve()

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_no_company_user(self):
        self.leave_type.write({'company_id': False})
        employee_leave = self.employee_leave.with_user(self.user_employee)

        employee_leave.name
        with self.assertRaises(UserError):
            employee_leave.action_approve()
        self.assertEqual(employee_leave.state, 'confirm')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_no_company_officer(self):
        self.leave_type.write({'company_id': False})
        employee_leave_hruser = self.employee_leave.with_user(self.user_hruser)

        employee_leave_hruser.name
        employee_leave_hruser.action_approve()
        self.assertEqual(employee_leave_hruser.state, 'validate')

    @mute_logger('odoo.models.unlink', 'odoo.addons.mail.models.mail_mail')
    def test_leave_access_no_company_manager(self):
        self.leave_type.write({'company_id': False})
        employee_leave_hrmanager = self.employee_leave.with_user(self.user_hrmanager)

        employee_leave_hrmanager.name
        employee_leave_hrmanager.action_approve()
        self.assertEqual(employee_leave_hrmanager.state, 'validate')
