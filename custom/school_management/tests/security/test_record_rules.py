from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tools.safe_eval import safe_eval


class TestSchoolManagementRecordRules(TransactionCase):
    def setUp(self):
        super().setUp()
        self.year = self.env["university.academic.year"].create({
            "name": "Rule Test Academic Year",
            "date_start": "2035-01-01",
            "date_end": "2035-12-31",
        })
        self.semester = self.env["university.semester"].create({
            "name": "Rule Test Semester",
            "academic_year_id": self.year.id,
            "semester_type": "semester_1",
            "date_start": "2035-01-01",
            "date_end": "2035-06-30",
        })
        self.faculty_a = self.env["university.faculty"].create({
            "name": "Rule Test Faculty A", "code": "RTFA"
        })
        self.faculty_b = self.env["university.faculty"].create({
            "name": "Rule Test Faculty B", "code": "RTFB"
        })
        self.department_a = self.env["university.department"].create({
            "name": "Rule Test Department A", "code": "RTDA", "faculty_id": self.faculty_a.id
        })
        self.department_b = self.env["university.department"].create({
            "name": "Rule Test Department B", "code": "RTDB", "faculty_id": self.faculty_b.id
        })

        self.normal_user = self._make_user("rule.normal", "group_school_user")
        self.dean_user = self._make_user("rule.dean", "group_school_dean")
        self.hod_user = self._make_user("rule.hod", "group_school_hod")
        self._appoint(self.dean_user, self.department_a, "dean", self.faculty_a)
        self._appoint(self.hod_user, self.department_a, "department_head")

        holiday_model = self.env["university.holiday"]
        self.university_holiday = holiday_model.create({
            "name": "University Holiday", "academic_year_id": self.year.id,
            "date_start": "2035-02-01", "date_end": "2035-02-01",
        })
        self.faculty_a_holiday = holiday_model.create({
            "name": "Faculty A Holiday", "academic_year_id": self.year.id,
            "faculty_id": self.faculty_a.id,
            "date_start": "2035-02-02", "date_end": "2035-02-02",
        })
        self.faculty_b_holiday = holiday_model.create({
            "name": "Faculty B Holiday", "academic_year_id": self.year.id,
            "faculty_id": self.faculty_b.id,
            "date_start": "2035-02-03", "date_end": "2035-02-03",
        })
        term_model = self.env["university.department.term"]
        self.term_a = term_model.create({
            "semester_id": self.semester.id, "department_id": self.department_a.id,
            "date_start": "2035-01-01", "date_end": "2035-06-30",
        })
        self.term_b = term_model.create({
            "semester_id": self.semester.id, "department_id": self.department_b.id,
            "date_start": "2035-01-01", "date_end": "2035-06-30",
        })

    def _make_user(self, login, group_xmlid):
        groups = self.env.ref("base.group_user") | self.env.ref(
            "school_management.%s" % group_xmlid
        )
        return self.env["res.users"].with_context(no_reset_password=True).create({
            "name": login,
            "login": login,
            "email": "%s@example.test" % login,
            "group_ids": [(6, 0, groups.ids)],
        })

    def _appoint(self, user, department, role, faculty=False):
        teacher = self.env["university.teacher"].create({
            "name": "%s Teacher" % user.name,
            "department_id": department.id,
            "user_id": user.id,
        })
        user.write({"teacher_id": teacher.id})
        values = {
            "staff_id": teacher.id,
            "role": role,
            "start_date": fields.Date.today(),
        }
        if faculty:
            values["faculty_id"] = faculty.id
        else:
            values["department_id"] = department.id
        self.env["university.academic.assignment"].create(values)

    def test_module_rule_domains_evaluate_and_target_registered_models(self):
        rule_data = self.env["ir.model.data"].search([
            ("module", "=", "school_management"), ("model", "=", "ir.rule"),
        ])
        self.assertTrue(rule_data)
        for data in rule_data:
            rule = self.env["ir.rule"].browse(data.res_id).exists()
            self.assertTrue(rule, "%s points to a missing rule" % data.complete_name)
            self.assertIn(rule.model_id.model, self.env.registry.models)
            self.assertIsInstance(safe_eval(rule.domain_force, {"user": self.env.user}), list)
            self.assertNotEqual(rule.domain_force, rule.model_id.model)

    def test_holiday_and_department_term_visibility_is_scoped(self):
        holiday_model = self.env["university.holiday"]
        term_model = self.env["university.department.term"]

        holiday_domain = [("id", "in", [
            self.university_holiday.id,
            self.faculty_a_holiday.id,
            self.faculty_b_holiday.id,
        ])]
        term_domain = [("id", "in", [self.term_a.id, self.term_b.id])]
        all_holidays = {
            self.university_holiday.id,
            self.faculty_a_holiday.id,
            self.faculty_b_holiday.id,
        }
        self.assertEqual(
            set(holiday_model.with_user(self.normal_user).search(holiday_domain).ids),
            all_holidays,
        )
        self.assertEqual(
            set(holiday_model.with_user(self.dean_user).search(holiday_domain).ids),
            all_holidays,
        )
        self.assertEqual(
            set(holiday_model.with_user(self.hod_user).search(holiday_domain).ids),
            all_holidays,
        )
        self.assertEqual(term_model.with_user(self.dean_user).search(term_domain), self.term_a)
        self.assertEqual(term_model.with_user(self.hod_user).search(term_domain), self.term_a)
        with self.assertRaises(AccessError):
            term_model.with_user(self.normal_user).search(term_domain)
