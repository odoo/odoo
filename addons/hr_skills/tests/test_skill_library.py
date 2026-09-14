from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests import new_test_user, tagged

from .common import SkillsCase


@tagged("post_install", "-at_install")
class TestDefaultSkillLevel(SkillsCase):
    def test_promoting_several_levels_at_once_keeps_the_last(self):
        (self.level_novice | self.level_expert).write({"default_level": True})

        defaults = self.skill_type.skill_level_ids.filtered("default_level")
        self.assertEqual(defaults, self.level_expert)

    def test_promoting_one_level_demotes_the_others(self):
        self.level_novice.default_level = True
        self.level_expert.default_level = True

        defaults = self.skill_type.skill_level_ids.filtered("default_level")
        self.assertEqual(defaults, self.level_expert)

    def test_creating_levels_across_two_types_keeps_one_default_each(self):
        other_type = self.env["hr.skill.type"].create({"name": "Voices"})
        self.env["hr.skill"].create(
            {"name": "Tenor", "skill_type_id": other_type.id},
        )
        self.env["hr.skill.level"].create(
            [
                {
                    "name": "Mine",
                    "skill_type_id": self.skill_type.id,
                    "level_progress": 60,
                    "default_level": True,
                },
                {
                    "name": "Theirs",
                    "skill_type_id": other_type.id,
                    "level_progress": 60,
                    "default_level": True,
                },
            ],
        )

        self.assertEqual(
            len(self.skill_type.skill_level_ids.filtered("default_level")), 1
        )
        self.assertEqual(len(other_type.skill_level_ids.filtered("default_level")), 1)


@tagged("post_install", "-at_install")
class TestSkillTypeCopy(SkillsCase):
    def test_a_copy_keeps_each_skill_sequence(self):
        self.skill_piano.sequence = 30
        self.skill_guitar.sequence = 1
        self.env.flush_all()

        copy = self.skill_type.copy()

        self.assertEqual(
            [(skill.name, skill.sequence) for skill in copy.skill_ids],
            [("Guitar", 1), ("Piano", 30)],
        )

    def test_a_copy_is_renamed_and_uncoloured(self):
        copy = self.skill_type.copy()
        self.assertIn("Instruments", copy.name)
        self.assertNotEqual(copy.name, self.skill_type.name)
        self.assertEqual(copy.color, 0)

    def test_a_copy_keeps_the_values_it_is_given(self):
        copy = self.skill_type.copy({"name": "Strings", "color": 4})
        self.assertEqual((copy.name, copy.color), ("Strings", 4))


@tagged("post_install", "-at_install")
class TestLibraryTypeFollowsTheRows(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Library employee"})
        cls.env["hr.employee.skill"].create(
            {
                "employee_id": cls.employee.id,
                "skill_id": cls.skill_piano.id,
                "skill_level_id": cls.level_novice.id,
                "skill_type_id": cls.skill_type.id,
            },
        )

    def test_a_skill_in_use_cannot_change_type(self):
        with self.assertRaises(ValidationError):
            self.skill_piano.skill_type_id = self.certification_type

    def test_a_level_in_use_cannot_change_type(self):
        with self.assertRaises(ValidationError):
            self.level_novice.skill_type_id = self.certification_type

    def test_an_unused_skill_and_level_move_freely(self):
        self.skill_guitar.skill_type_id = self.certification_type
        self.level_expert.skill_type_id = self.certification_type
        self.assertEqual(self.skill_guitar.skill_type_id, self.certification_type)
        self.assertEqual(self.level_expert.skill_type_id, self.certification_type)

    def test_a_plain_employee_cannot_add_skills_to_the_library(self):
        user = new_test_user(self.env, login="library.plain", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.env["hr.skill"].with_user(user).create(
                {"name": "Self-made", "skill_type_id": self.skill_type.id}
            )

    def test_every_individual_skill_model_is_checked(self):
        models = self.env[
            "mixin.hr.individual.skill"
        ]._concrete_individual_skill_models()
        self.assertIn("hr.employee.skill", [model._name for model in models])
        self.assertIn("hr.job.skill", [model._name for model in models])


@tagged("post_install", "-at_install")
class TestCertificationTypeLookup(SkillsCase):
    def test_one_helper_answers_for_every_call_site(self):
        found = self.env["hr.skill.type"]._get_certification_type()
        self.assertTrue(found.is_certification)

        employee = self.env["hr.employee"].create({"name": "Anyone"})
        self.assertTrue(employee.display_certification_page)


@tagged("post_install", "-at_install")
class TestSkillDefaults(SkillsCase):
    """The defaults read row zero, so the order must be deterministic."""

    def test_the_level_default_survives_two_levels_marked_default(self):
        # Only write() and create() keep one default per type; a row written
        # around them (an import, an older database) can leave two, and a
        # Many2one cannot take a recordset of two.
        self.env.cr.execute(
            "UPDATE hr_skill_level SET default_level = TRUE WHERE skill_type_id = %s",
            (self.skill_type.id,),
        )
        self.env.invalidate_all()

        row = self.env["hr.employee.skill"].new(
            {"skill_type_id": self.skill_type.id},
        )
        self.assertEqual(len(row.skill_level_id), 1)

    def test_the_orders_that_feed_the_defaults_are_total(self):
        for model in ("hr.skill", "hr.skill.level"):
            self.assertIn(
                "id",
                [part.strip().split()[0] for part in self.env[model]._order.split(",")],
                f"{model}._order must end in a unique column, or the default "
                f"picked by [:1] varies between reads",
            )

    def test_changing_the_type_moves_the_level_with_it(self):
        other_type = self.env["hr.skill.type"].create({"name": "Woodwind"})
        other_skill = self.env["hr.skill"].create(
            {"name": "Flute", "skill_type_id": other_type.id},
        )
        other_level = self.env["hr.skill.level"].create(
            {
                "name": "Woodwind novice",
                "skill_type_id": other_type.id,
                "level_progress": 30,
            },
        )
        row = self.env["hr.employee.skill"].new(
            {"skill_type_id": self.skill_type.id},
        )
        row.skill_type_id = other_type

        self.assertEqual(row.skill_id, other_skill)
        self.assertEqual(row.skill_level_id, other_level)


@tagged("post_install", "-at_install")
class TestCommandShape(SkillsCase):
    """The transformation emits Command tuples, not raw magic numbers."""

    def test_the_emitted_commands_are_command_values(self):
        employee = self.env["hr.employee"].create({"name": "Command employee"})
        commands = self.env["hr.employee.skill"]._get_transformed_commands(
            [
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
            employee,
        )
        self.assertTrue(commands)
        for command in commands:
            self.assertIn(command[0], (Command.CREATE, Command.UPDATE, Command.DELETE))
