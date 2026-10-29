# See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestSchool(common.TransactionCase):
    def setUp(self):
        super(TestSchool, self).setUp()
        self.student_student_obj = self.env["student.student"]
        self.teacher_obj = self.env["school.teacher"]
        self.parent_obj = self.env["school.parent"]
        self.school_school_obj = self.env["school.school"]
        self.school_standard_obj = self.env["school.standard"]
        self.res_company_obj = self.env["res.company"]
        self.assign_roll_obj = self.env["assign.roll.no"]
        self.school_id = self.env.ref("school.demo_school_1")
        self.standard_medium = self.env.ref("school.demo_standard_medium_1")
        self.year = self.env.ref("school.demo_academic_year_2")
        self.currency_id = self.env.ref("base.INR")
        self.sch = self.env.ref("school.demo_school_1")
        self.country_id = self.env.ref("base.in")
        self.std = self.env.ref("school.demo_standard_standard_1")
        self.state_id = self.env.ref("base.state_in_gj")
        self.subject1 = self.env.ref("school.demo_subject_subject_1")
        self.subject2 = self.env.ref("school.demo_subject_subject_2")
        self.student_student = self.env.ref("school.demo_student_student_2")
        self.student_done = self.env.ref("school.demo_student_student_6")
        self.parent = self.env.ref("school.demo_student_parent_1")
        student_list = [self.student_done.id]
        self.student_student._compute_student_age()
        self.student_student.check_age()
        self.student_student.admission_done()
        self.student_student.set_alumni()
        self.parent.student_id = [(6, 0, student_list)]
        # Create academic Year
        self.academic_year_obj = self.env["academic.year"]
        self.academic_year = self.academic_year_obj.create(
            {
                "sequence": 7,
                "code": "2012",
                "name": "2012 Year",
                "date_start": "2012-01-01",
                "date_stop": "2012-12-31",
            }
        )
        self.academic_year._check_academic_year()
        self.academic_month_obj = self.env["academic.month"]
        # Academic month created
        self.academic_month = self.academic_month_obj.create(
            {
                "name": "May",
                "code": "may",
                "date_start": "2012-05-01",
                "date_stop": "2012-05-31",
                "year_id": self.academic_year.id,
            }
        )
        self.academic_month._check_year_limit()
        self.assign_roll_no = self.assign_roll_obj.create(
            {"standard_id": self.std.id, "medium_id": self.standard_medium.id}
        )
        self.assign_roll_no.assign_rollno()

    def test_school(self):
        self.assertEqual(
            self.student_student.school_id,
            self.student_student.standard_id.school_id,
        )
