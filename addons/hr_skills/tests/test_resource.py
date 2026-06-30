# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestResourceSkills(TransactionCase):
    def test_availability_skills_infos_resource(self):
        """ Ensure that all the infos related to skill needed to display the avatar
            popover card are available on the model resource.resource.
        """
        user = self.env['res.users'].create([{
            'name': 'Test user',
            'login': 'test',
            'email': 'test@odoo.perso',
            'phone': '+32488990011',
        }])
        resource = self.env['resource.resource'].create([{
            'name': 'Test resource',
            'user_id': user.id,
        }])
        employee = self.env['hr.employee'].create([{
            'name': 'Test employee',
            'user_id': user.id,
            'resource_id': resource.id,
        }])

        with Form(self.env['hr.skill.type']) as skill_type:
            skill_type.name = 'Best Music'
            for i in range(3):
                with skill_type.skill_ids.new() as skill:
                    skill.name = f'Fortunate Son {i}'
            for x in range(10):
                with skill_type.skill_level_ids.new() as level:
                    level.name = f"level {x}"
                    level.level_progress = x * 10
                    level.default_level = x % 2
        skill_type = skill_type.save()

        self.env['hr.employee.skill'].create({
            'employee_id': employee.id,
            'skill_id': skill_type.skill_ids[2].id,
            'skill_level_id': skill_type.skill_level_ids[1].id,
            'skill_type_id': skill_type.id,
        })
        self.assertEqual(resource.employee_skill_ids, employee.employee_skill_ids)

        default_levels = skill_type.skill_level_ids.filtered(lambda level: level.default_level)
        self.assertEqual(len(default_levels), 1)
