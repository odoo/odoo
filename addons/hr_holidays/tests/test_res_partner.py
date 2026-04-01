# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests.common import new_test_user, tagged, TransactionCase, users
from odoo.addons.mail.tools.discuss import Store


@tagged('post_install', '-at_install')
class TestPartner(TransactionCase):

    @classmethod
    @freeze_time('2024-06-04')
    def setUpClass(cls):
        super().setUpClass()
        # use a single value for today throughout the tests to avoid weird scenarios around midnight
        cls.today = fields.Date.today()
        baseUser = cls.env['res.users'].create({
            'email': 'e.e@example.com',
            'group_ids': [Command.link(cls.env.ref('base.group_user').id)],
            'login': 'emp',
            'name': 'Ernest Employee',
            'notification_type': 'inbox',
            'signature': '--\nErnest',
        })
        cls.partner = baseUser.partner_id
        cls.users = baseUser + cls.env['res.users'].create({
            'name': 'test1',
            'login': 'test1',
            'email': 'test1@example.com',
            'partner_id': cls.partner.id,
        })
        cls.employees = cls.env['hr.employee'].create([{
            'user_id': user.id,
        } for user in cls.users])
        cls.leave_type = cls.env['hr.leave.type'].create({
            'requires_allocation': False,
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'responsible_ids': cls.users.ids
        })
        cls.leaves = cls.env['hr.leave'].create([{
            'request_date_from': "2024-06-03",
            'request_date_to': "2024-06-06",
            'employee_id': cls.employees[0].id,
            'holiday_status_id': cls.leave_type.id,
        }, {
            'request_date_from': "2024-06-02",
            'request_date_to': "2024-06-05",
            'employee_id': cls.employees[1].id,
            'holiday_status_id': cls.leave_type.id,
        }])
        cls.user_no_hr_access = new_test_user(
            cls.env, login="user_no_hr_access",
        )

    @freeze_time('2024-06-04')
    def test_res_partner_to_store(self):
        self.leaves.write({'state': 'validate'})
        self.assertEqual(
            Store().add(self.partner).get_result()["hr.employee"][0]["leave_date_to"],
            "2024-06-07",
            "Return date is the return date of the main user of the partner",
        )
        self.leaves[0].action_refuse()
        self.assertEqual(
            Store().add(self.partner).get_result()["hr.employee"][0]["leave_date_to"],
            False,
            "Partner is not considered out of office if their main user is not on holiday",
        )

    @freeze_time("2024-06-04")
    @users("user_no_hr_access")
    def test_res_partner_to_store_no_hr_access(self):
        self.leaves.write({"state": "validate"})
        data = Store().add(self.partner.with_user(self.user_no_hr_access)).get_result()
        self.assertEqual(
            data["hr.employee"][0]["leave_date_to"],
            "2024-06-07",
            "Return date is the return date of the main user of the partner, "
            "even if the user has no access to the company",
        )
