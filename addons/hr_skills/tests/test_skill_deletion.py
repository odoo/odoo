from odoo.exceptions import ValidationError
from odoo.tests import common


class TestHrSkillDeletion(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.skill_type = self.env['hr.skill.type'].create({
            'name': 'Quality Assurance',
            'skill_ids': [(0, 0, {'name': 'Functional Testing'})],
            'skill_level_ids': [(0, 0, {'name': 'Beginner', 'level_progress': 0})],
        })

    def test_cannot_delete_last_skill(self):
        last_skill = self.skill_type.skill_ids
        with self.assertRaises(ValidationError):
            last_skill.unlink()

    def test_cannot_delete_last_skill_level(self):
        last_level = self.skill_type.skill_level_ids
        with self.assertRaises(ValidationError):
            last_level.unlink()
