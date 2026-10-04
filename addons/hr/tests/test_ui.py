# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, HttpCase, freeze_time, tagged, new_test_user


@tagged('-at_install', 'post_install', 'is_tour')
class TestEmployeeUi(HttpCase):
    def test_employee_profile_tour(self):
        user = new_test_user(self.env, login='davidelora', groups='base.group_user')
        johnny_user = new_test_user(self.env, login="johnny", name="Johnny H.")

        self.env['hr.employee'].create([{
            'name': 'Johnny H.',
            "user_id": johnny_user.id,
        }, {
            'name': 'David Elora',
            'user_id': user.id,
        }])

        self.start_tour("/odoo", 'hr_employee_tour', login="davidelora")

    @freeze_time('2024-01-01')
    def test_version_timeline_auto_save_tour(self):
        # as payroll tap access will be overridden by hr_payroll
        is_payroll_installed = self.env['ir.module.module'].search_count([
            ('name', '=', 'hr_payroll'), ('state', '=', 'installed')])
        group = 'hr_payroll.group_hr_payroll_manager' if is_payroll_installed else 'hr.group_hr_manager'
        user = new_test_user(self.env, login='alice', groups=group)
        bob_user = new_test_user(self.env, login="Bob", name="Bob M.")

        _, bob_employee = self.env['hr.employee'].create([
            {
                'name': 'Alice',
                'user_id': user.id,
            },
            {
                'name': 'Bob M.',
                "user_id": bob_user.id,
                'employee_type_id': self.env.ref('hr.contract_type_employee').id,
            },
        ])

        self.start_tour("/odoo", 'version_timeline_auto_save_tour', login="alice")
        self.assertFalse(bob_employee.version_ids[-1].contract_date_start)

    def test_create_employee_with_hr_rights(self):
        new_test_user(self.env, login='hr_user', groups='hr.group_hr_user')
        self.start_tour('/odoo', 'hr_officer_create_employee_tour', login='hr_user')

        emp = self.env['hr.employee'].search([('name', 'ilike', 'My Employee')])
        self.assertTrue(emp)

    def test_first_contract_date_with_hr_user_rights(self):
        new_test_user(self.env, login='hr_user', groups='hr.group_hr_user')
        self.start_tour('/odoo', 'hr_user_kanban_view_tour', login='hr_user', timeout=350)

    def test_skills_tour(self):
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

    def test_skills_type_tour(self):
        self.start_tour("/odoo", 'hr_skills_type_tour', login='admin')
        skill_type_id = self.env['hr.skill.type'].search([('name', '=', 'Cooking Skill')]).id
        self.assertTrue(self.env['hr.skill.level'].search([
            ('default_level', '=', True),
            ('skill_type_id', '=', skill_type_id)
        ]).name, "Intermediate")
