# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import new_test_user, tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError
from odoo.fields import Command

from datetime import datetime
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta


@tagged('post_install', '-at_install')
class TestUserAccess(TransactionCase):

    def setUp(self):
        super(TestUserAccess, self).setUp()

        # create a planning manager
        self.planning_mgr = new_test_user(self.env,
                                          login='mgr',
                                          groups='planning.group_planning_manager',
                                          name='Planning Manager',
                                          email='mgr@example.com')

        self.hr_planning_mgr = self.env['hr.employee'].create({
            'name': 'Planning Manager',
            'user_id': self.planning_mgr.id,
        })

        # create a planning user
        self.planning_user = new_test_user(self.env,
                                           login='puser',
                                           groups='planning.group_planning_user',
                                           name='Planning User',
                                           email='user@example.com')

        self.hr_planning_user = self.env['hr.employee'].create({
            'name': 'Planning User',
            'user_id': self.planning_user.id,
        })
        self.res_planning_user = self.hr_planning_user.resource_id

        # create an internal user
        self.internal_user = new_test_user(self.env,
                                           login='iuser',
                                           groups='base.group_user',
                                           name='Internal User',
                                           email='internal_user@example.com')

        self.hr_internal_user = self.env['hr.employee'].create({
            'name': 'Internal User',
            'user_id': self.internal_user.id,
        })
        self.res_internal_user = self.hr_internal_user.resource_id

        self.portal_user = self.env['res.users'].create({
            'name': 'Portal User (Test)',
            'login': 'portal_user',
            'password': 'portal_user',
            'groups_id': [Command.link(self.env.ref('base.group_portal').id)]
        })

        # create several slots for users
        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 6, 27, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 27, 17, 0, 0),
            'resource_id': self.res_planning_user.id,
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2022, 6, 27, 17, 0, 0),
            'repeat_interval': 1,
            'state': 'published',
        })

        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 6, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 28, 17, 0, 0),
            'resource_id': self.res_internal_user.id,
            'repeat': True,
            'repeat_type': 'until',
            'repeat_until': datetime(2022, 6, 28, 17, 0, 0),
            'repeat_interval': 1,
            'state': 'published',
        })

    def test_01_internal_user_read_own_slots(self):
        """
        An internal user shall be able to read its own slots.
        """
        my_slot = self.env['planning.slot'].with_user(self.internal_user).search(
            [('user_id', '=', self.internal_user.id)],
            limit=1)

        self.assertNotEqual(my_slot.id, False,
                            "An internal user shall be able to read its own slots")

        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 5, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 5, 28, 17, 0, 0),
            'resource_id': self.res_internal_user.id,
            'state': 'draft',
        })
        unpublished_count = self.env['planning.slot'].with_user(self.internal_user).search_count([('state', '=', 'draft')])
        self.assertEqual(unpublished_count, 0, "An internal user shouldn't see unpublished slots")

    def test_02_internal_user_read_other_slots(self):
        """
        An internal user shall NOT be able to read other slots.
        """
        other_slot = self.env['planning.slot'].with_user(self.internal_user).search(
                [('user_id', '=', self.planning_user.id)],
                limit=1)

        planning_user_slot = self.env['planning.slot'].with_user(self.planning_user).search(
                [('user_id', '=', self.planning_user.id)],
                limit=1)

        self.assertFalse(
            other_slot,
            "An internal user shall NOT be able to read other slots")

        self.assertNotEqual(
            planning_user_slot,
            False,
            "A planning user shall be able to access to its own slots")

        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 5, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 5, 28, 17, 0, 0),
            'resource_id': self.res_planning_user.id,
            'state': 'draft',
        })
        unpublished_count = self.env['planning.slot'].with_user(self.planning_user).search_count([('state', '=', 'draft')])
        self.assertEqual(unpublished_count, 0, "A planning user shouldn't see unpublished slots")

        mgr_unpublished_count = self.env['planning.slot'].with_user(self.planning_mgr).search_count([('state', '=', 'draft')])
        self.assertNotEqual(mgr_unpublished_count, 0, "A planning manager should see unpublished slots")

    def test_03_internal_user_write_own_slots(self):
        """
        An internal user shall NOT be able to write its own slots.
        """
        my_slot = self.env['planning.slot'].with_user(self.internal_user).search(
            [('user_id', '=', self.internal_user.id)],
            limit=1)

        with self.assertRaises(AccessError):
            my_slot.write({
                'name': 'a new name'
            })

    def test_04_internal_user_create_own_slots(self):
        """
        An internal user shall NOT be able to create its own slots.
        """
        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.internal_user).create({
                'start_datetime': datetime(2019, 7, 28, 8, 0, 0),
                'end_datetime': datetime(2019, 7, 28, 17, 0, 0),
                'resource_id': self.res_internal_user.id,
                'repeat': True,
                'repeat_type': 'until',
                'repeat_until': datetime(2022, 7, 28, 17, 0, 0),
                'repeat_interval': 1,
            })

    def test_internal_user_can_see_own_progress_bar(self):
        """
        An internal user shall be able to see its own progress bar.
        """
        self.env['planning.slot'].with_user(self.internal_user).gantt_progress_bar(
            ['resource_id'], {'resource_id': self.res_internal_user.ids}, '2015-11-08 00:00:00', '2015-11-28 23:59:59'
        )['resource_id']

    def test_internal_user_can_see_others_progress_bar(self):
        """
        An internal user shall be able to see others progress bar.
        """
        self.env['planning.slot'].with_user(self.internal_user).gantt_progress_bar(
            ['resource_id'], {'resource_id': self.res_internal_user.ids}, '2015-11-08 00:00:00', '2015-11-28 23:59:59'
        )['resource_id']

    def test_portal_user_cannot_access_progress_bar(self):
        """
        A portal user shall not be able to see any progress bar.
        """
        progress_bar = self.env['planning.slot'].with_user(self.portal_user).gantt_progress_bar(
            ['resource_id'], {'resource_id': []}, '2015-11-08 00:00:00', '2015-11-28 23:59:59'
        )['resource_id']
        self.assertFalse(progress_bar, "Progress bar should be empty for non-planning users")

    def test_internal_user_cannot_copy_previous(self):
        """
        An internal user shall be able to call a non-void copy previous.

        i.e. If the copy previous doesn't select any slot, through the domain and the ir.rules, then it will do nothing and
        won't raise AccessError.
        """
        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 6, 25, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 25, 17, 0, 0),
            'resource_id': self.res_internal_user.id,
            'state': 'published',
        })
        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.internal_user).action_copy_previous_week(
                '2019-07-01 00:00:00',
                [['start_datetime', '<=', '2019-06-30 21:59:59'], ['end_datetime', '>=', '2019-06-22 23:00:00']]
            )

    def test_planning_user_cannot_create_slots(self):
        """ Planning user shall not be able to create slots. """
        my_slot = self.env['planning.slot'].with_user(self.planning_user).search([('user_id', '=', self.planning_user.id)], limit=1)

        self.assertNotEqual(my_slot.id, False, "An Planning user can see the slots")

        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.planning_user).create({
                'start_datetime': datetime(2019, 5, 28, 8, 0, 0),
                'end_datetime': datetime(2019, 5, 28, 17, 0, 0),
                'resource_id': self.res_internal_user.id,
                'state': 'draft',
            })

    def test_planning_user_read_own_and_other_slots(self):
        """ Planning user can read its own and other slots. """
        other_slot = self.env['planning.slot'].with_user(self.planning_user).search(
                [('user_id', '=', self.internal_user.id)],
                limit=1)

        planning_user_slot = self.env['planning.slot'].with_user(self.planning_user).search(
                [('user_id', '=', self.planning_user.id)],
                limit=1)

        self.assertTrue(
            other_slot,
            "An planning user can read other slots")

        self.assertNotEqual(
            planning_user_slot,
            False,
            "A planning user can access to its own slots")

        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 5, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 5, 28, 17, 0, 0),
            'resource_id': self.res_internal_user.id,
            'state': 'draft',
        })
        unpublished_count = self.env['planning.slot'].with_user(self.planning_user).search_count([('state', '=', 'draft')])
        self.assertEqual(unpublished_count, 0, "A planning user shouldn't see unpublished slots")

    def test_planning_user_can_take_unassigned_slots(self):
        """ Planning user can take unassigned slots. """
        test_slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 5, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 5, 28, 17, 0, 0),
            'state': 'published',
        })
        test_slot.with_user(self.planning_user).action_self_assign()
        self.assertEqual(test_slot.resource_id, self.res_planning_user, "Planning user can take slot")

    def test_planning_user_can_unassign_slots(self):
        """ Planning user can unassign their own slots. """
        self.env['res.config.settings'].create({
            'planning_allow_self_unassign': True,
            'planning_self_unassign_days_before': 1,
        }).execute()

        test_slot = self.env['planning.slot'].create({
            'start_datetime': datetime.now() + relativedelta(days=2),
            'end_datetime': datetime.now() + relativedelta(days=3),
            'state': 'published',
            'employee_id': self.planning_user.employee_id.id,
            'resource_id': self.res_planning_user.id,
            'unassign_deadline':  datetime.now() + relativedelta(days=1),
        })
        test_slot.with_user(self.planning_user).action_self_unassign()
        self.assertFalse(test_slot.resource_id, "Planning user can unassign their slot")

    def test_planning_user_cannot_copy_previous(self):
        """
        An internal user shall not be able to call a non-void copy previous.

        i.e. If the copy previous doesn't select any slot, through the domain and the ir.rules, then it will do nothing and
        won't raise AccessError.
        """
        self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 6, 25, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 25, 17, 0, 0),
            'resource_id': self.res_planning_user.id,
            'state': 'published',
        })
        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.planning_user).action_copy_previous_week(
                '2019-07-01 00:00:00',
                [['start_datetime', '<=', '2019-06-30 21:59:59'], ['end_datetime', '>=', '2019-06-22 23:00:00']]
            )

    def test_planning_mgr_can_copy_previous(self):
        """
        An internal user shall be able to call copy previous.
        """
        test_slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2019, 6, 25, 8, 0, 0),
            'end_datetime': datetime(2019, 6, 25, 17, 0, 0),
            'resource_id': self.res_planning_user.id,
        })
        self.env['planning.slot'].with_user(self.planning_mgr).action_copy_previous_week(
            '2019-07-01 00:00:00',
            [['start_datetime', '<=', '2019-06-30 21:59:59'], ['end_datetime', '>=', '2019-06-22 23:00:00']]
        )
        self.assertTrue(test_slot.was_copied, "Test slot should be copied")

    def test_portal_user_cannot_access_copy_previous(self):
        """
        A public user shall not be able to see any progress bar.
        """
        with self.assertRaises(AccessError):
            self.env['planning.slot'].with_user(self.portal_user).action_copy_previous_week(
                '2019-07-01 00:00:00',
                [['start_datetime', '<=', '2019-06-30 21:59:59'], ['end_datetime', '>=', '2019-06-22 23:00:00']]
            )
    def test_multicompany_access_slots(self):
        """
        A user shall NOT be able to access other companies' slots when sending plannings.
        """
        in_user = self.planning_mgr
        out_user = self.planning_user
        out_user.groups_id = [(6, 0, [self.env.ref('planning.group_planning_manager').id])]
        other_company = self.env['res.company'].create({
            'name': 'Other Co',
        })
        out_user.write({
            'company_ids': other_company.ids,
            'company_id': other_company.id,
        })
        out_user.employee_id.company_id = other_company

        slot = self.env['planning.slot'].with_user(out_user).create({
            'start_datetime': datetime(2019, 7, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 7, 28, 17, 0, 0),
            'employee_id': out_user.employee_id.id,
            'repeat': False,
        })
        send = self.env['planning.send'].with_user(in_user).create({
            'start_datetime': datetime(2019, 7, 28, 8, 0, 0),
            'end_datetime': datetime(2019, 7, 28, 17, 0, 0),
        })
        # Trigger _compute_slots_data
        send.start_datetime = datetime(2019, 7, 25, 8, 0, 0)

        self.assertNotIn(slot, send.slot_ids, "User should not be able to send planning to users from other companies")

    def test_user_can_archive_another_employee(self):
        """
        Test user may archive another employee with no access right to planning.
            Test Case:
            =========
            - Create user with no access planning access
            - Create employee
            - Create 2 slots
            - Archive employee
        """
        hr_officer = new_test_user(
            self.env, login='hr_user', groups='hr.group_hr_user',
            name='HR Officer', email='hro@example.com')

        employee_eren = self.env['hr.employee'].with_user(hr_officer).create({
            'name': 'bert',
            'work_email': 'bert@a.be',
            'tz': 'UTC',
            'employee_type': 'freelance',
        })

        with freeze_time("2020-04-22"):
            slot_1, slot_2 = self.env['planning.slot'].create([
                {
                    'resource_id': employee_eren.resource_id.id,
                    'start_datetime': datetime(2020, 4, 20, 8, 0),
                    'end_datetime': datetime(2020, 4, 24, 17, 0),
                },
                {
                    'resource_id': employee_eren.resource_id.id,
                    'start_datetime': datetime(2020, 4, 23, 8, 0),
                    'end_datetime': datetime(2020, 4, 24, 17, 0),
                },
            ])

            initial_end_date = slot_1.end_datetime

            employee_eren.with_user(hr_officer).action_archive()

            self.assertNotEqual(slot_1.end_datetime, initial_end_date, 'End date should be updated')
            self.assertFalse(slot_2.resource_id, 'Resource should be the False for archeived resource shifts')
