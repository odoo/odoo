# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, HttpCase, tagged, new_test_user

@tagged('-at_install', 'post_install')
class TestEmployeeUi(HttpCase):
    def test_employee_profile_tour(self):
        user = new_test_user(self.env, login='davidelora', groups='base.group_user')

        self.env['hr.employee'].create([{
            'name': 'Johnny H.',
        }, {
            'name': 'David Elora',
            'user_id': user.id,
        }])

        self.start_tour("/odoo", 'hr_employee_tour', login="davidelora")

    def test_skills_ui(self):
        with Form(self.env['hr.skill.type']) as skill_type:
            skill_type.name = 'Best Music'
            with skill_type.skill_ids.new() as skill:
                skill.name = 'Fortunate Son'
            with skill_type.skill_ids.new() as skill:
                skill.name = 'Oh Mary'
            for x in range(10):
                with skill_type.skill_level_ids.new() as level:
                    level.name = f"level {x}"
                    level.level_progress = x * 10
                    level.default_level = x % 2
        skill_type.save()

        with Form(self.env['hr.skill.type']) as skill_type:
            skill_type.name = 'Music Certification'
            skill_type.is_certification = True
            with skill_type.skill_ids.new() as skill:
                skill.name = 'Piano'
            with skill_type.skill_ids.new() as skill:
                skill.name = 'Guitar'
            with skill_type.skill_level_ids.new() as level:
                level.name = "Certified"
                level.level_progress = 100
                level.default_level = True
        skill_type.save()

        self.start_tour("/odoo", 'hr_skills_tour', login='admin')

    def test_skills_ui2(self):

        self.start_tour("/odoo", 'hr_skills_type_tour', login='admin')
        skill_type_id = self.env['hr.skill.type'].search([('name', '=', 'Cooking Skill')]).id
        self.assertTrue(self.env['hr.skill.level'].search([
            ('default_level', '=', True),
            ('skill_type_id', '=', skill_type_id)
        ]).name, "Intermediate")
