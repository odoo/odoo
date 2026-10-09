# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('post_install', '-at_install')
class TestSkillsSelfEdit(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee = mail_new_test_user(
            cls.env,
            login='skills_self_edit_user',
            groups='base.group_user',
            name='Self Edit User',
        )
        cls.own_employee = cls.env['hr.employee'].create({
            'name': 'Self Edit Employee',
            'user_id': cls.user_employee.id,
        })
        cls.other_employee = cls.env['hr.employee'].create({'name': 'Other Employee'})
        cls.skill_type = cls.env['hr.skill.type'].create({
            'name': 'Languages',
            'skill_ids': [Command.create({'name': 'English'}), Command.create({'name': 'French'})],
            'skill_level_ids': [
                Command.create({'name': 'B1', 'level_progress': 50}),
                Command.create({'name': 'C1', 'level_progress': 100}),
            ],
        })
        cls.english, cls.french = cls.skill_type.skill_ids
        cls.level_b1, cls.level_c1 = cls.skill_type.skill_level_ids

    def _skill_vals(self, skill, level):
        return {
            'employee_id': self.own_employee.id,
            'skill_type_id': self.skill_type.id,
            'skill_id': skill.id,
            'skill_level_id': level.id,
        }

    def _get_own_user(self):
        return self.user_employee.with_user(self.user_employee)

    def _get_last_message_body(self, employee):
        return employee.message_ids.sorted('id')[-1:].body

    def test_skills_self_edit_disabled(self):
        self.own_employee.company_id.hr_skills_self_edit = False
        own_user = self._get_own_user()
        self.assertFalse(own_user.can_edit_skills)
        with self.assertRaises(AccessError):
            own_user.write({
                'current_employee_skill_ids': [Command.create(self._skill_vals(self.english, self.level_b1))],
            })
        with self.assertRaises(AccessError):
            self.env['hr.employee.skill'].with_user(self.user_employee).create(
                self._skill_vals(self.english, self.level_b1),
            )

    def test_skills_self_edit_enabled(self):
        self.own_employee.company_id.hr_skills_self_edit = True
        own_user = self._get_own_user()
        self.assertTrue(own_user.can_edit_skills)

        own_user.write({
            'current_employee_skill_ids': [Command.create(self._skill_vals(self.english, self.level_b1))],
        })
        self.assertEqual(self.own_employee.current_employee_skill_ids.skill_level_id, self.level_b1)
        message = self.own_employee.message_ids.sorted('id')[-1]
        self.assertEqual(message.author_id, self.user_employee.partner_id)
        self.assertIn('Added: English: B1', message.body)

        english_skill = self.own_employee.current_employee_skill_ids
        own_user.write({
            'current_employee_skill_ids': [Command.update(english_skill.id, {'skill_level_id': self.level_c1.id})],
        })
        self.assertEqual(self.own_employee.current_employee_skill_ids.skill_level_id, self.level_c1)
        self.assertIn('Updated: English: B1 → C1', self._get_last_message_body(self.own_employee))

        own_user.write({
            'current_employee_skill_ids': [Command.delete(self.own_employee.current_employee_skill_ids.id)],
        })
        self.assertFalse(self.own_employee.current_employee_skill_ids)
        self.assertIn('Removed: English: C1', self._get_last_message_body(self.own_employee))

    def test_skills_self_edit_other_employee(self):
        self.env.company.hr_skills_self_edit = True
        self.assertFalse(self.res_users_hr_officer.with_user(self.user_employee).can_edit_skills)
        other_skill = self.env['hr.employee.skill'].create({
            **self._skill_vals(self.french, self.level_b1),
            'employee_id': self.other_employee.id,
        })
        with self.assertRaises(AccessError):
            self._get_own_user().write({
                'current_employee_skill_ids': [Command.delete(other_skill.id)],
            })
        with self.assertRaises(AccessError):
            self._get_own_user().write({
                'current_employee_skill_ids': [Command.update(other_skill.id, {'skill_level_id': self.level_c1.id})],
            })
        self.assertEqual(other_skill.skill_level_id, self.level_b1)

    def test_skills_changes_logged_for_hr_user(self):
        self.own_employee.with_user(self.res_users_hr_officer).write({
            'current_employee_skill_ids': [Command.create(self._skill_vals(self.french, self.level_c1))],
        })
        message = self.own_employee.message_ids.sorted('id')[-1]
        self.assertEqual(message.author_id, self.res_users_hr_officer.partner_id)
        self.assertIn('Added: French: C1', message.body)
