# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged, new_test_user

@tagged('-at_install', 'post_install')
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
