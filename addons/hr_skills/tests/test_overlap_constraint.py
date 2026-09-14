from datetime import date

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import SkillsCase


@tagged("post_install", "-at_install")
class TestOverlapConstraintTotality(SkillsCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env["hr.employee"].create({"name": "Overlap employee"})

    def test_a_batch_mixing_a_bounded_and_an_open_ended_skill_validates(self):
        """Two edits to one skill in one batch, one of them open-ended.

        The matching domain is a single OR across the whole batch, so a stored
        row can match because of the bounded values and then be date-compared
        against the open-ended ones. Comparing a date to `valid_to = False`
        raised TypeError -- a 500 out of a constraint whose job is to answer
        with a message.
        """
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.skill_piano.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date(2026, 11, 1),
                "valid_to": False,
            },
        )
        self.env.flush_all()

        with self.assertRaises(ValidationError):
            self.env["hr.employee.skill"].create(
                [
                    {
                        "employee_id": self.employee.id,
                        "skill_id": self.skill_piano.id,
                        "skill_level_id": self.level_novice.id,
                        "skill_type_id": self.skill_type.id,
                        "valid_from": date(2026, 10, 16),
                        "valid_to": date(2027, 5, 29),
                    },
                    {
                        "employee_id": self.employee.id,
                        "skill_id": self.skill_piano.id,
                        "skill_level_id": self.level_expert.id,
                        "skill_type_id": self.skill_type.id,
                        "valid_from": date(2026, 2, 15),
                        "valid_to": False,
                    },
                ],
            )

    def _guitar(self, level, valid_from, valid_to):
        return self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.skill_guitar.id,
                "skill_level_id": level.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": valid_from,
                "valid_to": valid_to,
            },
        )

    def test_a_span_inside_a_stored_one_is_refused(self):
        self._guitar(self.level_novice, date(2025, 1, 1), date(2025, 12, 31))

        with self.assertRaises(ValidationError):
            self._guitar(self.level_expert, date(2025, 3, 1), date(2025, 4, 1))

    def test_a_span_enclosing_a_stored_one_is_refused(self):
        self._guitar(self.level_novice, date(2025, 3, 1), date(2025, 4, 1))

        with self.assertRaises(ValidationError):
            self._guitar(self.level_expert, date(2025, 1, 1), date(2025, 12, 31))

    def test_an_open_ended_span_starting_earlier_is_refused(self):
        self._guitar(self.level_novice, date(2025, 3, 1), False)

        with self.assertRaises(ValidationError):
            self._guitar(self.level_expert, date(2025, 1, 1), False)

    def test_widening_a_row_over_another_is_refused(self):
        self._guitar(self.level_novice, date(2025, 1, 1), date(2025, 1, 31))
        later = self._guitar(self.level_expert, date(2025, 3, 1), date(2025, 3, 31))

        with self.assertRaises(ValidationError):
            later.valid_from = date(2024, 12, 1)

    def test_back_to_back_spans_are_accepted(self):
        self._guitar(self.level_novice, date(2025, 1, 1), date(2025, 1, 31))
        self._guitar(self.level_expert, date(2025, 2, 1), False)

        self.assertEqual(len(self.employee.employee_skill_ids), 2)

    def test_the_span_predicate_is_total(self):
        spans_overlap = self.env["hr.employee.skill"]._spans_overlap

        self.assertTrue(spans_overlap(date(2025, 1, 1), False, date(2024, 1, 1), False))
        self.assertTrue(
            spans_overlap(date(2025, 1, 1), False, date(2024, 1, 1), date(2025, 1, 1))
        )
        self.assertFalse(
            spans_overlap(date(2025, 1, 1), False, date(2024, 1, 1), date(2024, 12, 31))
        )

    def test_the_error_names_the_skill_rather_than_dumping_a_vals_dict(self):
        self.env["hr.employee.skill"].create(
            {
                "employee_id": self.employee.id,
                "skill_id": self.skill_guitar.id,
                "skill_level_id": self.level_novice.id,
                "skill_type_id": self.skill_type.id,
                "valid_from": date(2026, 1, 1),
                "valid_to": False,
            },
        )
        self.env.flush_all()

        with self.assertRaises(ValidationError) as caught:
            self.env["hr.employee.skill"].create(
                {
                    "employee_id": self.employee.id,
                    "skill_id": self.skill_guitar.id,
                    "skill_level_id": self.level_expert.id,
                    "skill_type_id": self.skill_type.id,
                    "valid_from": date(2026, 6, 1),
                    "valid_to": False,
                },
            )
        message = str(caught.exception)
        self.assertIn("Guitar", message)
        self.assertNotIn("employee_id", message)
        self.assertNotIn("{", message)
