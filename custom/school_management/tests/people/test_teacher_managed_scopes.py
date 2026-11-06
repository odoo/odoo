from uuid import uuid4

from odoo import fields
from odoo.tests.common import TransactionCase


class TestTeacherManagedScopes(TransactionCase):
    def setUp(self):
        super().setUp()
        code = uuid4().hex[:12]
        self.faculty = self.env["university.faculty"].create({
            "name": "Managed Scope Faculty", "code": code,
        })
        self.department = self.env["university.department"].create({
            "name": "Managed Scope Department", "code": code,
            "faculty_id": self.faculty.id,
        })
        self.teacher = self.env["university.teacher"].create({
            "name": "Managed Scope Teacher", "teacher_id": code,
            "department_id": self.department.id,
        })

    def _appoint(self, role):
        return self.env["university.academic.assignment"].create({
            "staff_id": self.teacher.id,
            "role": role,
            "department_id": self.department.id if role == "department_head" else False,
            "faculty_id": self.faculty.id if role == "dean" else False,
            "start_date": fields.Date.today(),
        })

    def test_department_membership_does_not_imply_management(self):
        self.assertFalse(self.teacher.managed_department_id)
        self.assertFalse(self.teacher.managed_faculty_id)

    def test_managed_department_recomputes_after_assignment_changes(self):
        assignment = self._appoint("department_head")
        self.assertEqual(self.teacher.managed_department_id, self.department)
        assignment.active = False
        self.assertFalse(self.teacher.managed_department_id)
        assignment.active = True
        self.assertEqual(self.teacher.managed_department_id, self.department)

        replacement = self.env["university.teacher"].create({
            "name": "Replacement Head", "teacher_id": uuid4().hex,
            "department_id": self.department.id,
        })
        assignment.staff_id = replacement
        self.assertFalse(self.teacher.managed_department_id)
        self.assertEqual(replacement.managed_department_id, self.department)
        assignment.unlink()
        self.assertFalse(replacement.managed_department_id)

    def test_managed_faculty_recomputes_after_role_changes(self):
        assignment = self._appoint("dean")
        self.assertEqual(self.teacher.managed_faculty_id, self.faculty)
        assignment.role = "vice_dean"
        self.assertFalse(self.teacher.managed_faculty_id)
        assignment.role = "dean"
        self.assertEqual(self.teacher.managed_faculty_id, self.faculty)
        assignment.active = False
        self.assertFalse(self.teacher.managed_faculty_id)

    def test_managed_scope_search_panel_counters_and_grouping(self):
        for role, field_name, scope in (
            ("department_head", "managed_department_id", self.department),
            ("dean", "managed_faculty_id", self.faculty),
        ):
            self._appoint(role)
            model = self.env["university.teacher"]
            domain = [("id", "=", self.teacher.id)]
            self.assertEqual(model.search(domain + [(field_name, "=", scope.id)]), self.teacher)
            self.assertEqual(model._read_group(domain, [field_name], ["__count"]), [(scope, 1)])
            panel = model.search_panel_select_range(field_name, search_domain=domain, enable_counters=True)
            value = next(value for value in panel["values"] if value["id"] == scope.id)
            self.assertEqual(value["__count"], 1)
