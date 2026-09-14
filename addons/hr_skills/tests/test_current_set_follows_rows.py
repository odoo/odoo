from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from .common import SkillsCase


@tagged("post_install", "-at_install")
class TestCurrentSetFollowsTheRows(SkillsCase):
    """current_* and skill_ids are derived from the rows' dates and types.

    They depended on the one2many alone, so editing a row's ``valid_to`` or
    ``skill_type_id`` in the same transaction left every derived field serving
    the value cached before the edit. Nothing here calls ``invalidate_all``;
    that is the point.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.employee = cls.env["hr.employee"].create({"name": "Follows employee"})
        cls.job = cls.env["hr.job"].create({"name": "Follows job"})

    def _piano(self, owner_field, owner):
        return self.env[
            "hr.employee.skill" if owner_field == "employee_id" else "hr.job.skill"
        ].create(
            {
                owner_field: owner.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": self.today - relativedelta(months=3),
            },
        )

    def test_an_employee_skill_that_lapses_leaves_the_current_set_at_once(self):
        row = self._piano("employee_id", self.employee)
        self.assertEqual(self.employee.current_employee_skill_ids, row)
        self.assertEqual(self.employee.skill_ids, self.skill_piano)

        row.valid_to = self.today - relativedelta(days=1)

        self.assertFalse(self.employee.current_employee_skill_ids)
        self.assertFalse(self.employee.skill_ids)

    def test_a_job_skill_that_lapses_leaves_the_current_set_at_once(self):
        row = self._piano("job_id", self.job)
        self.assertEqual(self.job.current_job_skill_ids, row)
        self.assertEqual(self.job.skill_ids, self.skill_piano)

        row.valid_to = self.today - relativedelta(days=1)

        self.assertFalse(self.job.current_job_skill_ids)
        self.assertFalse(self.job.skill_ids)

    def test_certification_ids_follow_the_row_type(self):
        row = self._piano("employee_id", self.employee)
        self.assertFalse(self.employee.certification_ids)

        row.write(
            {
                "skill_type_id": self.certification_type.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
            },
        )

        self.assertEqual(self.employee.certification_ids, row)

    def test_a_job_never_keeps_a_lapsed_certification_as_current(self):
        """The employee side shows the latest lapsed certification so its holder
        sees what expired; a job cannot set validity periods, so for it a lapsed
        requirement is simply gone. Both go through one helper now."""
        self.env["hr.job.skill"].create(
            {
                "job_id": self.job.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": self.today - relativedelta(months=3),
                "valid_to": self.today - relativedelta(days=1),
            },
        )
        lapsed = self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.certification.id,
                "skill_level_id": self.level_certified.id,
                "skill_type_id": self.certification_type.id,
                "valid_from": self.today - relativedelta(months=3),
                "valid_to": self.today - relativedelta(days=1),
            },
        )
        self.assertFalse(self.job.current_job_skill_ids)
        self.assertEqual(self.employee.current_employee_skill_ids, lapsed)


@tagged("post_install", "-at_install")
class TestEveryX2ManyCommandIsAnswered(SkillsCase):
    """The transformation used to recognise CREATE, UPDATE and DELETE and drop
    everything else on the floor, so a CLEAR left the list untouched and
    reported success."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()
        cls.employee, cls.other = cls.env["hr.employee"].create(
            [{"name": "Cleared employee"}, {"name": "Other employee"}],
        )
        cls.old_piano = cls.env["hr.employee.skill"].create(
            {
                "employee_id": cls.employee.id,
                "skill_id": cls.skill_piano.id,
                "skill_level_id": cls.level_novice.id,
                "skill_type_id": cls.skill_type.id,
                "valid_from": cls.today - relativedelta(months=3),
            },
        )
        cls.new_guitar = cls.env["hr.employee.skill"].create(
            {
                "employee_id": cls.employee.id,
                "skill_id": cls.skill_guitar.id,
                "skill_level_id": cls.level_novice.id,
                "skill_type_id": cls.skill_type.id,
                "valid_from": cls.today,
            },
        )
        cls.history = cls.env["hr.employee.skill"].create(
            {
                "employee_id": cls.employee.id,
                "skill_id": cls.skill_guitar.id,
                "skill_level_id": cls.level_expert.id,
                "skill_type_id": cls.skill_type.id,
                "valid_from": cls.today - relativedelta(years=1),
                "valid_to": cls.today - relativedelta(months=6),
            },
        )
        cls.foreign = cls.env["hr.employee.skill"].create(
            {
                "employee_id": cls.other.id,
                "skill_id": cls.skill_piano.id,
                "skill_level_id": cls.level_expert.id,
                "skill_type_id": cls.skill_type.id,
                "valid_from": cls.today - relativedelta(months=3),
            },
        )
        cls.env.flush_all()

    def test_clear_ends_every_current_skill_and_keeps_the_history(self):
        self.employee.write({"current_employee_skill_ids": [Command.clear()]})

        self.assertFalse(self.employee.current_employee_skill_ids)
        self.assertEqual(
            self.old_piano.valid_to,
            self.today - relativedelta(days=1),
            "a skill held for months is closed, not erased",
        )
        self.assertFalse(self.new_guitar.exists(), "a skill added today never existed")
        self.assertTrue(self.history.exists(), "history is not the list's to clear")
        self.assertEqual(self.other.current_employee_skill_ids, self.foreign)

    def test_set_of_the_rows_already_shown_changes_nothing(self):
        shown = self.employee.current_employee_skill_ids
        self.employee.write({"current_employee_skill_ids": [Command.set(shown.ids)]})
        self.assertEqual(self.employee.current_employee_skill_ids, shown)

    def test_set_that_drops_a_row_ends_it(self):
        self.employee.write(
            {"current_employee_skill_ids": [Command.set(self.old_piano.ids)]}
        )
        self.assertEqual(self.employee.current_employee_skill_ids, self.old_piano)
        self.assertFalse(self.new_guitar.exists())

    def test_linking_another_employee_row_is_refused_rather_than_ignored(self):
        with self.assertRaisesRegex(ValidationError, "belong to another record"):
            self.employee.write(
                {"current_employee_skill_ids": [Command.link(self.foreign.id)]}
            )

    def test_updating_another_employee_row_is_refused_rather_than_moving_it(self):
        with self.assertRaisesRegex(ValidationError, "belong to another record"):
            self.employee.write(
                {
                    "current_employee_skill_ids": [
                        Command.update(
                            self.foreign.id, {"skill_level_id": self.level_novice.id}
                        )
                    ]
                }
            )
        self.assertEqual(self.foreign.employee_id, self.other)
        self.assertFalse(self.foreign.valid_to)

    def test_deleting_another_employee_row_is_refused(self):
        with self.assertRaisesRegex(ValidationError, "belong to another record"):
            self.employee.write(
                {"current_employee_skill_ids": [Command.delete(self.foreign.id)]}
            )

    def test_a_multi_record_write_refuses_a_row_none_of_them_owns(self):
        third = self.env["hr.employee"].create({"name": "Bystander"})
        with self.assertRaisesRegex(ValidationError, "belong to another record"):
            (self.employee | third).write(
                {"current_employee_skill_ids": [Command.delete(self.foreign.id)]}
            )

    def test_a_multi_record_set_routes_each_row_to_its_owner(self):
        (self.employee | self.other).write(
            {
                "current_employee_skill_ids": [
                    Command.set([self.old_piano.id, self.foreign.id])
                ],
            },
        )
        self.assertEqual(self.employee.current_employee_skill_ids, self.old_piano)
        self.assertEqual(self.other.current_employee_skill_ids, self.foreign)
        self.assertFalse(self.new_guitar.exists())

    def test_an_unknown_command_fails_loudly(self):
        with self.assertRaises(NotImplementedError):
            self.env["hr.employee.skill"]._get_transformed_commands(
                [(9, 0, 0)], self.employee
            )


@tagged("post_install", "-at_install")
class TestOneCommandPerRow(SkillsCase):
    """Closing a skill and creating its successor in one batch closed the old
    row twice: once for the DELETE or CLEAR, once more when the CREATE found it
    still live. The ORM tolerated the duplicate, so nothing failed; the batch
    simply did the same work twice."""

    def _commands_for(self, *client_commands):
        employee = self.env["hr.employee"].create({"name": "One command employee"})
        old = self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date.today() - relativedelta(months=2),
            },
        )
        self.env.flush_all()
        successor = Command.create(
            {
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_expert.id,
                "skill_type_id": self.skill_type.id,
            },
        )
        commands = self.env["hr.employee.skill"]._get_transformed_commands(
            [command(old) for command in client_commands] + [successor], employee
        )
        return old, commands

    def _assert_each_row_once(self, old, commands):
        touched = [command[1] for command in commands if command[0] != Command.CREATE]
        self.assertEqual(touched, [old.id])
        self.assertEqual(
            [command for command in commands if command[0] == Command.CREATE].__len__(),
            1,
        )

    def test_delete_then_create_closes_the_old_row_once(self):
        old, commands = self._commands_for(lambda row: Command.delete(row.id))
        self._assert_each_row_once(old, commands)

    def test_clear_then_create_closes_the_old_row_once(self):
        old, commands = self._commands_for(lambda row: Command.clear())
        self._assert_each_row_once(old, commands)

    def test_a_level_change_closes_the_old_row_once(self):
        employee = self.env["hr.employee"].create({"name": "Level change employee"})
        for age in (relativedelta(months=2), relativedelta()):
            with self.subTest(age=age):
                old = self.env["hr.employee.skill"].create(
                    {
                        "employee_id": employee.id,
                        "skill_id": self.skill_piano.id,
                        "skill_level_id": self.level_novice.id,
                        "skill_type_id": self.skill_type.id,
                        "valid_from": date.today() - age,
                    },
                )
                commands = self.env["hr.employee.skill"]._get_transformed_commands(
                    [Command.update(old.id, {"skill_level_id": self.level_expert.id})],
                    employee,
                )
                self._assert_each_row_once(old, commands)
                old.unlink()

    def test_two_updates_of_one_row_make_one_successor(self):
        employee = self.env["hr.employee"].create({"name": "Two updates employee"})
        old = self.env["hr.employee.skill"].create(
            {
                "employee_id": employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date.today() - relativedelta(months=2),
            },
        )
        commands = self.env["hr.employee.skill"]._get_transformed_commands(
            [
                Command.update(old.id, {"skill_id": self.skill_guitar.id}),
                Command.update(old.id, {"skill_level_id": self.level_expert.id}),
            ],
            employee,
        )
        self._assert_each_row_once(old, commands)
        (created,) = [
            command[2] for command in commands if command[0] == Command.CREATE
        ]
        self.assertEqual(
            (created["skill_id"], created["skill_level_id"]),
            (self.skill_guitar.id, self.level_expert.id),
        )


@tagged("post_install", "-at_install")
class TestCreatingAnOwnerFromCopiedLines(SkillsCase):
    """copy_data() emits the lines with the old owner's id still in them; the
    ORM overwrites it on the new owner, but the transformation ran the
    collision check against it and closed the copied record's live skills.
    hr.applicant copies its skills, so duplicating an applicant into a talent
    pool emptied the applicant."""

    def test_the_source_of_a_copy_keeps_its_skills(self):
        source = self.env["hr.employee"].create({"name": "Copy source"})
        live = self.env["hr.employee.skill"].create(
            {
                "employee_id": source.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date.today() - relativedelta(months=2),
            },
        )
        self.env.flush_all()
        line_vals = live.copy_data()[0]
        self.assertEqual(
            line_vals["employee_id"], source.id, "copy_data keeps the parent"
        )

        commands = self.env["hr.employee.skill"]._get_transformed_commands(
            [Command.create(line_vals)], self.env["hr.employee"]
        )

        self.assertEqual([command[0] for command in commands], [Command.CREATE])
        self.assertNotIn("employee_id", commands[0][2])
        self.assertTrue(live.exists())
        self.assertFalse(live.valid_to)
