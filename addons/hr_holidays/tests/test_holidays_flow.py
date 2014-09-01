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

from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.hr_holidays.tests.common import TestHrHolidaysBase
from openerp.exceptions import AccessError
from openerp.osv.orm import except_orm
from openerp.tools import mute_logger

class TestHolidaysFlow(TestHrHolidaysBase):

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_00_leave_request_flow(self):
        """ Testing leave request flow """
        cr, uid = self.cr, self.uid

        def _check_holidays_status(holiday_status, ml, lt, rl, vrl):
            self.assertEqual(holiday_status.max_leaves, ml,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.leaves_taken, lt,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.remaining_leaves, rl,
                             'hr_holidays: wrong type days computation')
            self.assertEqual(holiday_status.virtual_remaining_leaves, vrl,
                             'hr_holidays: wrong type days computation')

        # HrUser creates some holiday statuses -> crash because only HrManagers should do this
        with self.assertRaises(AccessError):
            self.holidays_status_dummy = self.hr_holidays_status.create(cr, self.user_hruser_id, {
                'name': 'UserCheats',
                'limit': True,
            })

        # HrManager creates some holiday statuses
        self.holidays_status_0 = self.hr_holidays_status.create(cr, self.user_hrmanager_id, {
            'name': 'WithMeetingType',
            'limit': True,
            'categ_id': self.registry('calendar.event.type').create(cr, self.user_hrmanager_id, {'name': 'NotLimitedMeetingType'}),
        })
        self.holidays_status_1 = self.hr_holidays_status.create(cr, self.user_hrmanager_id, {
            'name': 'NotLimited',
            'limit': True,
        })
        self.holidays_status_2 = self.hr_holidays_status.create(cr, self.user_hrmanager_id, {
            'name': 'Limited',
            'limit': False,
            'double_validation': True,
        })

        # --------------------------------------------------
        # Case1: unlimited type of leave request
        # --------------------------------------------------

        # Employee creates a leave request for another employee -> should crash
        with self.assertRaises(except_orm):
            self.hr_holidays.create(cr, self.user_employee_id, {
                'name': 'Hol10',
                'employee_id': self.employee_hruser_id,
                'holiday_status_id': self.holidays_status_1,
                'date_from': (datetime.today() - relativedelta(days=1)),
                'date_to': datetime.today(),
                'number_of_days_temp': 1,
            })
        ids = self.hr_holidays.search(cr, uid, [('name', '=', 'Hol10')])
        self.hr_holidays.unlink(cr, uid, ids)

        # Employee creates a leave request in a no-limit category
        hol1_id = self.hr_holidays.create(cr, self.user_employee_id, {
            'name': 'Hol11',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_1,
            'date_from': (datetime.today() - relativedelta(days=1)),
            'date_to': datetime.today(),
            'number_of_days_temp': 1,
        })
        hol1 = self.hr_holidays.browse(cr, self.user_hruser_id, hol1_id)
        self.assertEqual(hol1.state, 'confirm', 'hr_holidays: newly created leave request should be in confirm state')

        # Employee validates its leave request -> should not work
        self.hr_holidays.signal_workflow(cr, self.user_employee_id, [hol1_id], 'validate')
        hol1.refresh()
        self.assertEqual(hol1.state, 'confirm', 'hr_holidays: employee should not be able to validate its own leave request')

        # HrUser validates the employee leave request
        self.hr_holidays.signal_workflow(cr, self.user_hrmanager_id, [hol1_id], 'validate')
        hol1.refresh()
        self.assertEqual(hol1.state, 'validate', 'hr_holidays: validates leave request should be in validate state')

        # --------------------------------------------------
        # Case2: limited type of leave request
        # --------------------------------------------------

        # Employee creates a new leave request at the same time -> crash, avoid interlapping
        with self.assertRaises(except_orm):
            self.hr_holidays.create(cr, self.user_employee_id, {
                'name': 'Hol21',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_status_1,
                'date_from': (datetime.today() - relativedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
                'date_to': datetime.today(),
                'number_of_days_temp': 1,
            })

        # Employee creates a leave request in a limited category -> crash, not enough days left
        with self.assertRaises(except_orm):
            self.hr_holidays.create(cr, self.user_employee_id, {
                'name': 'Hol22',
                'employee_id': self.employee_emp_id,
                'holiday_status_id': self.holidays_status_2,
                'date_from': (datetime.today() + relativedelta(days=0)).strftime('%Y-%m-%d %H:%M'),
                'date_to': (datetime.today() + relativedelta(days=1)),
                'number_of_days_temp': 1,
            })

        # Clean transaction
        self.hr_holidays.unlink(cr, uid, self.hr_holidays.search(cr, uid, [('name', 'in', ['Hol21', 'Hol22'])]))

        # HrUser allocates some leaves to the employee
        aloc1_id = self.hr_holidays.create(cr, self.user_hruser_id, {
            'name': 'Days for limited category',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_2,
            'type': 'add',
            'number_of_days_temp': 2,
        })
        # HrUser validates the allocation request
        self.hr_holidays.signal_workflow(cr, self.user_hruser_id, [aloc1_id], 'validate')
        self.hr_holidays.signal_workflow(cr, self.user_hruser_id, [aloc1_id], 'second_validate')
        # Checks Employee has effectively some days left
        hol_status_2 = self.hr_holidays_status.browse(cr, self.user_employee_id, self.holidays_status_2)
        _check_holidays_status(hol_status_2, 2.0, 0.0, 2.0, 2.0)

        # Employee creates a leave request in the limited category, now that he has some days left
        hol2_id = self.hr_holidays.create(cr, self.user_employee_id, {
            'name': 'Hol22',
            'employee_id': self.employee_emp_id,
            'holiday_status_id': self.holidays_status_2,
            'date_from': (datetime.today() + relativedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
            'date_to': (datetime.today() + relativedelta(days=3)),
            'number_of_days_temp': 1,
        })
        hol2 = self.hr_holidays.browse(cr, self.user_hruser_id, hol2_id)
        # Check left days: - 1 virtual remaining day
        hol_status_2.refresh()
        _check_holidays_status(hol_status_2, 2.0, 0.0, 2.0, 1.0)

        # HrUser validates the first step
        self.hr_holidays.signal_workflow(cr, self.user_hruser_id, [hol2_id], 'validate')
        hol2.refresh()
        self.assertEqual(hol2.state, 'validate1',
                         'hr_holidays: first validation should lead to validate1 state')

        # HrUser validates the second step
        self.hr_holidays.signal_workflow(cr, self.user_hruser_id, [hol2_id], 'second_validate')
        hol2.refresh()
        self.assertEqual(hol2.state, 'validate',
                         'hr_holidays: second validation should lead to validate state')
        # Check left days: - 1 day taken
        hol_status_2.refresh()
        _check_holidays_status(hol_status_2, 2.0, 1.0, 1.0, 1.0)

        # HrManager finds an error: he refuses the leave request
        self.hr_holidays.signal_workflow(cr, self.user_hrmanager_id, [hol2_id], 'refuse')
        hol2.refresh()
        self.assertEqual(hol2.state, 'refuse',
                         'hr_holidays: refuse should lead to refuse state')
        # Check left days: 2 days left again
        hol_status_2.refresh()
        _check_holidays_status(hol_status_2, 2.0, 0.0, 2.0, 2.0)

        # Annoyed, HrUser tries to fix its error and tries to reset the leave request -> does not work, only HrManager
        self.hr_holidays.signal_workflow(cr, self.user_hruser_id, [hol2_id], 'reset')
        self.assertEqual(hol2.state, 'refuse',
                         'hr_holidays: hr_user should not be able to reset a refused leave request')

        # HrManager resets the request
        self.hr_holidays.signal_workflow(cr, self.user_hrmanager_id, [hol2_id], 'reset')
        hol2.refresh()
        self.assertEqual(hol2.state, 'draft',
                         'hr_holidays: resetting should lead to draft state')

        # HrManager changes the date and put too much days -> crash when confirming
        self.hr_holidays.write(cr, self.user_hrmanager_id, [hol2_id], {
            'date_from': (datetime.today() + relativedelta(days=4)).strftime('%Y-%m-%d %H:%M'),
            'date_to': (datetime.today() + relativedelta(days=7)),
            'number_of_days_temp': 4,
        })
        with self.assertRaises(except_orm):
            self.hr_holidays.signal_workflow(cr, self.user_hrmanager_id, [hol2_id], 'confirm')
