from odoo.tests.common import TransactionCase


class TestUniversityFaculty(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Faculty = cls.env["university.faculty"]
        cls.Department = cls.env["university.department"]

        cls.faculty1 = cls.Faculty.create({
            "name": "Faculty of Engineering",
            "code": "ENG",
        })
        cls.faculty2 = cls.Faculty.create({
            "name": "Faculty of Business",
            "code": "BIZ",
        })

    def test_department_count_computation(self):
        self.assertEqual(self.faculty1.department_count, 0)
        self.assertEqual(self.faculty2.department_count, 0)

        self.Department.create({
            "name": "Computer Science",
            "code": "CS-TEST",
            "faculty_id": self.faculty1.id,
        })
        self.assertEqual(self.faculty1.department_count, 1)
        self.assertEqual(self.faculty2.department_count, 0)

        self.Department.create({
            "name": "Civil Engineering",
            "code": "CE-TEST",
            "faculty_id": self.faculty1.id,
        })
        self.assertEqual(self.faculty1.department_count, 2)
        self.assertEqual(self.faculty2.department_count, 0)

    def test_action_view_departments(self):
        self.Department.create({
            "name": "Mechanical Engineering",
            "code": "ME-TEST",
            "faculty_id": self.faculty1.id,
        })
        action = self.faculty1.action_view_departments()
        self.assertEqual(action.get("res_model"), "university.department")
        self.assertEqual(action.get("domain"), [("faculty_id", "=", self.faculty1.id)])
        self.assertIn("context", action)
        ctx = action["context"]
        self.assertEqual(ctx.get("default_faculty_id"), self.faculty1.id)
        self.assertEqual(ctx.get("search_default_faculty_id"), self.faculty1.id)

    def test_action_view_departments_ensure_one(self):
        both = self.faculty1 | self.faculty2
        with self.assertRaises(ValueError):
            both.action_view_departments()

        empty = self.Faculty.browse()
        with self.assertRaises(ValueError):
            empty.action_view_departments()

    def test_stage_actions(self):
        self.assertEqual(self.faculty1.state, "draft")
        self.faculty1.action_set_active()
        self.assertEqual(self.faculty1.state, "active")
        self.faculty1.action_set_closed()
        self.assertEqual(self.faculty1.state, "closed")
        self.faculty1.action_set_draft()
        self.assertEqual(self.faculty1.state, "draft")
