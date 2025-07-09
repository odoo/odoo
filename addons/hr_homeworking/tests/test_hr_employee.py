# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo.tests import common


class TestHrHomeworkingCommon(common.TransactionCase):

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
