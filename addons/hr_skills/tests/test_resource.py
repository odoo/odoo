# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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
        levels = self.env['hr.skill.level'].create([{
            'name': f'Level {x}',
            'level_progress': x * 10,
        } for x in range(10)])
        skill_type = self.env['hr.skill.type'].create({
            'name': 'Best Music',
            'skill_level_ids': levels.ids,
        })
        skill = self.env['hr.skill'].create([{
            'name': 'Fortunate Son',
            'skill_type_id': skill_type.id,
        }])
        self.env['hr.employee.skill'].create({
            'employee_id': employee.id,
            'skill_id': skill.id,
            'skill_level_id': levels[1].id,
            'skill_type_id': skill_type.id,
        })

        self.assertEqual(resource.employee_skill_ids, employee.employee_skill_ids)
