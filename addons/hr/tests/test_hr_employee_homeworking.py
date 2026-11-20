# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

<<<<<<< c2361783a8433805f6121e85002083c6546863ed:addons/hr/tests/test_hr_employee_homeworking.py
from odoo.tests import common, tagged, new_test_user
||||||| 532869dbbd88a1a2797e43bad3f36c89f8a69cfe:addons/hr_homeworking/tests/test_hr_employee.py
from odoo.tests import common
=======
from odoo.exceptions import UserError
from odoo.tests import common
>>>>>>> 348f87e89e1bdc101e515dfce5205dbd72b6629f:addons/hr_homeworking/tests/test_hr_employee.py


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHrEmployeeHomeworking(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        main_partner_id = cls.env.ref('base.main_partner')

        cls.work_office_1, cls.work_office_2, cls.work_home = cls.env['hr.work.location'].create([
            {
                'name': "Office 1",
                'location_type': "office",
                'address_id': main_partner_id.id,
            }, {
                'name': "Office 2",
                'location_type': "office",
                'address_id': main_partner_id.id,
            }, {
                'name': "Home",
                'location_type': "home",
                'address_id': main_partner_id.id,
            },
        ])

        cls.employee_1 = cls.env['hr.employee'].create([{
            'name': 'Employee Test',
            'monday_location_id': cls.work_home.id,
            'tuesday_location_id': cls.work_office_1.id,
            'wednesday_location_id': cls.work_home.id,
            'thursday_location_id': cls.work_office_2.id,
            'friday_location_id': cls.work_office_2.id,
            'work_location_id': cls.work_office_2.id,
        }])

    @freeze_time("2025-07-13")
    def test_standard_work_location(self):
        "2025-07-13 ==> Sunday"
        self.assertEqual(self.employee_1.work_location_name, False)
        self.assertEqual(self.employee_1.work_location_type, False)

    @freeze_time("2025-07-08")
    def test_day_work_location(self):
        "2025-07-08 ==> Tuesday"
        self.assertEqual(self.employee_1.work_location_name, "Office 1")
        self.assertEqual(self.employee_1.work_location_type, "office")

    @freeze_time("2025-07-09")
    def test_exceptional_work_location(self):
        "2025-07-09 ==> Wednesday"
        self.assertEqual(self.employee_1.work_location_name, "Home")
        self.assertEqual(self.employee_1.work_location_type, "home")

        self.env['hr.employee.location'].create({
            'work_location_id': self.work_office_1.id,
            'employee_id': self.employee_1.id,
            'date': '2025-07-09'
        })
        self.employee_1._compute_exceptional_location_id()
        self.assertEqual(self.employee_1.work_location_name, "Office 1")
        self.assertEqual(self.employee_1.work_location_type, "office")

    @freeze_time("2025-07-09")
    def test_change_current_work_location(self):
        "2025-07-09 ==> Wednesday"
        self.assertEqual(self.employee_1.work_location_name, "Home")
        self.assertEqual(self.employee_1.work_location_type, "home")
        self.employee_1.wednesday_location_id = self.work_office_1.id
        self.assertEqual(self.employee_1.work_location_name, "Office 1")
        self.assertEqual(self.employee_1.work_location_type, "office")

<<<<<<< c2361783a8433805f6121e85002083c6546863ed:addons/hr/tests/test_hr_employee_homeworking.py
    def test_user_can_change_own_location(self):
        """Check user without HR rights and linked to an employee can change its own location."""
        test_user = new_test_user(self.env, login='test_user', groups='base.group_user', name='testuser')
        test_user.action_create_employee()
        test_user.with_user(test_user).monday_location_id = self.work_office_1
||||||| 532869dbbd88a1a2797e43bad3f36c89f8a69cfe:addons/hr_homeworking/tests/test_hr_employee.py
    def test_im_status_format_with_location(self):
        """Test that im_status uses format 'location_status' without 'presence_' prefix"""
        with freeze_time('2025-01-06'):  # Monday
            self.assertEqual(self.test_user.im_status, 'home_offline')
        with freeze_time('2025-01-07'):  # Tuesday
            self.test_user.invalidate_recordset(['im_status'])
            self.assertEqual(self.test_user.im_status, 'office_offline')
=======
    def test_im_status_format_with_location(self):
        """Test that im_status uses format 'location_status' without 'presence_' prefix"""
        with freeze_time('2025-01-06'):  # Monday
            self.assertEqual(self.test_user.im_status, 'home_offline')
        with freeze_time('2025-01-07'):  # Tuesday
            self.test_user.invalidate_recordset(['im_status'])
            self.assertEqual(self.test_user.im_status, 'office_offline')

    def test_cannot_delete_location_used_by_employee(self):
        """A work location used by an employee on some days only can't be deleted."""
        with self.assertRaises(UserError):
            self.work_office_1.unlink()
        self.assertEqual(self.employee_1.tuesday_location_id, self.work_office_1)

        unused_location = self.env['hr.work.location'].create({
            'name': "Unused Office",
            'address_id': self.env.ref('base.main_partner').id,
        })
        unused_location.unlink()
        self.assertFalse(unused_location.exists())
>>>>>>> 348f87e89e1bdc101e515dfce5205dbd72b6629f:addons/hr_homeworking/tests/test_hr_employee.py
