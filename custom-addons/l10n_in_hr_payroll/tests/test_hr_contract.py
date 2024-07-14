# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from freezegun import freeze_time
from odoo.addons.l10n_in_hr_payroll.tests.common import TestPayrollCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestHrContract(TestPayrollCommon):

    def test_contract_end_reminder_to_hr(self):
        """ Check reminder activity is set the for probation contract
        Test Case
        ---------
            1) Create contract
            2) Check the activity is activity schedule or not
            3) Now run cron
            4) Check the activity is activity schedule or not
        """
        user_admin_id = self.env.ref('base.user_admin').id

        contract = self.env['hr.contract'].create({
            'date_start': date(2020, 1, 1),
            'date_end':  date(2020, 4, 30),
            'name': 'Rahul Probation contract',
            'resource_calendar_id': self.env.company.resource_calendar_id.id,
            'wage': 5000.0,
            'employee_id': self.rahul_emp.id,
            'state': 'open',
            'contract_type_id': self.env.ref('l10n_in_hr_payroll.l10n_in_contract_type_probation').id,
            'kanban_state': 'done',
            'hr_responsible_id': user_admin_id,
        })
        with freeze_time("2020-04-24"):
            mail_activity = self.env['mail.activity'].search([('res_id', '=', contract.id), ('res_model', '=', 'hr.contract')])
            self.assertFalse(mail_activity.exists(), "There should be no mail activity as contract is not ends on 2020-04-10")
            # run the cron
            self.env['hr.contract'].update_state()
            mail_activity = self.env['mail.activity'].search([('res_id', '=', contract.id), ('res_model', '=', 'hr.contract')])
            self.assertTrue(mail_activity.exists(), "There should be reminder activity as employee rahul's contract end today")
