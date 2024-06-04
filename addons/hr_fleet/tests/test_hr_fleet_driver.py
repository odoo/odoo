# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestHrFleetDriver(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_employee = cls.env['hr.employee'].create({
            'name': 'Test Employee'
        })

        cls.test_user = cls.env['res.users'].create({
            'login': 'test',
            'name': 'The King',
            'email': 'noop@example.com',
        })

        cls.brand = cls.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })

        cls.model = cls.env["fleet.vehicle.model"].create({
            "brand_id": cls.brand.id,
            "name": "A3",
        })

        cls.car = cls.env["fleet.vehicle"].create({
            "model_id": cls.model.id,
            "future_driver_id": cls.test_employee.work_contact_id.id,
            "plan_to_change_car": False
        })

    def test_driver_sync_with_employee(self):
        """
        If an employee has a car and their partner has changed, the update should be synced with the fleet
        """
        self.assertEqual(self.car.future_driver_id, self.test_employee.work_contact_id)
        self.test_employee.user_id = self.test_user
        self.assertEqual(self.test_employee.work_contact_id, self.test_user.partner_id)
        self.car.action_accept_driver_change()
        self.assertEqual(self.car.driver_id, self.test_user.partner_id)
