# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command
from odoo.tests import HttpCase
from odoo.tests.common import tagged

from datetime import date


@tagged('post_install', '-at_install')
class TestHrLeaveTypeTour(HttpCase):
    @freeze_time('01/17/2022')
    def test_hr_leave_type_tour(self):
        """
        Test Time Off multi company rule defined in hr_holidays_security for hr_leave_type.
        The available leave types are the ones whose:
            - Company is one of the selected companies.
            - Company is false but whose country is one the countries of the selected companies.
            - Company is false and country is false

        Define:
            - 2 Companies: company_1 and company_2
            - 3 Leave Types:
                * leave_type_1 whose country is set to the country of company_1.
                * leave_type_2 whose company is set to company_2.
                * leave_type_3 whose country and company are both False.

        leave_type_1 will be available if company_1 is one of the selected companies.
        leave_type_2 will be available if company_2 is one of the selected companies.
        leave_type_3 will always be available.
        """
        admin_user = self.env.ref('base.user_admin')
        admin_user.write({
            'email': 'mitchell.admin@example.com',
        })
        admin_employee = admin_user.employee_id
        HRLeave = self.env['hr.leave']
        date_from = date(2022, 1, 17)
        date_to = date(2022, 1, 18)
        leaves_on_freeze_date = HRLeave.search([
            ('date_from', '>=', date_from),
            ('date_to', "<=", date_to),
            ('employee_id', '=', admin_employee.id)
        ])
        leaves_on_freeze_date.sudo().unlink()
        company_1 = self.env.company
        company_1.name = 'company_1'
        company_2 = self.env['res.company'].create({'name': 'company_2'})
        self.env["res.users"].browse(2).write({
            "company_ids": [Command.clear(), Command.link(company_1.id), Command.link(company_2.id)]
        })

        leave_type = self.env['hr.leave.type'].with_user(admin_user)

        leave_type.create({
            'name': 'leave_type_1',
            'requires_allocation': False,
            'leave_validation_type': 'hr',
            'country_id': company_1.country_id.id
        })
        leave_type.create({
            'name': 'leave_type_2',
            'requires_allocation': False,
            'leave_validation_type': 'hr',
            'company_id': company_2.id
        })
        leave_type.create({
            'name': 'leave_type_3',
            'requires_allocation': False,
            'leave_validation_type': 'hr'
        })
        self.start_tour('/web', 'hr_leave_type_tour', login="admin")
