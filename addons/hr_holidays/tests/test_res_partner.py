# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from dateutil.relativedelta import relativedelta

from freezegun import freeze_time

from odoo import Command, fields
from odoo.tests.common import tagged, TransactionCase
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
            'groups_id': [Command.link(cls.env.ref('base.group_user').id)],
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
            'requires_allocation': 'no',
            'name': 'Legal Leaves',
            'time_type': 'leave',
            'responsible_ids': cls.users.ids
        })
        cls.leaves = cls.env['hr.leave'].create([{
            'request_date_from': cls.today + relativedelta(days=-1),
            'request_date_to': cls.today + relativedelta(days=2),
            'employee_id': cls.employees[0].id,
            'holiday_status_id': cls.leave_type.id,
        }, {
            'request_date_from': cls.today + relativedelta(days=-2),
            'request_date_to': cls.today + relativedelta(days=1),
            'employee_id': cls.employees[1].id,
            'holiday_status_id': cls.leave_type.id,
        }])

    @freeze_time('2024-06-04')
    def test_res_partner_to_store(self):
        self.leaves.write({'state': 'validate'})
        self.assertEqual(
            Store(self.partner).get_result()["res.partner"][0]["out_of_office_date_end"],
            fields.Date.to_string(self.today + relativedelta(days=2)),
            'Return date is the first return date of all users associated with a partner',
        )
        self.leaves[1].action_refuse()
        self.assertEqual(
            Store(self.partner).get_result()["res.partner"][0]["out_of_office_date_end"],
            False,
            'Partner is not considered out of office if one of their users is not on holiday',
        )
