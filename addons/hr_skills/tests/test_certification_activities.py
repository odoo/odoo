from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.tests import TransactionCase, tagged


@tagged("recruitment")
class TestCertificationActivities(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.demo_data_activities = cls.env[
            "hr.employee"
        ]._add_certification_activity_to_employees()

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
        cls.t_cert_type = cls.env["hr.skill.type"].create(
            {"name": "Certification for tests", "is_certification": True}
        )
        cls.t_cert_level_1, cls.t_cert_level_2 = cls.env["hr.skill.level"].create(
            [
                {
                    "name": "Half Certified",
                    "skill_type_id": cls.t_cert_type.id,
                    "level_progress": 50,
                },
                {
                    "name": "Fully Certified",
                    "skill_type_id": cls.t_cert_type.id,
                    "level_progress": 100,
                },
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
                {
                    "name": "test employee 1",
                    "job_id": cls.t_job.id,
                    "user_id": cls.t_user_1.id,
                },
            ],
        )

    def _own_activities(self, *extra_employees):
        own = self.t_employee_1
        for employee in extra_employees:
            own |= employee
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        return activities.filtered(lambda act: act.res_id in own.ids)

    def test_employee_with_no_certifications_gets_activity(self):
        activities = self._own_activities()
        self.assertEqual(len(activities), 2)
        self.assertEqual(
            self.t_job.job_skill_ids.mapped("display_name"),
            activities.mapped("summary"),
        )
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_employee_with_correct_certifications_gets_no_activity(self):
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
        activities = self._own_activities()
        self.assertFalse(activities)

    def _hold(self, skill, level, valid_from, valid_to=False):
        return self.env["hr.employee.skill"].create(
            {
                "employee_id": self.t_employee_1.id,
                "skill_id": skill.id,
                "skill_level_id": level.id,
                "skill_type_id": self.t_cert_type.id,
                "valid_from": valid_from,
                "valid_to": valid_to,
            },
        )

    def test_employee_with_a_lower_level_gets_activity(self):
        self._hold(self.t_cert_2, self.t_cert_level_1, self.today)
        activities = self._own_activities()
        self.assertEqual(len(activities), 2)
        self.assertEqual(
            self.t_job.job_skill_ids.mapped("display_name"),
            activities.mapped("summary"),
        )

    def test_a_higher_level_than_required_satisfies_it(self):
        self._hold(self.t_cert_1, self.t_cert_level_2, self.today)
        activities = self._own_activities()
        self.assertEqual(
            activities.mapped("summary"), self.t_job_cert_2.mapped("display_name")
        )

    def test_a_renewal_that_takes_over_counts_as_covered(self):
        self._hold(self.t_cert_2, self.t_cert_level_2, self.today)
        ends = self.today + relativedelta(months=1)
        self._hold(
            self.t_cert_1,
            self.t_cert_level_1,
            self.today - relativedelta(years=1),
            ends,
        )
        self._hold(self.t_cert_1, self.t_cert_level_1, ends + relativedelta(days=1))
        self.assertFalse(self._own_activities())

    def test_a_certification_starting_later_does_not_cover_today(self):
        self._hold(self.t_cert_2, self.t_cert_level_2, self.today)
        self._hold(
            self.t_cert_1, self.t_cert_level_1, self.today + relativedelta(days=10)
        )
        activities = self._own_activities()
        self.assertEqual(
            activities.mapped("summary"), self.t_job_cert_1.mapped("display_name")
        )
        self.assertEqual(activities.date_deadline, self.today)

    def test_an_archived_job_requires_nothing(self):
        self.t_job.active = False
        self.assertFalse(self._own_activities())

    def test_employee_with_one_correct_certification_gets_one_activity(self):
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
        activities = self._own_activities()
        self.assertEqual(len(activities), 1)
        self.assertEqual(
            self.t_job_cert_2.mapped("display_name"), activities.mapped("summary")
        )
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_employee_with_correct_but_expired_certifications_gets_activity(self):
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
        activities = self._own_activities()
        self.assertEqual(len(activities), 2)
        self.assertEqual(
            self.t_job.job_skill_ids.mapped("display_name"),
            activities.mapped("summary"),
        )
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_employee_with_correct_but_expiring_in_3_months_certifications_gets_activity(
        self,
    ):
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
        activities = self._own_activities()
        self.assertEqual(len(activities), 1)
        self.assertEqual(
            self.t_job_cert_1.mapped("display_name"), activities.mapped("summary")
        )
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

    def test_a_dropped_requirement_stops_chasing_the_employee(self):
        # The cron read job_skill_ids, which keeps every requirement the job has
        # ever had, so an employee was asked daily to upload a certification the
        # job stopped asking for.
        dropped = self.env["hr.skill"].create(
            {"name": "Dropped requirement", "skill_type_id": self.t_cert_type.id},
        )
        today = self.today
        self.env["hr.job.skill"].create(
            {
                "job_id": self.t_job.id,
                "skill_id": dropped.id,
                "skill_level_id": self.t_cert_level_1.id,
                "skill_type_id": self.t_cert_type.id,
                "valid_from": today - relativedelta(days=300),
                "valid_to": today - relativedelta(days=200),
            },
        )
        self.env.flush_all()

        activities = self.env["hr.employee"]._add_certification_activity_to_employees()

        self.assertFalse(
            [s for s in activities.mapped("summary") if dropped.name in s],
            "a requirement whose validity has passed is not a requirement",
        )

    def test_scheduling_is_batched_per_group_not_per_activity(self):
        """One activity_schedule call per (summary, deadline, responsible).

        activity_schedule already creates one activity per record of the
        recordset it is given, so calling it per employee paid the whole
        scheduling path once per activity.
        """
        manager = self.env["res.users"].create(
            {"name": "Batch manager", "login": "batch_manager"},
        )
        job = self.env["hr.job"].create({"name": "Batch job", "user_id": manager.id})
        skills = self.env["hr.skill"].create(
            [
                {"name": f"Batch skill {i}", "skill_type_id": self.t_cert_type.id}
                for i in range(2)
            ],
        )
        self.env["hr.job.skill"].create(
            [
                {
                    "job_id": job.id,
                    "skill_id": skill.id,
                    "skill_level_id": self.t_cert_level_1.id,
                    "skill_type_id": self.t_cert_type.id,
                    "valid_from": self.today - relativedelta(days=30),
                }
                for skill in skills
            ],
        )
        batch = self.env["hr.employee"].create(
            [{"name": f"Batch employee {i}", "job_id": job.id} for i in range(20)],
        )
        self.env.flush_all()
        self.env.invalidate_all()

        before = self.env.cr.sql_statement_count
        activities = self.env["hr.employee"]._add_certification_activity_to_employees()
        self.env.flush_all()
        cost = self.env.cr.sql_statement_count - before

        # scoped to this test's own employees: the class fixtures qualify too
        mine = activities.filtered(lambda a: a.res_id in batch.ids)
        self.assertEqual(len(mine), 40)
        self.assertLess(
            cost,
            300,
            "20 employees sharing one responsible over 2 requirements is two "
            "groups; scheduling them one at a time cost 709 queries",
        )

    def test_activities_are_only_created_once(self):
        activities = self._own_activities()
        self.assertEqual(len(activities), 2)
        self.assertEqual(
            self.t_job.job_skill_ids.mapped("display_name"),
            activities.mapped("summary"),
        )
        self.assertEqual(set(activities.mapped("res_id")), set(self.t_employee_1.ids))

        new_activities = self._own_activities()
        self.assertFalse(new_activities)

    def test_activities_are_created_for_multiple_employees_with_no_certification(self):
        employee_2 = self.env["hr.employee"].create(
            {
                "name": "test employee 2",
                "job_id": self.t_job.id,
                "user_id": self.t_user_2.id,
            },
        )
        activities = self._own_activities(employee_2)
        self.assertEqual(len(activities), 4)
        self.assertEqual(
            set(self.t_job.job_skill_ids.mapped("display_name")),
            set(activities.mapped("summary")),
        )
        self.assertEqual(
            set(activities.mapped("res_id")),
            set(self.t_employee_1.ids) | set(employee_2.ids),
        )

    def test_no_activities_are_created_for_multiple_employees_with_certification(self):
        employee_2 = self.env["hr.employee"].create(
            {
                "name": "test employee 2",
                "job_id": self.t_job.id,
                "user_id": self.t_user_2.id,
            },
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
        activities = self._own_activities(employee_2)
        self.assertFalse(activities)

    def test_a_reminder_names_the_requirement_it_is_for(self):
        activities = self._own_activities()
        self.assertEqual(
            {
                (activity.certification_skill_id, activity.certification_skill_level_id)
                for activity in activities
            },
            {
                (self.t_cert_1, self.t_cert_level_1),
                (self.t_cert_2, self.t_cert_level_2),
            },
        )

    def test_renaming_a_certification_does_not_repeat_its_reminder(self):
        self.assertEqual(len(self._own_activities()), 2)
        self.t_cert_1.name = "Certification 1 (renamed)"
        self.t_cert_level_2.name = "Fully Certified (renamed)"
        self.env.invalidate_all()
        self.assertFalse(self._own_activities())
