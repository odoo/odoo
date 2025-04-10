from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests import TransactionCase, tagged


@tagged("recruitment")
class TestCertificationActivities(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()

        cls.t_job = cls.env["hr.job"].create({"name": "Test Job"})
        cls.t_user_1, cls.t_user_2 = cls.env["res.users"].create(
            [
                {
                    "name": "Test User 1",
                    "login": "user_1",
                    "password": "password",
                },
                {
                    "name": "Test User 2",
                    "login": "user_2",
                    "password": "password",
                },
            ],
        )
        cls.t_cert_type = cls.env["hr.skill.type"].create({"name": "Certification for tests", "is_certification": True})
        cls.t_cert_level_1, cls.t_cert_level_2 = cls.env["hr.skill.level"].create(
            [
                {"name": "Half Certified", "skill_type_id": cls.t_cert_type.id, "level_progress": 50},
                {"name": "Fully Certified", "skill_type_id": cls.t_cert_type.id, "level_progress": 100},
            ],
        )
        cls.t_cert_1, cls.t_cert_2 = cls.env["hr.skill"].create(
            [
                {"name": "Certification 1", "skill_type_id": cls.t_cert_type.id},
                {"name": "Certification 2", "skill_type_id": cls.t_cert_type.id},
            ],
        )
        cls.t_job_cert_1, cls.t_job_cert_2 = cls.env["hr.job.skill"].create(
            [
                {
                    "job_id": cls.t_job.id,
                    "skill_id": cls.t_cert_1.id,
                    "skill_level_id": cls.t_cert_level_1.id,
                    "skill_type_id": cls.t_cert_type.id,
                    "valid_from": cls.today,
                    "valid_to": False,
                },
                {
                    "job_id": cls.t_job.id,
                    "skill_id": cls.t_cert_2.id,
                    "skill_level_id": cls.t_cert_level_2.id,
                    "skill_type_id": cls.t_cert_type.id,
                    "valid_from": cls.today,
                    "valid_to": False,
                },
            ],
        )

        cls.t_employee_1 = cls.env["hr.employee"].create(
            [
                {"name": "test employee 1", "job_id": cls.t_job.id, "user_id": cls.t_user_1.id},
            ],
        )

    def test_employee_with_no_certifications_gets_activity(self):
        """
        Assert that if an employee has none of the certifications from the job,
        an activity will be created for each missing certification.
        """
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertEqual(len(activities), 2)
        self.assertEqual(self.t_job.job_skill_ids.mapped("display_name"), activities.mapped("summary"))
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_employee_with_correct_certifications_gets_no_activity(self):
        """
        Assert that if an employee has all of the certifications from the job,
        no activities will be created.
        """
        self.env["hr.employee.skill"].create(
            [
                {
                    "employee_id": self.t_employee_1.id,
                    "skill_id": self.t_cert_1.id,
                    "skill_level_id": self.t_cert_level_1.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today,
                    "valid_to": False,
                },
                {
                    "employee_id": self.t_employee_1.id,
                    "skill_id": self.t_cert_2.id,
                    "skill_level_id": self.t_cert_level_2.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today,
                    "valid_to": False,
                },
            ],
        )
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertFalse(activities)

    def test_employee_with_wrong_certifications_gets_activity(self):
        """
        Assert that if an employee has the correct certification(skill_id) but
        the wrong level compared to the job, an activity is created.
        """
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.t_employee_1.id,
                "skill_id": self.t_cert_1.id,
                "skill_level_id": self.t_cert_level_2.id,
                "skill_type_id": self.t_cert_type.id,
                "valid_from": self.today,
                "valid_to": False,
            },
        )
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertEqual(len(activities), 2)
        self.assertEqual(self.t_job.job_skill_ids.mapped("display_name"), activities.mapped("summary"))
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_employee_with_one_correct_certification_gets_one_activity(self):
        """
        Assert that if an employee has one certification out of two from the job,
        only one activity is created.
        """
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.t_employee_1.id,
                "skill_id": self.t_cert_1.id,
                "skill_level_id": self.t_cert_level_1.id,
                "skill_type_id": self.t_cert_type.id,
                "valid_from": self.today,
                "valid_to": False,
            },
        )
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertEqual(len(activities), 1)
        self.assertEqual(self.t_job_cert_2.mapped("display_name"), activities.mapped("summary"))
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_employee_with_correct_but_expired_certifications_gets_activity(self):
        """
        Assert that if an employee has the same certifications as the job but
        they are expired (valid_to < today), activities are created.
        """
        self.env["hr.employee.skill"].create(
            [
                {
                    "employee_id": self.t_employee_1.id,
                    "skill_id": self.t_cert_1.id,
                    "skill_level_id": self.t_cert_level_1.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today - relativedelta(months=2),
                    "valid_to": self.today - relativedelta(months=1),
                },
                {
                    "employee_id": self.t_employee_1.id,
                    "skill_id": self.t_cert_2.id,
                    "skill_level_id": self.t_cert_level_2.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today - relativedelta(months=2),
                    "valid_to": self.today - relativedelta(months=1),
                },
            ],
        )
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertEqual(len(activities), 2)
        self.assertEqual(self.t_job.job_skill_ids.mapped("display_name"), activities.mapped("summary"))
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_employee_with_correct_but_expiring_in_3_months_certifications_gets_activity(self):
        """
        Assert that if an employee has the same certifications as the job but
        one of them is expiring within the next 3 months, an activity is created.
        """
        self.env["hr.employee.skill"].create(
            [
                {
                    "employee_id": self.t_employee_1.id,
                    "skill_id": self.t_cert_1.id,
                    "skill_level_id": self.t_cert_level_1.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today - relativedelta(months=2),
                    "valid_to": self.today + relativedelta(months=3),
                },
                {
                    "employee_id": self.t_employee_1.id,
                    "skill_id": self.t_cert_2.id,
                    "skill_level_id": self.t_cert_level_2.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today - relativedelta(months=2),
                    "valid_to": self.today + relativedelta(months=4),
                },
            ],
        )
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertEqual(len(activities), 1)
        self.assertEqual(self.t_job_cert_1.mapped("display_name"), activities.mapped("summary"))
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_activities_are_only_created_once(self):
        """
        Assert that an activity is only created once if an employee is missing skills.
        """
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertEqual(len(activities), 2)
        self.assertEqual(self.t_job.job_skill_ids.mapped("display_name"), activities.mapped("summary"))
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

        new_activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertFalse(new_activities)

    def test_activities_are_created_for_multiple_employees_with_no_certification(self):
        """
        Assert that activities are created for multiple employees with no certifications.
        """
        employee_2 = self.env["hr.employee"].create(
            {"name": "test employee 2", "job_id": self.t_job.id, "user_id": self.t_user_2.id},
        )
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertEqual(len(activities), 4)
        self.assertEqual(set(self.t_job.job_skill_ids.mapped("display_name")), set(activities.mapped("summary")))
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids) | set(employee_2.ids))

    def test_no_activities_are_created_for_multiple_employees_with_certification(self):
        """
        Assert that no activities are created for multiple employees with the correct certifications.
        """
        employee_2 = self.env["hr.employee"].create(
            {"name": "test employee 2", "job_id": self.t_job.id, "user_id": self.t_user_2.id},
        )
        self.env["hr.employee.skill"].create(
            [
                {
                    "employee_id": self.t_employee_1.id,
                    "skill_id": self.t_cert_1.id,
                    "skill_level_id": self.t_cert_level_1.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today,
                    "valid_to": False,
                },
                {
                    "employee_id": self.t_employee_1.id,
                    "skill_id": self.t_cert_2.id,
                    "skill_level_id": self.t_cert_level_2.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today,
                    "valid_to": False,
                },
                {
                    "employee_id": employee_2.id,
                    "skill_id": self.t_cert_1.id,
                    "skill_level_id": self.t_cert_level_1.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today,
                    "valid_to": False,
                },
                {
                    "employee_id": employee_2.id,
                    "skill_id": self.t_cert_2.id,
                    "skill_level_id": self.t_cert_level_2.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today,
                    "valid_to": False,
                },
            ],
        )
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.assertFalse(activities)
