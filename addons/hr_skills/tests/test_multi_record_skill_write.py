from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.fields import Command
from odoo.tests import tagged

from .common import SkillsCase


@tagged("post_install", "-at_install")
class TestMultiRecordSkillWrite(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.novice_holder, cls.newcomer = cls.env["hr.employee"].create(
            [{"name": "Already plays"}, {"name": "Brand new"}],
        )

    def _piano_rows(self, employee):
        return employee.employee_skill_ids.filtered(
            lambda skill: skill.skill_id == self.skill_piano
        )

    def test_skill_lands_on_every_employee(self):
        (self.novice_holder | self.newcomer).write(
            {
                "employee_skill_ids": [
                    [
                        0,
                        0,
                        {
                            "skill_id": self.skill_piano.id,
                            "skill_level_id": self.level_novice.id,
                            "skill_type_id": self.skill_type.id,
                        },
                    ]
                ],
            },
        )

        for employee in (self.novice_holder, self.newcomer):
            self.assertEqual(len(self._piano_rows(employee)), 1, employee.name)

    def test_existing_skill_is_archived_on_every_employee(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.novice_holder.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today - relativedelta(months=2),
            },
        )

        (self.novice_holder | self.newcomer).write(
            {
                "employee_skill_ids": [
                    [
                        0,
                        0,
                        {
                            "skill_id": self.skill_piano.id,
                            "skill_level_id": self.level_expert.id,
                            "skill_type_id": self.skill_type.id,
                        },
                    ]
                ],
            },
        )

        superseded = self._piano_rows(self.novice_holder).filtered("valid_to")
        self.assertEqual(superseded.skill_level_id, self.level_novice)
        self.assertEqual(superseded.valid_to, self.today - relativedelta(days=1))

        for employee in (self.novice_holder, self.newcomer):
            live = self._piano_rows(employee).filtered(lambda skill: not skill.valid_to)
            self.assertEqual(len(live), 1, employee.name)
            self.assertEqual(live.skill_level_id, self.level_expert, employee.name)

    def test_a_line_is_edited_only_on_the_employee_that_owns_it(self):
        owned = self.env["hr.employee.skill"].create(
            {
                "employee_id": self.novice_holder.id,
                "skill_id": self.skill_guitar.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today,
            },
        )

        (self.novice_holder | self.newcomer).write(
            {
                "employee_skill_ids": [
                    [1, owned.id, {"skill_level_id": self.level_expert.id}]
                ],
            },
        )

        rows = self.novice_holder.employee_skill_ids.filtered(
            lambda skill: skill.skill_id == self.skill_guitar
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows.skill_level_id, self.level_expert)
        self.assertFalse(self.newcomer.employee_skill_ids)

    def _hold_piano(self, employees):
        self.env["hr.employee.skill"].create(
            [
                {
                    "employee_id": employee.id,
                    "skill_id": self.skill_piano.id,
                    "skill_level_id": self.level_novice.id,
                    "skill_type_id": self.skill_type.id,
                    "valid_from": self.today - relativedelta(months=2),
                }
                for employee in employees
            ]
        )
        self.env.flush_all()
        self.env.invalidate_all()

    def _queries_to_promote(self, employees):
        before = self.env.cr.sql_statement_count
        employees.write(
            {
                "current_employee_skill_ids": [
                    Command.create(
                        {
                            "skill_id": self.skill_piano.id,
                            "skill_level_id": self.level_expert.id,
                            "skill_type_id": self.skill_type.id,
                        }
                    )
                ]
            }
        )
        self.env.flush_all()
        return self.env.cr.sql_statement_count - before

    def test_the_cost_of_a_multi_record_write_does_not_grow_with_the_records(self):
        few = self.env["hr.employee"].create([{"name": f"Few {i}"} for i in range(2)])
        many = self.env["hr.employee"].create([{"name": f"Many {i}"} for i in range(8)])
        self._hold_piano(few | many)

        few_queries = self._queries_to_promote(few)
        self.env.invalidate_all()
        many_queries = self._queries_to_promote(many)

        self.assertEqual(many_queries, few_queries)
        for employee in few | many:
            live = self._piano_rows(employee).filtered(lambda row: not row.valid_to)
            self.assertEqual(live.skill_level_id, self.level_expert, employee.name)

    def test_a_certification_one_of_them_holds_is_added_to_the_others_only(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.novice_holder.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": self.today,
            },
        )
        (self.novice_holder | self.newcomer).write(
            {
                "current_employee_skill_ids": [
                    Command.create(
                        {
                            "skill_id": self.certification.id,
                            "skill_level_id": self.level_certified.id,
                            "skill_type_id": self.certification_type.id,
                            "valid_from": self.today,
                        }
                    )
                ]
            }
        )
        for employee in (self.novice_holder, self.newcomer):
            self.assertEqual(
                len(employee.employee_skill_ids.filtered("is_certification")),
                1,
                employee.name,
            )

    def test_creating_an_employee_without_skills_touches_no_skill_field(self):
        employee = self.env["hr.employee"].create({"name": "No skills at all"})
        self.assertFalse(employee.employee_skill_ids)
