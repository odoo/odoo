from odoo.tests import TransactionCase


class HomeworkingCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.address = cls.env.ref("base.main_partner")
        WorkLocation = cls.env["hr.work.location"]
        cls.work_office_1, cls.work_office_2, cls.work_home = WorkLocation.create(
            [
                {
                    "name": "Office 1",
                    "location_type": "office",
                    "address_id": cls.address.id,
                },
                {
                    "name": "Office 2",
                    "location_type": "office",
                    "address_id": cls.address.id,
                },
                {
                    "name": "Home",
                    "location_type": "home",
                    "address_id": cls.address.id,
                },
            ]
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee Test",
                "monday_location_id": cls.work_home.id,
                "tuesday_location_id": cls.work_office_1.id,
                "wednesday_location_id": cls.work_home.id,
                "thursday_location_id": cls.work_office_2.id,
                "friday_location_id": cls.work_office_2.id,
                "work_location_id": cls.work_office_2.id,
            }
        )

    def set_exception(self, date, location, employee=None):
        return self.env["hr.employee.location"].create(
            {
                "employee_id": (employee or self.employee).id,
                "work_location_id": location.id,
                "date": date,
            }
        )
