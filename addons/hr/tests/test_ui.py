# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, freeze_time, tagged, new_test_user


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

        self.env['hr.employee'].create([{
            'name': 'Alice',
            'user_id': user.id,
        }])

        bob_employee = self.env['hr.employee'].create([{
            'name': 'Bob M.',
            "user_id": bob_user.id,
        }])

        bob_employee.write({
            'contract_date_start': '2024-01-01',
            'contract_date_end': False,
        })

        self.start_tour("/odoo", 'version_timeline_auto_save_tour', login="alice")
        self.assertFalse(bob_employee.version_ids[-1].contract_date_start)
