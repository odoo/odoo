# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta
import datetime

from odoo import fields

from odoo.exceptions import ValidationError
from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestEmployeeSkills(TransactionCase):

    @classmethod
    def _create_skill_types(self, vals_list):
        skill_types = self.env['hr.skill.type']
        for vals in vals_list:
            with Form(self.env['hr.skill.type']) as skill_type_form:
                skill_type_form.name = vals['name']
                skill_type_form.is_certification = vals.get('certificate', False)
                for skill_val in vals['skills']:
                    with skill_type_form.skill_ids.new() as skill:
                        skill.name = skill_val['name']
                for level_val in vals['levels']:
                    with skill_type_form.skill_level_ids.new() as level:
                        level.name = level_val['name']
                        level.level_progress = level_val['level_progress']
            skill_types += skill_type_form.save()
        return skill_types

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.skipTest(cls, "To be reintroduced post 18.4 freeze")
        cls.employee = cls.env['hr.employee'].create([
            {'name': 'Test Employee'},
        ])
        cls.certification, cls.language = cls._create_skill_types([
            {
                'name': "Certificate",
                'certificate': True,
                'skills': [
                    {'name': 'Odoo'},
                    {'name': 'Scrum'},
                ],
                'levels': [
                    {'name': '20%', 'level_progress': 20},
                    {'name': '50%', 'level_progress': 50},
                    {'name': '70%', 'level_progress': 70},
                    {'name': '100%', 'level_progress': 100},
                ],
            }, {
                'name': "Languages",
                'skills': [
                    {'name': 'Arabic'},
                    {'name': 'English'},
                    {'name': 'French'},
                ],
                'levels': [
                    {'name': 'A1', 'level_progress': 10},
                    {'name': 'A2', 'level_progress': 30},
                    {'name': 'B1', 'level_progress': 50},
                    {'name': 'B2', 'level_progress': 70},
                    {'name': 'C1', 'level_progress': 90},
                    {'name': 'C2', 'level_progress': 100},
                ],
            },
        ])

# |-------------------------------|  |----------------------------------|
# |           Skills              |  |              Level               |
# |-------------------------------|  |----------------------------------|---------------------------------|
# | Id  |  Skill Type  |   Name   |  |   Id  |  Skill Type  |   Name    | Index (in skill_type.level_ids) |
# |   1 |  Certificate |     Odoo |  |     1 |  Certificate |       20% |                               0 |
# |   2 |  Certificate |    Scrum |  |     2 |  Certificate |       50% |                               1 |
# |     |              |          |  |     3 |  Certificate |       70% |                               2 |
# |     |              |          |  |     4 |  Certificate |      100% |                               3 |
# |-------------------------------|  |----------------------------------|---------------------------------|
# |   2 |    Languages |  Arabic  |  |     5 |    Languages |        A1 |                               0 |
# |   3 |    Languages | English  |  |     6 |    Languages |        A2 |                               1 |
# |   4 |    Languages |  French  |  |     7 |    Languages |        B1 |                               2 |
# |     |              |          |  |     8 |    Languages |        B2 |                               3 |
# |     |              |          |  |     9 |    Languages |        C1 |                               4 |
# |     |              |          |  |    10 |    Languages |        C2 |                               5 |
# |-------------------------------|  |----------------------------------|---------------------------------|

# |-------------------------------------------------------------------------------------|
# |                                Employee Skill                                       |
# |-------------------------------------------------------------------------------------|
# |  Id  |  Skill Type  |  Skill  |  Level  | Certificate  |  Start Date  |  Stop Date  |
# |    1 |  Certificate |    Odoo |     50% |        True  |     24-03-02 |           - |
# |    2 |  Certificate |    Odoo |     20% |        True  |     24-01-01 |    24-04-01 | <- not present in current_employee_skill (because a valid certification for this skill exist)
# |    3 |    Languages | English |     A2  |       False  |     24-01-01 |           - |
# |    4 |    Languages |  Arabic |     A2  |       False  |     24-02-01 |           - |
# |    4 |    Languages |  Arabic |     A1  |       False  |     24-01-01 |    24-01-31 | <- not present in current_employee_skill (because this regular skill is expired)
# |-------------------------------------------------------------------------------------|

        cls.line1, cls.line2, cls.line3, cls.line4, cls.line5 = cls.env['hr.employee.skill'].create([
            {
                'skill_type_id': cls.certification.id,
                'skill_id': cls.certification.skill_ids[0].id,
                'skill_level_id': cls.certification.skill_level_ids[1].id,
                'employee_id': cls.employee.id,
                'valid_from': datetime.date(2024, 3, 2),
            }, {
                'skill_type_id': cls.certification.id,
                'skill_id': cls.certification.skill_ids[0].id,
                'skill_level_id': cls.certification.skill_level_ids[0].id,
                'employee_id': cls.employee.id,
                'valid_from': datetime.date(2024, 1, 1),
                'valid_to': datetime.date(2024, 4, 1),
            }, {
                'skill_type_id': cls.language.id,
                'skill_id': cls.language.skill_ids[1].id,
                'skill_level_id': cls.language.skill_level_ids[1].id,
                'employee_id': cls.employee.id,
                'valid_from': datetime.date(2024, 1, 1),
            }, {
                'skill_type_id': cls.language.id,
                'skill_id': cls.language.skill_ids[0].id,
                'skill_level_id': cls.language.skill_level_ids[1].id,
                'employee_id': cls.employee.id,
                'valid_from': datetime.date(2024, 2, 1),
            }, {
                'skill_type_id': cls.language.id,
                'skill_id': cls.language.skill_ids[0].id,
                'skill_level_id': cls.language.skill_level_ids[0].id,
                'employee_id': cls.employee.id,
                'valid_from': datetime.date(2024, 1, 1),
                'valid_to': datetime.date(2024, 1, 31),
            },
        ])

    def test_add_english_b1(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.language
            employee_skill_form.skill_id = self.language.skill_ids[1]
            employee_skill_form.skill_level_id = self.language.skill_level_ids[2]

        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        self.assertEqual(len(self.employee.employee_skill_ids.ids), 6)
        self.assertEqual(new_employee_skill.valid_from, fields.Date.today())
        self.assertEqual(self.line3.valid_to, fields.Date.today() - relativedelta(days=1))

    def test_edit_english_a2_to_english_b1(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        index = self.employee.current_employee_skill_ids.ids.index(self.line3.id)
        with employee_form.current_employee_skill_ids.edit(index) as employee_skill_form:
            employee_skill_form.skill_level_id = self.language.skill_level_ids[2]

        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        self.assertEqual(len(employee.employee_skill_ids.ids), 6)
        self.assertEqual(new_employee_skill.valid_from, fields.Date.today())
        self.assertEqual(self.line3.valid_to, fields.Date.today() - relativedelta(days=1))

    def test_edit_odoo_50_stop_date(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        index = self.employee.current_employee_skill_ids.ids.index(self.line1.id)
        with employee_form.current_employee_skill_ids.edit(index) as employee_skill_form:
            employee_skill_form.valid_to = fields.Date.today() + relativedelta(months=2)

        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        self.assertFalse(new_employee_skill)
        self.assertEqual(len(employee.employee_skill_ids.ids), 5)
        self.assertEqual(self.line1.valid_to, fields.Date.today() + relativedelta(months=2))

    def test_create_scrum_50_and_edit_it_to_french_a1(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        self.assertEqual(len(self.employee.employee_skill_ids.ids), 5)
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[1]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[1]
            employee_skill_form.valid_from = fields.Date.today() + relativedelta(months=-11)
            employee_skill_form.valid_to = fields.Date.today() + relativedelta(months=-5)

        employee = employee_form.save()
        self.assertEqual(len(employee.employee_skill_ids.ids), 6)
        self.assertEqual(len(employee.current_employee_skill_ids.ids), 4,
            "this expired certification should be added because this employee doesn't any valid certification for this skill"
        )

        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        index = self.employee.current_employee_skill_ids.ids.index(new_employee_skill.id)
        new_previous_employee_skills = employee.employee_skill_ids

        with employee_form.current_employee_skill_ids.edit(index) as employee_skill_form:
            employee_skill_form.skill_type_id = self.language
            employee_skill_form.skill_id = self.language.skill_ids[2]
            employee_skill_form.skill_level_id = self.language.skill_level_ids[0]

        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - new_previous_employee_skills
        delete_one = new_previous_employee_skills - employee.employee_skill_ids
        self.assertEqual(len(employee.employee_skill_ids.ids), 6)
        self.assertEqual(len(employee.current_employee_skill_ids.ids), 4,
            "the expired certification is deleted and the skill french a1 is valid so this skill should be in current_employee_skill_ids"
        )
        self.assertEqual(len(delete_one.ids), 1)
        self.assertEqual(new_employee_skill.valid_from, fields.Date.today())
        self.assertFalse(new_employee_skill.valid_to)

    def test_edit_arabic_a2_to_odoo_50_from_1_jan_to_1_june(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        index = self.employee.current_employee_skill_ids.ids.index(self.line4.id)
        with employee_form.current_employee_skill_ids.edit(index) as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[1]
            employee_skill_form.valid_from = fields.Date.today() - relativedelta(months=5)
            employee_skill_form.valid_to = fields.Date.today() + relativedelta(months=7)

        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        self.assertEqual(self.line4.valid_to, fields.Date.today() - relativedelta(days=1))
        self.assertEqual(self.line4.valid_from, datetime.date(2024, 2, 1))
        self.assertEqual(new_employee_skill.valid_from, fields.Date.today() - relativedelta(months=5))
        self.assertEqual(new_employee_skill.valid_to, fields.Date.today() + relativedelta(months=7))

    def test_add_odoo_50_from_2_mar_to_infinite(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[1]
            employee_skill_form.valid_from = datetime.date(2024, 3, 2)

        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        self.assertFalse(new_employee_skill, "this certificate already exist for this date range")
        self.assertEqual(len(self.employee.employee_skill_ids.ids), 5)

    def test_add_english_a2(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.language
            employee_skill_form.skill_id = self.language.skill_ids[1]
            employee_skill_form.skill_level_id = self.language.skill_level_ids[2]
        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        self.assertEqual(new_employee_skill.valid_from, fields.Date.today())
        self.assertFalse(new_employee_skill.valid_to)
        self.assertEqual(self.line3.valid_to, fields.Date.today() - relativedelta(days=1))
        self.assertEqual(len(employee.employee_skill_ids.ids), 6)

    def test_add_french_a1_and_edit_it_after_to_french_a2(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.language
            employee_skill_form.skill_id = self.language.skill_ids[2]
            employee_skill_form.skill_level_id = self.language.skill_level_ids[1]
        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills

        self.assertEqual(new_employee_skill.valid_from, fields.Date.today())
        self.assertFalse(new_employee_skill.valid_to)
        self.assertEqual(len(employee.employee_skill_ids.ids), 6)

        index = self.employee.current_employee_skill_ids.ids.index(new_employee_skill.id)
        with employee_form.current_employee_skill_ids.edit(index) as employee_skill_form:
            employee_skill_form.skill_level_id = self.language.skill_level_ids[4]
        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        self.assertEqual(new_employee_skill.valid_from, fields.Date.today())
        self.assertFalse(new_employee_skill.valid_to)
        self.assertEqual(new_employee_skill.skill_level_id, self.language.skill_level_ids[4])
        self.assertEqual(len(employee.employee_skill_ids.ids), 6)

    def test_archiving_vs_deleting_regular_skill(self):
        employee_form = Form(self.employee)
        self.assertEqual(
            len(self.employee.employee_skill_ids.ids), 5, "The test employee should start with 5 skills."
        )

        # Remove one of the skills from the setup
        index = self.employee.current_employee_skill_ids.ids.index(self.line3.id)
        employee_form.current_employee_skill_ids.remove(index=index)
        employee = employee_form.save()
        self.assertEqual(
            len(employee.employee_skill_ids.ids),
            5,
            "The test employee should still have 5 skills, as the archived skill was not created within the last day",
        )

        self.assertEqual(
            self.line3.valid_to,
            fields.Date.today() - relativedelta(days=1),
            "The skill that got removed should have date_to set to one day before now",
        )

        previous_employee_skills = self.employee.employee_skill_ids
        # Add French B2
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.language
            employee_skill_form.skill_id = self.language.skill_ids[2]
            employee_skill_form.skill_level_id = self.language.skill_level_ids[4]
        employee = employee_form.save()
        new_employee_skill = employee.employee_skill_ids - previous_employee_skills
        self.assertEqual(
            len(employee.employee_skill_ids.ids),
            6,
            "Creating a new skill should result in the employee having 6 skills.",
        )

        # Remove it
        index = self.employee.current_employee_skill_ids.ids.index(new_employee_skill.id)
        employee_form.current_employee_skill_ids.remove(index=index)
        employee = employee_form.save()
        self.assertEqual(
            len(employee.employee_skill_ids.ids),
            5,
            "The skill that got removed should have been deleted as it was created within the last day",
        )

    def test_archiving_vs_deleting_certification(self):
        employee_form = Form(self.employee)
        self.assertEqual(
            len(self.employee.employee_skill_ids.ids), 5, "The test employee should start with 5 skills."
        )

        # Remove one of certification from the setup (not expired certification)
        index = self.employee.current_employee_skill_ids.ids.index(self.line1.id)
        employee_form.current_employee_skill_ids.remove(index=index)
        employee = employee_form.save()
        self.assertEqual(len(employee.employee_skill_ids.ids), 5, "The test employee should have 5 skills")
        self.assertEqual(self.line1.valid_to, fields.Date.today() - relativedelta(days=1))

        # Remove one of certification from the setup (expired certification)
        index = self.employee.current_employee_skill_ids.ids.index(self.line1.id)
        employee_form.current_employee_skill_ids.remove(index=index)
        employee = employee_form.save()
        self.assertEqual(
            len(employee.employee_skill_ids.ids),
            4,
            "The test employee should have 4 skills since the expired certification is removed"
        )

    def test_add_odoo_70_from_1_jan_1_mar(self):
        self.assertEqual(
            len(self.employee.employee_skill_ids.ids),
            5,
            "The test employee should have 5 skills",
        )
        employee_form = Form(self.employee)
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[2]
            employee_skill_form.valid_from = datetime.date(2024, 1, 1)  # so same as odoo 20%
            employee_skill_form.valid_to = datetime.date(2024, 4, 1)  # so same as odoo 20%

        employee = employee_form.save()
        self.assertEqual(
            len(employee.employee_skill_ids.ids),
            6,
            "The test employee should have 6 skills",
        )

    def test_add_odoo_50_from_1_jan_to_infinite(self):
        self.assertEqual(
            len(self.employee.employee_skill_ids.ids),
            5,
            "The test employee should have 5 skills",
        )
        employee_form = Form(self.employee)
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[1]  # so same as odoo 50%
            employee_skill_form.valid_from = datetime.date(2024, 1, 1)

        employee = employee_form.save()
        self.assertEqual(
            len(employee.employee_skill_ids.ids),
            6,
            "The test employee should have 6 skills",
        )

    def test_multiple_exact_same_skills_are_deduplicated_before_creation(self):
        """
        Assert that when you add multiple entries of the same skill:level,
        only one applicant skill will be created.
        """
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        for i in range(3):
            with employee_form.current_employee_skill_ids.new() as employee_skill_form:
                employee_skill_form.skill_type_id = self.certification
                employee_skill_form.skill_id = self.certification.skill_ids[0]
                employee_skill_form.skill_level_id = self.certification.skill_level_ids[1]
        employee_form.save()
        new_skill = self.employee.employee_skill_ids - previous_employee_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(new_skill), 1)
        self.assertEqual(new_skill.valid_from, fields.Date.today())
        self.assertEqual(len(self.employee.employee_skill_ids), 6)

    def test_multiple_same_skill_different_level_are_deduplicated_before_creation(self):
        """
        Assert that when you add multiple entries of the same skill but different level,
        only one applicant skill will be created.
        """
        skill_levels = self.language.skill_level_ids
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        for level in skill_levels:
            with employee_form.current_employee_skill_ids.new() as employee_skill_form:
                employee_skill_form.skill_type_id = self.language
                employee_skill_form.skill_id = self.language.skill_ids[0]
                employee_skill_form.skill_level_id = level
        employee_form.save()
        new_skill = self.employee.employee_skill_ids - previous_employee_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(new_skill), 1)
        self.assertEqual(new_skill.valid_from, fields.Date.today())
        self.assertEqual(len(self.employee.employee_skill_ids), 6)

    def test_same_certification_with_different_levels_but_same_dates_can_coexist(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        self.assertEqual(len(self.employee.current_employee_skill_ids), 3)
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[1]
            employee_skill_form.valid_from = fields.Date.today() - relativedelta(months=4)
            employee_skill_form.valid_to = fields.Date.today() + relativedelta(months=8)
        employee_form.save()
        new_skill = self.employee.employee_skill_ids - previous_employee_skills

        self.assertTrue(new_skill)
        self.assertEqual(len(self.employee.employee_skill_ids), 6, "The new certification should be added")
        self.assertEqual(len(self.employee.current_employee_skill_ids), 4, "The new certification should be added")

    def test_duplicate_certifications_in_the_past_are_not_created(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids
        previous_current_employee_skills = self.employee.current_employee_skill_ids
        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[2]
            employee_skill_form.valid_from = fields.Date.today() - relativedelta(years=2)
            employee_skill_form.valid_to = fields.Date.today() - relativedelta(years=2)
        employee_form.save()
        new_skill = self.employee.employee_skill_ids - previous_employee_skills
        new_previous_employee_skills = self.employee.employee_skill_ids
        self.assertTrue(new_skill)
        self.assertEqual(len(self.employee.employee_skill_ids), 6)
        self.assertEqual(self.employee.current_employee_skill_ids, previous_current_employee_skills,
        "an active certification already existed for this skill type; so the current_employee_skills should be the same"
        )

        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[2]
            employee_skill_form.valid_from = fields.Date.today() - relativedelta(years=2)
            employee_skill_form.valid_to = fields.Date.today() - relativedelta(years=2)
        employee_form.save()
        new_skill = self.employee.employee_skill_ids - new_previous_employee_skills
        self.assertFalse(new_skill, "A certification with the exact same values already exists so a new one shouldn't be created")
        self.assertEqual(len(self.employee.employee_skill_ids), 6)
        self.assertEqual(self.employee.current_employee_skill_ids, previous_current_employee_skills,
        "an active certification already existed for this skill type; so the current_employee_skills should be the same"
        )

    def test_rpc_call_editing_range_date_regular_skill(self):
        """
            This test is to ensure if a client call directly the create without our form view or with a custom
            then he can modify the date range of a regular skill

            French level for Employee Test
            start:
                    2025-01-15        2025-03-20                             2025-05-20
            -------------|-----------------|--------------------------------------|------------------
                        A1                 A2                                     B1
            stop:
                    2025-01-15                          2025-04-20           2025-05-20
            -------------|----------------------------------|---------------------|------------------
                        A1                                  A2                    B1
        """

        french_a1, french_a2, _ = self.env['hr.employee.skill'].create([
            {
                'skill_type_id': self.language.id,
                'skill_id': self.language.skill_ids[2].id,
                'skill_level_id': self.language.skill_level_ids[0].id,
                'employee_id': self.employee.id,
                'valid_from': datetime.date(2025, 1, 15),
                'valid_to': datetime.date(2025, 3, 19),
            }, {
                'skill_type_id': self.language.id,
                'skill_id': self.language.skill_ids[2].id,
                'skill_level_id': self.language.skill_level_ids[1].id,
                'employee_id': self.employee.id,
                'valid_from': datetime.date(2025, 3, 20),
                'valid_to': datetime.date(2025, 5, 19),
            }, {
                'skill_type_id': self.language.id,
                'skill_id': self.language.skill_ids[2].id,
                'skill_level_id': self.language.skill_level_ids[2].id,
                'employee_id': self.employee.id,
                'valid_from': datetime.date(2025, 5, 20)
            },
        ])
        french_a2.write({'valid_from': datetime.date(2025, 4, 20)})
        french_a1.write({'valid_to': datetime.date(2025, 4, 19)})
        self.assertEqual(french_a1.valid_to, datetime.date(2025, 4, 19))
        self.assertEqual(french_a2.valid_from, datetime.date(2025, 4, 20))
        with self.assertRaises(ValidationError):
            french_a1.write({'valid_to': datetime.date(2025, 4, 25)})
        with self.assertRaises(ValidationError):
            french_a2.write({'valid_from': datetime.date(2025, 2, 25)})

    def test_expire_current_certification_with_one_expired_for_the_same_date(self):
        employee_form = Form(self.employee)
        previous_employee_skills = self.employee.employee_skill_ids

        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[2]
            employee_skill_form.valid_from = fields.Date.today() - relativedelta(years=2)
            employee_skill_form.valid_to = fields.Date.today() + relativedelta(years=2)
        employee_form.save()
        new_skill = self.employee.employee_skill_ids - previous_employee_skills

        with employee_form.current_employee_skill_ids.new() as employee_skill_form:
            employee_skill_form.skill_type_id = self.certification
            employee_skill_form.skill_id = self.certification.skill_ids[0]
            employee_skill_form.skill_level_id = self.certification.skill_level_ids[2]
            employee_skill_form.valid_from = fields.Date.today() - relativedelta(years=2)
            employee_skill_form.valid_to = fields.Date.today() - relativedelta(days=1)
        employee_form.save()

        self.assertEqual(len(self.employee.employee_skill_ids), 7)

        index = self.employee.current_employee_skill_ids.ids.index(new_skill.id)
        employee_form.current_employee_skill_ids.remove(index=index)
        employee_form.save()
        self.assertEqual(len(self.employee.employee_skill_ids), 6, "the certification is removed because an other expired certification has the same validity range")
