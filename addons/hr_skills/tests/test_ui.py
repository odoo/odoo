# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, Form, HttpCase
from odoo.tools import mute_logger

@tagged('-at_install', 'post_install')
class SkillsTestUI(HttpCase):

    @mute_logger('odoo.http', 'odoo.sql_db')
    def test_ui(self):
        with Form(self.env['hr.skill.type']) as skill_type:
            skill_type.name = 'Best Music'
            with skill_type.skill_ids.new() as skill:
                skill.name = f'Fortunate Son'
            with skill_type.skill_ids.new() as skill:
                skill.name = f'Oh Mary'
            for x in range(10):
                with skill_type.skill_level_ids.new() as level:
                    level.name = f"level {x}"
                    level.level_progress = x * 10
                    level.default_level = x % 2
        skill_type = skill_type.save()

        self.start_tour("/odoo", 'hr_skills_tour', login='admin')

    def test_ui2(self):

        self.start_tour("/odoo", 'hr_skills_type_tour', login='admin')
        skill_type_id = self.env['hr.skill.type'].search([('name', '=', 'Cooking Skill')]).id
        self.assertTrue(self.env['hr.skill.level'].search([
            ('default_level', '=', True),
            ('skill_type_id', '=', skill_type_id)
        ]).name, "Intermediate")
