# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo.addons.payroll.models.hr_payslip import BaseBrowsableObject, BrowsableObject

from .common import TestPayslipBase


class TestBrowsableObject(TestPayslipBase):
    def setUp(self):
        super().setUp()

    def test_init(self):
        obj = BrowsableObject(self.richard_emp.id, {"test": 1}, self.env)

        self.assertEqual(obj.test, 1, "Simple initialization")
        self.assertEqual(
            obj.employee_id,
            self.richard_emp.id,
            "Employee Id is retrieved successfully",
        )
        self.assertEqual(obj.env, self.env, "Env is retrieved successfully")

        d = {
            "level1": BaseBrowsableObject(
                {
                    "level2": 10,
                    "env": 900.0,
                },
            )
        }
        obj = BrowsableObject(self.richard_emp.id, d, self.env)

        self.assertEqual(obj.level1.level2, 10, "Nested initialization")
        self.assertEqual(
            obj.employee_id,
            self.richard_emp.id,
            "Employee Id is retrieved successfully from nested dictionary",
        )
        self.assertEqual(
            obj.env, self.env, "Env is retrieved successfully from nested dictionary"
        )
        self.assertEqual(
            obj.level1.employee_id, 0.0, "Employee Id is *NOT* in BaseBrowsableObject"
        )
        self.assertEqual(
            obj.level1.env,
            900.0,
            "Env is *IN* BaseBrowsableObject, but it's in user-defined dictionary",
        )

    def test_update_attribute(self):
        obj = BrowsableObject(
            self.richard_emp.id,
            {
                "foo": BaseBrowsableObject(
                    {
                        "bar": 200.0,
                    }
                )
            },
            self.env,
        )
        self.assertEqual(obj.foo.bar, 200.0, "Nested initialization succeeded")

        obj.foo.bar = 350.0
        self.assertEqual(
            obj.foo.bar,
            350.0,
            "Updating of attribute using dot ('.') notation succeeded",
        )
